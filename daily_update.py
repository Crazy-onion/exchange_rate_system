# -*- coding: utf-8 -*-
"""
汇率底稿系统 —— 每日自动更新（独立运行版）

不依赖 WorkBuddy，可由 Windows 任务计划程序 / 双击 / 命令行直接运行。

流程：
  1. 判断是否真的需要更新（线上已是今天 + 印尼非空 + 兜底已是今天 → 直接退出）
  2. 刷新印尼 Ortax 兜底数据（本机国内网络才能抓到，服务器抓不到）
  3. git 提交并 push，触发 GitHub Actions 重新抓取三源并部署
  4. 轮询验证线上数据是否已变为今天

用法：
  python daily_update.py            正常执行
  python daily_update.py --force    跳过判断，强制执行一次
  python daily_update.py --no-pages 只刷新兜底不推送（调试用）
"""
import os
import sys
import json
import time
import subprocess
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# ---- 让 Windows 控制台能输出中文 ----
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "update.log"
LOCK_FILE = ROOT / ".update.lock"

DATA_URL = "https://crazy-onion.github.io/exchange_rate_system/data.json"
FALLBACK = ROOT / "fallback" / "ortax_fallback.json"
BRANCH = "main"

PYEXE = sys.executable
LOCK_TIMEOUT_MIN = 45          # 锁超过 45 分钟视为僵死
PUSH_RETRY = 3                 # push 重试次数
VERIFY_TIMEOUT_MIN = 15        # 轮询验证上限


def log(msg=""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


# ---------------- 单实例锁 ----------------
def acquire_lock():
    if LOCK_FILE.exists():
        age_min = (time.time() - LOCK_FILE.stat().st_mtime) / 60
        if age_min < LOCK_TIMEOUT_MIN:
            log(f"另一个实例正在运行（{age_min:.0f} 分钟前启动），本次退出。")
            return False
        log(f"发现僵死锁（{age_min:.0f} 分钟），清理后继续。")
        LOCK_FILE.unlink(missing_ok=True)
    LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    return True


def release_lock():
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


# ---------------- 工具 ----------------
def fetch_online(timeout=30):
    req = urllib.request.Request(DATA_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def run(cmd, timeout=1200, cwd=None):
    """执行命令，返回 (returncode, stdout+stderr)"""
    try:
        p = subprocess.run(
            cmd, cwd=cwd or str(ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, shell=False,
        )
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return -9, f"TIMEOUT after {timeout}s: {' '.join(cmd)}"
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}"


def git(args, timeout=300):
    return run(["git"] + args, timeout=timeout)


# ---------------- 步骤 ----------------
def need_update():
    """返回 (是否需要更新, 原因说明)"""
    today = today_str()
    reasons = []

    online_ok_date = None
    idn_count = -1
    try:
        d = fetch_online()
        ut = (d.get("updateTime") or "")[:10]
        idn_count = len(d.get("ortaxData", {}).get("CNY", []))
        online_ok_date = ut
        log(f"线上 updateTime = {d.get('updateTime')}，印尼 CNY 条数 = {idn_count}")
        if ut != today:
            reasons.append(f"线上数据不是今天（{ut}）")
        if idn_count <= 0:
            reasons.append("线上印尼数据为空（严重）")
    except Exception as e:
        reasons.append(f"无法读取线上数据（{type(e).__name__}）")
        log(f"读取线上数据失败: {e}")

    try:
        fb = json.loads(FALLBACK.read_text(encoding="utf-8"))
        gen = (fb.get("generated_at") or "")[:10]
        log(f"本地兜底 generated_at = {fb.get('generated_at')}")
        if gen != today:
            reasons.append(f"本地兜底不是今天（{gen}）")
    except Exception as e:
        reasons.append(f"无法读取本地兜底（{type(e).__name__}）")
        log(f"读取兜底失败: {e}")

    if not reasons:
        return False, "线上已是今天 + 印尼非空 + 兜底已是今天"
    return True, "；".join(reasons)


def refresh_fallback():
    """刷新印尼 Ortax 兜底数据（约 3 分钟，50 个请求）"""
    log(">>> 步骤1 刷新印尼兜底数据（约需 3 分钟）")
    rc, out = run([PYEXE, str(ROOT / "gen_ortax_fallback.py"), "25"], timeout=1800)
    tail = [l for l in out.strip().splitlines() if l.strip()][-6:]
    for l in tail:
        log("    " + l)
    if rc != 0:
        log(f"!! 兜底刷新返回码 {rc}（单币种失败时脚本会保留旧兜底，继续）")
    try:
        fb = json.loads(FALLBACK.read_text(encoding="utf-8"))
        for c in ["CNY", "USD"]:
            items = fb["data"].get(c, [])
            latest = max([x["date"] for x in items]) if items else "无"
            log(f"    兜底 {c}: {len(items)} 条，最新 {latest}")
    except Exception as e:
        log(f"!! 无法确认兜底结果: {e}")
    return rc == 0


def commit_and_push():
    log(">>> 步骤2 提交并推送")
    if refresh_fallback():
        rc, out = git(["add", "fallback/ortax_fallback.json"])
        rc, out = git(["commit", "-m", "chore: 刷新 Ortax 印尼兜底数据"])
        if rc == 0:
            log("    已提交兜底数据")
        else:
            log("    兜底数据无变化，跳过该提交")
    rc, out = git(["commit", "--allow-empty", "-m", "chore: 自动触发汇率更新"])
    log(f"    触发提交 rc={rc}")

    for i in range(1, PUSH_RETRY + 1):
        log(f"    第 {i}/{PUSH_RETRY} 次推送（可能耗时数分钟）…")
        rc, out = git(["push", "origin", BRANCH], timeout=900)
        tail = [l for l in out.strip().splitlines() if l.strip()][-3:]
        for l in tail:
            log("      " + l)
        if rc == 0:
            log("    推送成功")
            return True
        log(f"    推送失败 rc={rc}，30 秒后重试")
        time.sleep(30)
    log("!! 推送多次仍失败，终止")
    return False


def verify():
    log(">>> 步骤3 验证部署（最多等待 %d 分钟）" % VERIFY_TIMEOUT_MIN)
    today = today_str()
    deadline = time.time() + VERIFY_TIMEOUT_MIN * 60
    last = None
    while time.time() < deadline:
        time.sleep(30)
        try:
            d = fetch_online()
            ut = (d.get("updateTime") or "")[:10]
            cnt = len(d.get("ortaxData", {}).get("CNY", []))
            last = d.get("updateTime")
            if ut == today and cnt > 0:
                log(f"✔ 部署完成：updateTime = {last}，印尼 {cnt} 条")
                return True
        except Exception:
            pass
    log(f"!! 超时未完成部署，最后一次读到：{last}")
    return False


def main():
    force = "--force" in sys.argv
    no_push = "--no-push" in sys.argv

    log("=" * 60)
    log(f"汇率底稿自动更新启动  PID={os.getpid()}  force={force}")

    if not acquire_lock():
        return 0
    try:
        if force:
            need, reason = True, "--force 强制执行"
        else:
            need, reason = need_update()

        log(f"判断结果：{'需要更新' if need else '无需更新'} —— {reason}")
        if not need:
            log("今日数据已是最新，本次结束。")
            return 0

        if no_push:
            refresh_fallback()
            log("--no-push 模式，跳过推送。")
            return 0

        if not commit_and_push():
            return 2
        ok = verify()
        return 0 if ok else 3
    finally:
        release_lock()
        log("=" * 60 + "\n")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log(f"!! 未捕获异常: {type(e).__name__}: {e}")
        import traceback
        log(traceback.format_exc())
        release_lock()
        sys.exit(1)

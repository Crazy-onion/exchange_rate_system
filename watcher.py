# -*- coding: utf-8 -*-
"""
汇率底稿系统 —— 常驻哨兵（后台守护）

不需要管理员权限。随 Windows 登录自动启动，之后每 15 分钟巡检一次：
只要线上数据还不是「今天」、且已过当日 10:20，就自动跑一次完整更新
（刷新印尼兜底 → 提交 → 推送 → 验证部署）。

设计要点：
- 单实例：通过绑定本地端口确保只会有一个实例在跑
- 不抢跑：早于 10:20 不动，避免源数据还没出就误判完成
- 会退避：某次失败后等待 45 分钟再重试，不会疯狂刷
- 全静默：由 pythonw.exe 启动，没有窗口
- 所有输出写入 logs/update.log

用法：
  pythonw watcher.py    后台常驻（推荐）
  python  watcher.py    前台运行（调试用）
"""
import os
import sys
import time
import socket
import subprocess
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import daily_update as du  # noqa: E402

LOCK_PORT = 47391
CHECK_INTERVAL = 15 * 60     # 每 15 分钟巡检一次
RETRY_BACKOFF = 45 * 60      # 失败后退避 45 分钟
EARLIEST_HM = (10, 20)       # 当日最早允许运行时刻
BOOT_GRACE = 60              # 启动后先歇 1 分钟


def log(msg):
    du.log("[watcher] " + msg)


def bind_single_instance():
    """绑定固定端口实现单实例；绑定失败说明已有实例在跑"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    try:
        s.bind(("127.0.0.1", LOCK_PORT))
        s.listen(1)
        return s
    except OSError:
        try:
            s.close()
        except Exception:
            pass
        return None


def past_earliest():
    now = datetime.now()
    return (now.hour, now.minute) >= EARLIEST_HM


def run_full_update():
    """调用独立脚本执行完整更新（进程隔离，更稳）"""
    log(">>> 触发完整更新流程")
    try:
        p = subprocess.run(
            [sys.executable, os.path.join(ROOT, "daily_update.py")],
            cwd=ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=3300,
        )
        tail = [l for l in (p.stdout or "").strip().splitlines() if l.strip()][-5:]
        for l in tail:
            log("    " + l)
        ok = (p.returncode == 0)
        log(f"<<< 更新流程结束，退出码 {p.returncode}")
        return ok
    except subprocess.TimeoutExpired:
        log("!! 更新流程超时（55 分钟），本轮放弃")
        return False
    except Exception as e:
        log(f"!! 调用更新脚本异常: {type(e).__name__}: {e}")
        return False


def main():
    log("=" * 60)
    log(f"哨兵启动 PID={os.getpid()}  Python={sys.executable}")

    sock = bind_single_instance()
    if sock is None:
        log("已有哨兵实例在运行，本次退出。")
        return 0

    log(f"单实例锁定成功（端口 {LOCK_PORT}），{BOOT_GRACE} 秒后开始巡检")
    time.sleep(BOOT_GRACE)

    next_retry_at = 0.0
    consecutive_fail = 0

    while True:
        try:
            now_ts = time.time()
            if now_ts >= next_retry_at:
                need, reason = du.need_update()
                now = datetime.now()
                hhmm = now.strftime("%H:%M")
                if need and past_earliest():
                    log(f"巡检 {hhmm}：需要更新 —— {reason}")
                    ok = run_full_update()
                    if ok:
                        consecutive_fail = 0
                        log("本日更新已完成，继续待命。")
                    else:
                        consecutive_fail += 1
                        wait = RETRY_BACKOFF * min(consecutive_fail, 3)
                        next_retry_at = time.time() + wait
                        log(f"本轮失败（连续 {consecutive_fail} 次），{wait // 60} 分钟后重试")
                else:
                    why = "未到当日 %02d:%02d" % EARLIEST_HM if need else "数据已是最新"
                    log(f"巡检 {hhmm}：{why}，下次巡检 {CHECK_INTERVAL // 60} 分钟后")
            else:
                left = int(next_retry_at - now_ts)
                log(f"退避中，还剩 {left // 60} 分钟")
        except Exception as e:
            log(f"!! 巡检异常: {type(e).__name__}: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("收到中断，哨兵退出")
    except Exception as e:
        du.log(f"!! 哨兵致命错误: {type(e).__name__}: {e}")
        import traceback
        du.log(traceback.format_exc())
        sys.exit(1)

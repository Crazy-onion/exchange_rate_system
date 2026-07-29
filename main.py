"""
汇率底稿自动化系统 - 主入口
1. 抓取三个数据源
2. 生成Excel底稿
3. 生成HTML看板
4. 输出到 dist/ 目录供部署
"""
import os
import sys
import json
import shutil
from datetime import datetime, timedelta

# 确保能 import 同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers import scrape_ortax, scrape_safe_converter, scrape_safe_rmb_rate
from excel_generator import generate_excel_for_month
from dashboard import generate_dashboard
import holidays

# ============================================================
# 配置
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 优先使用仓库内置模板（云端 Linux 环境可用）；本地保留桌面路径兜底
TEMPLATE_PATH = os.path.join(BASE_DIR, "template", "汇率底稿模版.xlsx")
if not os.path.exists(TEMPLATE_PATH):
    TEMPLATE_PATH = r"D:\Users\rfuser\Desktop\【发送】汇率底稿模版.xlsx"
DIST_DIR = os.path.join(BASE_DIR, "dist")
CACHE_DIR = os.path.join(BASE_DIR, "cache")

# 目标月份 = 当前月
NOW = datetime.now()
TARGET_YEAR = NOW.year
TARGET_MONTH = NOW.month

# 历史数据范围：最近1年
HISTORY_START = (NOW - timedelta(days=365)).strftime('%Y-%m-%d')
HISTORY_END = NOW.strftime('%Y-%m-%d')


def ensure_dirs():
    """创建输出目录"""
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)


def save_cache(data, filename):
    """保存数据到缓存"""
    path = os.path.join(CACHE_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, default=str, indent=2)
    print(f"  缓存已保存: {path}")


def load_cache(filename):
    """从缓存加载数据"""
    path = os.path.join(CACHE_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def main():
    print("=" * 60)
    print(f"汇率底稿自动化系统")
    print(f"目标: {TARGET_YEAR}年{TARGET_MONTH}月")
    print(f"历史范围: {HISTORY_START} ~ {HISTORY_END}")
    print("=" * 60)

    ensure_dirs()

    # ============================================================
    # 1. 抓取数据
    # ============================================================
    print("\n[步骤1] 抓取汇率数据...")

    # 1a. Ortax 印尼央行 CNY + USD
    print("\n--- 1a. Ortax 印尼央行汇率 ---")
    ortax_cny = scrape_ortax('CNY', max_pages=25)
    ortax_usd = scrape_ortax('USD', max_pages=25)

    # 1b. SAFE 各种货币对美元折算率
    print("\n--- 1b. SAFE 货币折算率 ---")
    converter_data = scrape_safe_converter(months_back=12)

    # 1c. SAFE 人民币汇率中间价
    print("\n--- 1c. SAFE 人民币中间价 ---")
    rmb_rates, rmb_headers = scrape_safe_rmb_rate(HISTORY_START, HISTORY_END)

    # 保存缓存
    save_cache({
        'ortax_cny': ortax_cny,
        'ortax_usd': ortax_usd,
        'converter_data': converter_data,
        'rmb_rates': rmb_rates,
        'rmb_headers': rmb_headers,
        'update_time': NOW.strftime('%Y-%m-%d %H:%M:%S')
    }, 'exchange_rates.json')

    # ============================================================
    # 2. 生成 Excel 底稿 (所有可用月份)
    # ============================================================
    print("\n[步骤2] 生成Excel底稿...")

    # 从人民币中间价数据中确定可用月份
    available_months = set()
    for r in rmb_rates:
        parts = r['date'].split('-')
        available_months.add((int(parts[0]), int(parts[1])))

    # 按时间降序排列
    available_months = sorted(available_months, reverse=True)
    print(f"  可用月份: {len(available_months)}个月")

    # 为每个月生成Excel
    excel_files = []
    for year, month in available_months:
        excel_filename = f"汇率底稿_{year}{month:02d}.xlsx"
        excel_path = os.path.join(DIST_DIR, excel_filename)
        try:
            generate_excel_for_month(
                template_path=TEMPLATE_PATH,
                output_path=excel_path,
                ortax_cny=ortax_cny,
                ortax_usd=ortax_usd,
                rmb_rates=rmb_rates,
                rmb_headers=rmb_headers,
                converter_data=converter_data,
                target_year=year,
                target_month=month
            )
            excel_files.append(excel_filename)
        except Exception as e:
            print(f"  生成{year}-{month:02d}失败: {e}")

    # 当前月文件名 (用于兼容)
    excel_filename = f"汇率底稿_{TARGET_YEAR}{TARGET_MONTH:02d}.xlsx"
    print(f"  共生成{len(excel_files)}个Excel文件")

    # ============================================================
    # 3. 生成 HTML 看板
    # ============================================================
    print("\n[步骤3] 生成HTML看板...")
    from dashboard import load_update_worker_url
    dashboard_path = os.path.join(DIST_DIR, "index.html")

    generate_dashboard(
        output_path=dashboard_path,
        ortax_cny=ortax_cny,
        ortax_usd=ortax_usd,
        rmb_rates=rmb_rates,
        rmb_headers=rmb_headers,
        converter_data=converter_data,
        excel_filename=excel_filename,
        excel_files=excel_files,
        auth_password='exchange2026',
        update_worker_url=load_update_worker_url()
    )

    # ============================================================
    # 4. 汇总
    # ============================================================
    print("\n" + "=" * 60)
    print("完成！输出文件:")
    print(f"  Excel: {len(excel_files)}个月度底稿")
    for f in excel_files:
        print(f"    - {f}")
    print(f"  看板:  {dashboard_path}")
    print(f"  缓存:  {os.path.join(CACHE_DIR, 'exchange_rates.json')}")
    print("=" * 60)

    return {
        'excel_files': excel_files,
        'dashboard_path': dashboard_path,
        'ortax_cny_count': len(ortax_cny),
        'ortax_usd_count': len(ortax_usd),
        'rmb_count': len(rmb_rates),
        'converter_count': len(converter_data),
    }


if __name__ == '__main__':
    result = main()
    print(f"\n数据量统计:")
    print(f"  Ortax CNY: {result['ortax_cny_count']}条")
    print(f"  Ortax USD: {result['ortax_usd_count']}条")
    print(f"  人民币中间价: {result['rmb_count']}条")
    print(f"  货币折算率: {result['converter_count']}期")
    print(f"  生成Excel: {len(result['excel_files'])}个月度底稿")

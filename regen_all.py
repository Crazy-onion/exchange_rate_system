"""
从缓存数据重新生成所有月份的Excel底稿 + HTML看板
不需要重新抓取数据
"""
import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from excel_generator import generate_excel_for_month
from dashboard import generate_dashboard, load_update_worker_url

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "template", "汇率底稿模版.xlsx")
if not os.path.exists(TEMPLATE_PATH):
    TEMPLATE_PATH = r"D:\Users\rfuser\Desktop\【发送】汇率底稿模版.xlsx"
DIST_DIR = os.path.join(BASE_DIR, "dist")
CACHE_DIR = os.path.join(BASE_DIR, "cache")


def main():
    # 1. 加载缓存
    cache_path = os.path.join(CACHE_DIR, 'exchange_rates.json')
    print(f"加载缓存: {cache_path}")
    with open(cache_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    ortax_cny = data['ortax_cny']
    ortax_usd = data['ortax_usd']
    converter_data = data['converter_data']
    rmb_rates = data['rmb_rates']
    rmb_headers = data['rmb_headers']

    print(f"  Ortax CNY: {len(ortax_cny)}条")
    print(f"  Ortax USD: {len(ortax_usd)}条")
    print(f"  人民币中间价: {len(rmb_rates)}条")
    print(f"  货币折算率: {len(converter_data)}期")

    os.makedirs(DIST_DIR, exist_ok=True)

    # 2. 确定可用月份
    available_months = set()
    for r in rmb_rates:
        parts = r['date'].split('-')
        available_months.add((int(parts[0]), int(parts[1])))
    available_months = sorted(available_months, reverse=True)
    print(f"\n可用月份: {len(available_months)}个月")
    for y, m in available_months:
        print(f"  {y}-{m:02d}")

    # 3. 为每个月生成Excel
    print(f"\n生成Excel底稿...")
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

    print(f"\n共生成{len(excel_files)}个Excel文件")

    # 4. 生成HTML看板
    print(f"\n生成HTML看板...")
    now = datetime.now()
    current_excel = f"汇率底稿_{now.year}{now.month:02d}.xlsx"

    dashboard_path = os.path.join(DIST_DIR, "index.html")
    generate_dashboard(
        output_path=dashboard_path,
        ortax_cny=ortax_cny,
        ortax_usd=ortax_usd,
        rmb_rates=rmb_rates,
        rmb_headers=rmb_headers,
        converter_data=converter_data,
        excel_filename=current_excel,
        excel_files=excel_files,
        auth_password='exchange2026',
        update_time=data.get('update_time'),
        update_worker_url=load_update_worker_url()
    )

    print(f"\n完成！")
    print(f"  Excel: {len(excel_files)}个月度底稿")
    print(f"  看板: {dashboard_path}")


if __name__ == '__main__':
    main()

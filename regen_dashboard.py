"""从缓存重新生成HTML看板（不需要重新抓取数据）"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dashboard import generate_dashboard, load_update_worker_url

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
DIST_DIR = os.path.join(BASE_DIR, "dist")

# 加载缓存
cache_path = os.path.join(CACHE_DIR, "exchange_rates.json")
with open(cache_path, 'r', encoding='utf-8') as f:
    cache = json.load(f)

print(f"加载缓存: {cache_path}")
print(f"  更新时间: {cache['update_time']}")
print(f"  Ortax CNY: {len(cache['ortax_cny'])}条")
print(f"  Ortax USD: {len(cache['ortax_usd'])}条")
print(f"  人民币中间价: {len(cache['rmb_rates'])}条")
print(f"  货币折算率: {len(cache['converter_data'])}期")

# 生成看板
dashboard_path = os.path.join(DIST_DIR, "index.html")
excel_filename = "汇率底稿_202607.xlsx"

generate_dashboard(
    output_path=dashboard_path,
    ortax_cny=cache['ortax_cny'],
    ortax_usd=cache['ortax_usd'],
    rmb_rates=cache['rmb_rates'],
    rmb_headers=cache['rmb_headers'],
    converter_data=cache['converter_data'],
    excel_filename=excel_filename,
    update_worker_url=load_update_worker_url()
)

print(f"\n看板已重新生成: {dashboard_path}")

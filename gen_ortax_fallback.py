#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成 Ortax（印尼央行）兜底数据文件 fallback/ortax_fallback.json

背景：GitHub Actions（美国机房 IP）无法访问 datacenter.ortax.org，
      导致线上印尼汇率为空。本机（国内网络）可正常抓取，
      因此由本机抓取后提交到仓库，供 Actions 在实时抓取失败时使用。

用法：python gen_ortax_fallback.py [max_pages]
"""
import sys
import json
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scrapers import scrape_ortax

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FALLBACK_DIR = os.path.join(BASE_DIR, 'fallback')
OUT_PATH = os.path.join(FALLBACK_DIR, 'ortax_fallback.json')


def main():
    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    os.makedirs(FALLBACK_DIR, exist_ok=True)

    data = {}
    ok = True
    for cur in ['CNY', 'USD']:
        print(f'抓取 {cur} (max_pages={max_pages})...', flush=True)
        items = scrape_ortax(cur, max_pages=max_pages)
        if items:
            data[cur] = items
            print(f'  {cur}: {len(items)} 条, 最新 {items[0]["date"]}', flush=True)
        else:
            print(f'  {cur}: 抓取失败，保留原兜底数据', flush=True)
            ok = False
            # 保留文件中已有的旧数据
            if os.path.exists(OUT_PATH):
                try:
                    old = json.load(open(OUT_PATH, encoding='utf-8'))
                    if cur in old.get('data', {}):
                        data[cur] = old['data'][cur]
                        print(f'    沿用旧数据 {len(data[cur])} 条', flush=True)
                except Exception as e:
                    print(f'    读取旧兜底失败: {e}', flush=True)

    if not any(data.get(c) for c in ('CNY', 'USD')):
        print('两个币种均无数据，不覆盖兜底文件', flush=True)
        return 1

    out = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source': '本机抓取 datacenter.ortax.org（GitHub Actions 机房无法访问该站）',
        'data': data
    }
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f'已写入 {OUT_PATH} ({os.path.getsize(OUT_PATH)} bytes)', flush=True)
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())

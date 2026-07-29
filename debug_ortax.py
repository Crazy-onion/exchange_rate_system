"""调试Ortax页面：查找数据在HTML中的位置"""
import requests
import re
import json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}

resp = requests.get("https://datacenter.ortax.org/ortax/kursbi/show/CNY?page=1", headers=HEADERS, timeout=30)
html = resp.text

# 方法1: 查找 __NEXT_DATA__
next_data_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
if next_data_match:
    print("=== 找到 __NEXT_DATA__ ===")
    data = json.loads(next_data_match.group(1))
    # 打印数据结构的关键部分
    print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
else:
    print("未找到 __NEXT_DATA__")

# 方法2: 查找 self.__next_f.push 调用
push_matches = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.DOTALL)
print(f"\n=== 找到 {len(push_matches)} 个 __next_f.push 调用 ===")
for i, match in enumerate(push_matches):
    if 'CNY' in match or 'Kurs' in match or 'kurs' in match:
        print(f"\n--- push {i} (包含汇率数据) ---")
        # 这是一个JSON片段，可能需要处理转义
        try:
            # 尝试解析
            cleaned = match.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
            print(cleaned[:2000])
        except:
            print(match[:2000])

# 方法3: 直接搜索 Rp 数字模式
rp_matches = re.findall(r'Rp[\d.]+,\d+', html)
print(f"\n=== 找到 {len(rp_matches)} 个 Rp 数字 ===")
for m in rp_matches[:10]:
    print(f"  {m}")

# 方法4: 搜索日期模式
date_matches = re.findall(r'\d+\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}', html)
print(f"\n=== 找到 {len(date_matches)} 个日期 ===")
for m in date_matches[:10]:
    print(f"  {m}")

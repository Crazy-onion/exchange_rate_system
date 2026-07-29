"""调试脚本：检查Ortax和SAFE的HTML结构"""
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}

# 1. 检查Ortax页面结构
print("=== Ortax HTML结构 ===")
resp = requests.get("https://datacenter.ortax.org/ortax/kursbi/show/CNY?page=1", headers=HEADERS, timeout=30)
soup = BeautifulSoup(resp.text, 'lxml')

# 查找所有table
tables = soup.find_all('table')
print(f"表格数量: {len(tables)}")
for i, t in enumerate(tables):
    rows = t.find_all('tr')
    print(f"\n表格 {i}: {len(rows)} 行")
    for j, row in enumerate(rows[:5]):
        cells = row.find_all(['td', 'th'])
        cell_texts = [c.get_text(strip=True)[:40] for c in cells]
        print(f"  行{j}: {cell_texts}")

# 如果没有table，检查div结构
if not tables:
    print("\n无表格，检查div结构...")
    # 查找包含日期文本的元素
    import re
    date_elements = soup.find_all(string=re.compile(r'\d+\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}'))
    print(f"找到 {len(date_elements)} 个日期文本")
    for elem in date_elements[:5]:
        parent = elem.parent
        print(f"  标签: {parent.name}, 文本: {elem.strip()[:60]}")
        # 查找父容器的结构
        grandparent = parent.parent
        if grandparent:
            print(f"  父标签: {grandparent.name}, class={grandparent.get('class')}")

# 2. 检查SAFE人民币中间价响应
print("\n\n=== SAFE RMB Rate 响应结构 ===")
resp2 = requests.post(
    "https://www.safe.gov.cn/AppStructured/hlw/RMBQuery.do",
    data={'startDate': '2026-07-20', 'endDate': '2026-07-24', 'queryYN': 'true'},
    headers={**HEADERS, 'Content-Type': 'application/x-www-form-urlencoded'},
    timeout=30
)
resp2.encoding = 'utf-8'
soup2 = BeautifulSoup(resp2.text, 'lxml')

tables2 = soup2.find_all('table')
print(f"表格数量: {len(tables2)}")
for i, t in enumerate(tables2):
    rows = t.find_all('tr')
    print(f"\n表格 {i}: {len(rows)} 行")
    for j, row in enumerate(rows[:5]):
        cells = row.find_all(['td', 'th'])
        cell_texts = [c.get_text(strip=True)[:30] for c in cells]
        print(f"  行{j} ({len(cells)}列): {cell_texts}")

# 也打印响应的前2000字符看结构
print("\n\n响应前2000字符:")
print(resp2.text[:2000])

"""
汇率数据抓取模块
三个数据源:
1. Ortax 印尼央行 CNY 中间价 (每日)
2. SAFE 各种货币对美元折算率 (每月)
3. SAFE 人民币汇率中间价 (每日)
"""
import requests
import re
import io
import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import openpyxl

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

MONTHS_EN = {
    'January': 1, 'February': 2, 'March': 3, 'April': 4,
    'May': 5, 'June': 6, 'July': 7, 'August': 8,
    'September': 9, 'October': 10, 'November': 11, 'December': 12
}


def parse_indonesian_number(text):
    """Rp2.646,14 -> 2646.14"""
    if not text:
        return None
    text = text.strip().replace('Rp', '').strip()
    text = text.replace('.', '').replace(',', '.')
    try:
        return float(text)
    except ValueError:
        return None


def parse_ortax_date(text):
    """'24 July 2026' -> '2026-07-24'"""
    match = re.match(r'(\d+)\s+(\w+)\s+(\d{4})', text.strip())
    if match:
        day, month_name, year = match.groups()
        month = MONTHS_EN.get(month_name)
        if month:
            return f"{year}-{month:02d}-{int(day):02d}"
    return None


# ============================================================
# 1. Ortax 印尼央行汇率 (CNY + USD)
# ============================================================
def scrape_ortax(currency='CNY', max_pages=30):
    """
    抓取 Ortax 印尼央行指定币种中间价
    currency: 'CNY' 或 'USD'
    返回: [{'date': '2026-07-24', 'rate': 2646.14, 'rate_inverse': 0.000378...}, ...]
    """
    print(f"[Ortax] 开始抓取印尼央行{currency}中间价...")
    all_rates = []
    seen_dates = set()

    for page in range(1, max_pages + 1):
        url = f"https://datacenter.ortax.org/ortax/kursbi/show/{currency}?page={page}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            html = resp.text

            # 用正则提取日期和Rp数值
            dates = re.findall(r'(\d+\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})', html)
            rp_values = re.findall(r'Rp([\d.]+,\d+)', html)

            if not rp_values:
                print(f"  第{page}页: 无数据，停止")
                break

            # 每行有3个Rp值 (Jual, Beli, Tengah)，取第3个
            # 每行有2个日期 (start, end)，取第1个
            # 注意: 页面有桌面+移动两份重复数据，需要去重
            page_rates = []
            page_seen = set()
            for i in range(0, len(rp_values), 3):
                if i + 2 < len(rp_values):
                    tengah = parse_indonesian_number(rp_values[i + 2])
                    date_idx = i // 3 * 2
                    if date_idx < len(dates):
                        date_str = parse_ortax_date(dates[date_idx])
                        if date_str and tengah and date_str not in page_seen:
                            page_seen.add(date_str)
                            page_rates.append({
                                'date': date_str,
                                'rate': tengah,
                                'rate_inverse': round(1 / tengah, 12)
                            })

            if not page_rates:
                print(f"  第{page}页: 解析无结果，停止")
                break

            # 全局去重
            new_rates = [r for r in page_rates if r['date'] not in seen_dates]
            for r in new_rates:
                seen_dates.add(r['date'])
            all_rates.extend(new_rates)

            print(f"  第{page}页: 获取{len(new_rates)}条新记录 (累计{len(all_rates)}条)")

            if len(new_rates) == 0:
                break

        except Exception as e:
            print(f"  第{page}页错误: {e}")
            break

    all_rates.sort(key=lambda x: x['date'], reverse=True)
    if all_rates:
        print(f"[Ortax] {currency}完成: 共{len(all_rates)}条, {all_rates[-1]['date']}~{all_rates[0]['date']}")
    else:
        print(f"[Ortax] {currency}无数据")
    return all_rates


def scrape_ortax_cny(max_pages=30):
    """抓取CNY中间价 (兼容接口)"""
    return scrape_ortax('CNY', max_pages)


def scrape_ortax_usd(max_pages=30):
    """抓取USD中间价"""
    return scrape_ortax('USD', max_pages)


# ============================================================
# 2. SAFE 各种货币对美元折算率
# ============================================================
def scrape_safe_converter_list():
    """获取SAFE折算率报告列表"""
    print("[SAFE折算率] 获取报告列表...")
    url = "https://www.safe.gov.cn/safe/gzhbdmyzslb/index.html"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'lxml')

        reports = []
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            href = link['href']
            if '各种货币对美元折算率' in text and '.html' in href:
                date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
                if date_match:
                    date_str = f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
                    full_url = href if href.startswith('http') else f"https://www.safe.gov.cn{href}"
                    reports.append({'title': text, 'date': date_str, 'url': full_url})

        reports.sort(key=lambda x: x['date'], reverse=True)
        print(f"[SAFE折算率] 找到{len(reports)}期报告")
        return reports
    except Exception as e:
        print(f"[SAFE折算率] 错误: {e}")
        return []


def download_safe_converter(report_url):
    """下载并解析SAFE折算率xlsx，返回货币折算率字典"""
    print(f"  下载: {report_url}")
    try:
        resp = requests.get(report_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'lxml')

        xlsx_link = soup.find('a', href=re.compile(r'\.xlsx'))
        if not xlsx_link:
            print(f"  未找到xlsx链接")
            return None

        xlsx_url = xlsx_link['href']
        if not xlsx_url.startswith('http'):
            xlsx_url = f"https://www.safe.gov.cn{xlsx_url}"

        # 下载xlsx
        xlsx_resp = requests.get(xlsx_url, headers=HEADERS, timeout=60)
        xlsx_resp.raise_for_status()

        # 解析xlsx
        wb = openpyxl.load_workbook(io.BytesIO(xlsx_resp.content), data_only=True)
        ws = wb.active

        rates = {}
        for row in ws.iter_rows(min_row=1, values_only=False):
            # 两列结构: B/C/D/E 和 F/G/H/I
            for col_start in [2, 6]:  # B列和F列
                code_cell = row[col_start - 1] if col_start - 1 < len(row) else None
                if code_cell and code_cell.value and len(str(code_cell.value)) == 3:
                    code = str(code_cell.value).strip()
                    rate_cell = row[col_start + 2] if col_start + 2 < len(row) else None  # E列或I列
                    if rate_cell and rate_cell.value:
                        try:
                            rate = float(rate_cell.value)
                            rates[code] = rate
                        except (ValueError, TypeError):
                            pass

        print(f"  解析完成: {len(rates)}种货币")
        return rates

    except Exception as e:
        print(f"  错误: {e}")
        return None


def scrape_safe_converter(months_back=12):
    """抓取最近N个月的SAFE折算率"""
    reports = scrape_safe_converter_list()
    all_data = {}

    for report in reports[:months_back]:
        rates = download_safe_converter(report['url'])
        if rates:
            all_data[report['date']] = rates

    return all_data


# ============================================================
# 3. SAFE 人民币汇率中间价
# ============================================================
def scrape_safe_rmb_rate(start_date, end_date):
    """
    抓取SAFE人民币汇率中间价
    返回: (rates_list, headers_list)
    rates_list: [{'date': '2026-07-24', '美元': 679.39, '欧元': 772.37, ...}, ...]
    headers_list: ['日期', '美元', '欧元', ...]
    """
    print(f"[SAFE人民币] 查询 {start_date} ~ {end_date}")

    # SAFE限制每次查询不超过366天
    all_rates = []
    headers = []
    current_start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    while current_start <= end:
        current_end = min(current_start + timedelta(days=366), end)
        start_str = current_start.strftime('%Y-%m-%d')
        end_str = current_end.strftime('%Y-%m-%d')

        print(f"  查询: {start_str} ~ {end_str}")

        try:
            resp = requests.post(
                "https://www.safe.gov.cn/AppStructured/hlw/RMBQuery.do",
                data={'startDate': start_str, 'endDate': end_str, 'queryYN': 'true'},
                headers={**HEADERS, 'Content-Type': 'application/x-www-form-urlencoded',
                         'Referer': 'https://www.safe.gov.cn/safe/rmbhlzjj/index.html'},
                timeout=30
            )
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'lxml')

            tables = soup.find_all('table')
            if not tables:
                print(f"    无表格")
                current_start = current_end + timedelta(days=1)
                continue

            # 使用最后一个表格 (数据表)
            table = tables[-1]
            rows = table.find_all('tr')

            if not headers:
                header_row = rows[0]
                headers = [cell.get_text(strip=True) for cell in header_row.find_all(['th', 'td'])]

            for row in rows[1:]:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    date_text = cells[0].get_text(strip=True)
                    date_match = re.match(r'(\d{4}-\d{2}-\d{2})', date_text)
                    if date_match:
                        date = date_match.group(1)
                        rate_data = {'date': date}
                        for i, cell in enumerate(cells[1:], 1):
                            if i < len(headers):
                                col_name = headers[i]
                                value_text = cell.get_text(strip=True)
                                try:
                                    rate_data[col_name] = float(value_text)
                                except ValueError:
                                    rate_data[col_name] = value_text
                        all_rates.append(rate_data)

            print(f"    获取{len([r for r in all_rates if start_str <= r['date'] <= end_str])}条记录")

        except Exception as e:
            print(f"    错误: {e}")

        current_start = current_end + timedelta(days=1)

    # 去重并排序
    seen = set()
    unique_rates = []
    for r in all_rates:
        if r['date'] not in seen:
            seen.add(r['date'])
            unique_rates.append(r)
    unique_rates.sort(key=lambda x: x['date'], reverse=True)

    print(f"[SAFE人民币] 完成: 共{len(unique_rates)}条记录" if unique_rates else "[SAFE人民币] 无数据")
    if unique_rates:
        print(f"  日期范围: {unique_rates[-1]['date']}~{unique_rates[0]['date']}")
        print(f"  最新: {unique_rates[0]}")

    return unique_rates, headers


# ============================================================
# 主入口
# ============================================================
if __name__ == '__main__':
    from holidays import is_holiday

    # 测试 Ortax
    ortax = scrape_ortax_cny(max_pages=3)
    print(f"\nOrtax样本: {ortax[:3] if ortax else '无'}")

    # 测试 SAFE折算率
    converter = scrape_safe_converter(months_back=1)
    print(f"\nSAFE折算率: {len(converter)}期")
    for date_str, rates in converter.items():
        print(f"  {date_str}: CNY={rates.get('CNY')}, USD=1, EUR={rates.get('EUR')}")

    # 测试 SAFE人民币中间价
    end = datetime.now().strftime('%Y-%m-%d')
    start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    rmb_rates, rmb_headers = scrape_safe_rmb_rate(start, end)
    print(f"\nSAFE人民币: {len(rmb_rates)}条, headers={rmb_headers}")

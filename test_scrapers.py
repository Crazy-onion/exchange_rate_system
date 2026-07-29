"""
汇率数据抓取模块 - 测试脚本
测试三个数据源的抓取能力
"""
import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime, timedelta

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


def parse_indonesian_number(text):
    """解析印尼数字格式: Rp2.646,14 -> 2646.14"""
    if not text:
        return None
    text = text.strip()
    text = text.replace('Rp', '').strip()
    text = text.replace('.', '').replace(',', '.')
    try:
        return float(text)
    except ValueError:
        return None


def parse_ortax_date(text):
    """解析Ortax日期格式: '24 July 2026 - 25 July 2026' -> '2026-07-24'"""
    if not text:
        return None
    text = text.strip()
    # 取第一个日期 (Masa Berlaku 起始日)
    match = re.match(r'(\d+)\s+(\w+)\s+(\d{4})', text)
    if match:
        day, month_name, year = match.groups()
        months = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4,
            'May': 5, 'June': 6, 'July': 7, 'August': 8,
            'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        month = months.get(month_name)
        if month:
            return f"{year}-{month:02d}-{int(day):02d}"
    return None


def scrape_ortax_cny(max_pages=25):
    """抓取Ortax印尼央行CNY中间价"""
    print("\n=== 抓取 Ortax 印尼央行 CNY 汇率 ===")
    all_rates = []
    
    for page in range(1, max_pages + 1):
        url = f"https://datacenter.ortax.org/ortax/kursbi/show/CNY?page={page}"
        print(f"  第 {page} 页: {url}")
        
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')
            
            # 查找数据表格
            table = soup.find('table')
            if not table:
                print(f"    未找到表格，停止")
                break
            
            rows = table.find_all('tr')
            page_count = 0
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    date_text = cells[0].get_text(strip=True)
                    kurs_tengah_text = cells[3].get_text(strip=True)
                    
                    if 'Kurs Tengah' in kurs_tengah_text or not date_text or 'Masa Berlaku' in date_text:
                        continue
                    
                    date = parse_ortax_date(date_text)
                    rate = parse_indonesian_number(kurs_tengah_text)
                    
                    if date and rate:
                        all_rates.append({
                            'date': date,
                            'rate': rate,
                            'rate_inverse': round(1 / rate, 12) if rate else None
                        })
                        page_count += 1
            
            print(f"    获取 {page_count} 条记录")
            
            if page_count == 0:
                print(f"    无数据，停止")
                break
                
        except Exception as e:
            print(f"    错误: {e}")
            break
    
    print(f"  总计获取 {len(all_rates)} 条CNY中间价记录")
    if all_rates:
        print(f"  日期范围: {all_rates[-1]['date']} ~ {all_rates[0]['date']}")
        print(f"  最新汇率: {all_rates[0]['rate']} (1/{all_rates[0]['rate']:.10f})")
    
    return all_rates


def scrape_safe_converter():
    """抓取SAFE各种货币对美元折算率列表"""
    print("\n=== 抓取 SAFE 各种货币对美元折算率列表 ===")
    url = "https://www.safe.gov.cn/safe/gzhbdmyzslb/index.html"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'lxml')
        
        # 查找列表
        links = soup.find_all('a', href=True)
        reports = []
        for link in links:
            href = link['href']
            text = link.get_text(strip=True)
            if '各种货币对美元折算率' in text and '.html' in href:
                # 提取日期
                date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
                if date_match:
                    date_str = f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
                    full_url = href if href.startswith('http') else f"https://www.safe.gov.cn{href}"
                    reports.append({
                        'title': text,
                        'date': date_str,
                        'url': full_url
                    })
        
        print(f"  找到 {len(reports)} 期折算率报告")
        for r in reports[:5]:
            print(f"    {r['date']}: {r['url']}")
        
        return reports
        
    except Exception as e:
        print(f"  错误: {e}")
        return []


def download_safe_converter_xlsx(report_url):
    """下载并解析SAFE折算率xlsx文件"""
    print(f"\n  下载折算率文件: {report_url}")
    
    try:
        resp = requests.get(report_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        
        # 查找xlsx下载链接
        soup = BeautifulSoup(resp.text, 'lxml')
        xlsx_link = soup.find('a', href=re.compile(r'\.xlsx'))
        
        if xlsx_link:
            xlsx_url = xlsx_link['href']
            if not xlsx_url.startswith('http'):
                xlsx_url = f"https://www.safe.gov.cn{xlsx_url}"
            print(f"  xlsx下载链接: {xlsx_url}")
            return xlsx_url
        else:
            print(f"  未找到xlsx下载链接")
            return None
            
    except Exception as e:
        print(f"  错误: {e}")
        return None


def scrape_safe_rmb_rate(start_date, end_date):
    """抓取SAFE人民币汇率中间价"""
    print(f"\n=== 抓取 SAFE 人民币汇率中间价 ({start_date} ~ {end_date}) ===")
    
    # SAFE的AJAX查询接口
    url = "https://www.safe.gov.cn/AppStructured/hlw/RMBQuery.do"
    
    data = {
        'startDate': start_date,
        'endDate': end_date,
        'queryYN': 'true'
    }
    
    try:
        resp = requests.post(url, data=data, headers={
            **HEADERS,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://www.safe.gov.cn/safe/rmbhlzjj/index.html'
        }, timeout=30)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        
        soup = BeautifulSoup(resp.text, 'lxml')
        
        # 查找数据表格
        table = soup.find('table')
        if not table:
            # 尝试查找所有表格
            tables = soup.find_all('table')
            print(f"  找到 {len(tables)} 个表格")
            if tables:
                table = tables[-1]  # 通常数据在最后一个表格
        
        if not table:
            print(f"  未找到数据表格")
            print(f"  响应长度: {len(resp.text)}")
            # 打印部分响应以调试
            print(f"  响应前500字符: {resp.text[:500]}")
            return []
        
        rows = table.find_all('tr')
        print(f"  表格行数: {len(rows)}")
        
        # 解析表头
        header_row = rows[0]
        headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        print(f"  表头: {headers}")
        
        # 解析数据行
        all_rates = []
        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) >= 2:
                date_text = cells[0].get_text(strip=True)
                # 解析日期
                date_match = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_text)
                if date_match:
                    date = date_match.group(0)
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
        
        print(f"  获取 {len(all_rates)} 条记录")
        if all_rates:
            print(f"  日期范围: {all_rates[-1]['date']} ~ {all_rates[0]['date']}")
            print(f"  最新记录: {all_rates[0]}")
        
        return all_rates, headers
        
    except Exception as e:
        print(f"  错误: {e}")
        return [], []


if __name__ == '__main__':
    # 测试1: Ortax
    ortax_rates = scrape_ortax_cny(max_pages=3)
    
    # 测试2: SAFE折算率列表
    converter_reports = scrape_safe_converter()
    if converter_reports:
        # 测试下载最新一期
        xlsx_url = download_safe_converter_xlsx(converter_reports[0]['url'])
    
    # 测试3: SAFE人民币中间价
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    rmb_rates, rmb_headers = scrape_safe_rmb_rate(start_date, end_date)

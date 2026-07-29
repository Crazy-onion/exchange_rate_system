"""
HTML 看板生成模块
生成交互式汇率波动看板，支持：
- 选币种查看历史趋势
- 截止日期选择
- 历史明细表含币种名称
- 单一币种/全部币种 CSV 导出
"""
import json
import os
from datetime import datetime


def generate_dashboard(output_path, ortax_cny, ortax_usd, rmb_rates, rmb_headers, converter_data,
                       excel_filename=None, excel_files=None, auth_password='exchange2026',
                       update_time=None):
    """
    生成HTML看板
    auth_password: 访问密码，默认 exchange2026
    """
    print(f"\n[看板] 生成HTML看板: {output_path}")

    # 准备数据
    rmb_data = []
    for r in sorted(rmb_rates, key=lambda x: x['date']):
        row = {'date': r['date']}
        for h in rmb_headers[1:]:
            if h in r and isinstance(r[h], (int, float)):
                row[h] = r[h]
        rmb_data.append(row)

    # 每个币种独立的时间序列（用于按币种标注真实数据日期 / 滞后识别）
    rmb_by_currency = {}
    for r in rmb_rates:
        d = r['date']
        for h in rmb_headers[1:]:
            if h in r and isinstance(r[h], (int, float)):
                rmb_by_currency.setdefault(h, []).append({'date': d, 'rate': r[h]})
    for k in rmb_by_currency:
        rmb_by_currency[k].sort(key=lambda x: x['date'])

    ortax_data = {
        'CNY': [{'date': r['date'], 'rate': r['rate']} for r in sorted(ortax_cny, key=lambda x: x['date'])],
        'USD': [{'date': r['date'], 'rate': r['rate']} for r in sorted(ortax_usd, key=lambda x: x['date'])] if ortax_usd else []
    }

    converter_json = {}
    for date_str, rates in converter_data.items():
        converter_json[date_str] = rates

    currencies = rmb_headers[1:] if rmb_headers else []
    if update_time is None:
        update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    html = _build_html(
        rmb_data, rmb_by_currency, ortax_data, converter_json, currencies,
        update_time, excel_filename, excel_files or [], auth_password
    )

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    # 写入独立 data.json，供"手动实时更新"按钮按需拉取最新数据
    all_dates = []
    if rmb_data:
        all_dates.extend([r['date'] for r in rmb_data])
    if ortax_data.get('CNY'):
        all_dates.extend([r['date'] for r in ortax_data['CNY']])
    all_dates.sort()
    data_min = all_dates[0] if all_dates else '2025-01-01'
    data_max = update_time[:10] if update_time else (all_dates[-1] if all_dates else '2026-01-01')

    currency_names_map = {
        '美元': 'USD', '欧元': 'EUR', '日元': 'JPY', '港元': 'HKD',
        '英镑': 'GBP', '澳元': 'AUD', '新西兰元': 'NZD', '新加坡元': 'SGD',
        '瑞士法郎': 'CHF', '加元': 'CAD', '澳门元': 'MOP', '林吉特': 'MYR',
        '卢布': 'RUB', '兰特': 'ZAR', '韩元': 'KRW', '迪拉姆': 'AED',
        '里亚尔': 'SAR', '福林': 'HUF', '兹罗提': 'PLN', '丹麦克朗': 'DKK',
        '瑞典克朗': 'SEK', '挪威克朗': 'NOK', '里拉': 'TRY', '比索': 'MXN', '泰铢': 'THB'
    }
    indirect_set = {'澳门元', '林吉特', '卢布', '兰特', '韩元', '迪拉姆', '里亚尔',
                    '福林', '兹罗提', '丹麦克朗', '瑞典克朗', '挪威克朗', '里拉', '比索', '泰铢'}
    quote_info_map = {}
    for name in currencies:
        if name in indirect_set:
            quote_info_map[name] = {'type': 'indirect', 'desc': '间接标价法：100人民币折合外币'}
        else:
            quote_info_map[name] = {'type': 'direct', 'desc': '直接标价法：100外币折合人民币'}

    data_payload = {
        'rmbData': rmb_data,
        'rmbByCurrency': rmb_by_currency,
        'ortaxData': ortax_data,
        'converterData': converter_data,
        'currencies': currencies,
        'currencyNames': currency_names_map,
        'quoteInfo': quote_info_map,
        'excelFiles': excel_files or [],
        'updateTime': update_time,
        'minDate': data_min,
        'maxDate': data_max,
    }
    data_path = os.path.join(os.path.dirname(os.path.abspath(output_path)), 'data.json')
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(data_payload, f, ensure_ascii=False, default=str)
    print(f"[看板] 数据文件已写入: {data_path}")

    print(f"[看板] 完成: {output_path}")
    return output_path


def _build_html(rmb_data, rmb_by_currency, ortax_data, converter_data, currencies,
                update_time, excel_filename, excel_files, auth_password):
    """构建完整HTML - 密码门控 + 直接JSON嵌入（可靠稳定）"""

    rmb_json = json.dumps(rmb_data, ensure_ascii=False)
    rmb_by_currency_json = json.dumps(rmb_by_currency, ensure_ascii=False)
    ortax_json = json.dumps(ortax_data, ensure_ascii=False)
    converter_json = json.dumps(converter_data, ensure_ascii=False)
    currencies_json = json.dumps(currencies, ensure_ascii=False)
    excel_files_json = json.dumps(excel_files, ensure_ascii=False)

    currency_names = {
        '美元': 'USD', '欧元': 'EUR', '日元': 'JPY', '港元': 'HKD',
        '英镑': 'GBP', '澳元': 'AUD', '新西兰元': 'NZD', '新加坡元': 'SGD',
        '瑞士法郎': 'CHF', '加元': 'CAD', '澳门元': 'MOP', '林吉特': 'MYR',
        '卢布': 'RUB', '兰特': 'ZAR', '韩元': 'KRW', '迪拉姆': 'AED',
        '里亚尔': 'SAR', '福林': 'HUF', '兹罗提': 'PLN', '丹麦克朗': 'DKK',
        '瑞典克朗': 'SEK', '挪威克朗': 'NOK', '里拉': 'TRY', '比索': 'MXN', '泰铢': 'THB'
    }
    currency_names_json = json.dumps(currency_names, ensure_ascii=False)

    # 报价方式备注（依据SAFE官网说明）
    # 间接标价法：100人民币折合多少外币（15种）
    # 直接标价法：100外币折合多少人民币（其余10种）
    indirect_currencies = {'澳门元', '林吉特', '卢布', '兰特', '韩元', '迪拉姆', '里亚尔',
                           '福林', '兹罗提', '丹麦克朗', '瑞典克朗', '挪威克朗', '里拉', '比索', '泰铢'}
    quote_info = {}
    for name in currencies:
        if name in indirect_currencies:
            quote_info[name] = {'type': 'indirect', 'desc': '间接标价法：100人民币折合外币'}
        else:
            quote_info[name] = {'type': 'direct', 'desc': '直接标价法：100外币折合人民币'}
    quote_info_json = json.dumps(quote_info, ensure_ascii=False)

    all_dates = []
    if rmb_data:
        all_dates.extend([r['date'] for r in rmb_data])
    if ortax_data.get('CNY'):
        all_dates.extend([r['date'] for r in ortax_data['CNY']])
    all_dates.sort()
    min_date = all_dates[0] if all_dates else '2025-01-01'
    # 选择器上限取"今天"，而非数据最新日，避免数据滞后时无法选到当天
    max_date = update_time[:10] if update_time else (all_dates[-1] if all_dates else '2026-01-01')

    excel_link = '<a href="#" id="downloadLink" class="btn-download" download>下载汇率底稿Excel</a>'

    template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>汇率波动看板</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, "Microsoft YaHei", sans-serif; background: #f0f2f5; color: #333; }
.header { background: linear-gradient(135deg, #1a237e 0%, #283593 100%); color: white; padding: 20px 30px; }
.header h1 { font-size: 22px; font-weight: 500; }
.header .subtitle { font-size: 13px; opacity: 0.8; margin-top: 4px; }
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.section { background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.section-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; color: #1a237e; border-left: 4px solid #1a237e; padding-left: 12px; }
.rates-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
.rate-card { background: #f8f9ff; border: 1px solid #e3e6f3; border-radius: 8px; padding: 14px; text-align: center; transition: transform 0.15s; }
.rate-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(26,35,126,0.1); }
.rate-code { font-size: 18px; font-weight: 700; color: #1a237e; }
.rate-name { font-size: 12px; color: #666; margin: 4px 0; }
.rate-value { font-size: 16px; font-weight: 600; color: #c62828; }
.rate-quote { font-size: 10px; color: #999; margin-top: 5px; line-height: 1.3; }
.rate-asof { font-size: 10px; color: #999; margin-top: 5px; }
.rate-asof.lag { color: #e65100; font-weight: 600; }
.rate-card.card-lag { border-color: #ffb74d; background: #fff8e1; }
.ortax-card.card-lag { border-color: #ffb74d; background: #fff3e0; }
.ortax-section { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.ortax-card { background: #fff8e1; border: 1px solid #ffe082; border-radius: 8px; padding: 16px; text-align: center; }
.ortax-card .label { font-size: 13px; color: #666; }
.ortax-card .value { font-size: 24px; font-weight: 700; color: #e65100; margin: 8px 0; }
.ortax-card .sub { font-size: 11px; color: #999; }
.controls { display: flex; gap: 10px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.controls label { font-size: 14px; font-weight: 500; white-space: nowrap; }
.controls select, .controls input[type="date"] { padding: 7px 14px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; background: white; cursor: pointer; }
.controls select:focus, .controls input[type="date"]:focus { outline: none; border-color: #1a237e; }
.preset-btns { display: flex; gap: 6px; flex-wrap: wrap; }
.preset-btn { padding: 6px 12px; border: 1px solid #c5cae9; border-radius: 6px; background: #e8eaf6; color: #1a237e; font-size: 12px; cursor: pointer; transition: all 0.15s; }
.preset-btn:hover { background: #c5cae9; }
.preset-btn.active { background: #1a237e; color: white; border-color: #1a237e; }
.chart-container { position: relative; height: 400px; }
.info-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.update-time { font-size: 12px; color: #999; }
.btn-download { display: inline-block; padding: 8px 20px; background: #c62828; color: white; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: 500; transition: background 0.15s; }
.btn-download:hover { background: #b71c1c; }
.refresh-note { font-size: 12px; color: #b26a00; background: #fff8e1; border-left: 3px solid #ffb300; padding: 8px 12px; margin-bottom: 14px; border-radius: 4px; line-height: 1.6; }
.refresh-note b { color: #e65100; }
.btn-export { display: inline-block; padding: 6px 16px; border: 1px solid #1a237e; background: white; color: #1a237e; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.15s; }
.btn-export:hover { background: #e8eaf6; }
.stats-row { display: flex; gap: 20px; margin-top: 12px; }
.stat-item { flex: 1; text-align: center; padding: 12px; background: #f5f5f5; border-radius: 8px; }
.stat-item .stat-label { font-size: 12px; color: #666; }
.stat-item .stat-value { font-size: 18px; font-weight: 700; margin-top: 4px; }
.stat-up { color: #c62828; }
.stat-down { color: #2e7d32; }
.chart-quote { font-size: 12px; color: #999; margin-top: 8px; }
.stat-note { font-size: 12px; color: #999; margin-top: 8px; }
table { width: 100%; border-collapse: collapse; }
table th, table td { padding: 8px 12px; text-align: right; border-bottom: 1px solid #eee; font-size: 13px; }
table th { background: #f8f9ff; color: #1a237e; font-weight: 600; text-align: right; }
table th:first-child, table td:first-child { text-align: left; }
table tr:hover { background: #f8f9ff; }
.footer { text-align: center; padding: 20px; font-size: 12px; color: #999; }
.cutoff-info { display: inline-block; margin-left: 8px; padding: 4px 12px; background: #fff3e0; border: 1px solid #ffb74d; border-radius: 6px; font-size: 13px; color: #e65100; font-weight: 500; }
.table-toolbar { display: flex; gap: 10px; justify-content: flex-end; margin-bottom: 12px; }
.sub-title { font-size: 13px; font-weight: 600; color: #283593; margin: 16px 0 8px; }
.sub-title:first-of-type { margin-top: 4px; }
</style>
</head>
<body>

<div class="header">
  <h1>汇率波动看板</h1>
  <div class="subtitle">数据来源：SAFE国家外汇管理局 / Ortax印尼央行</div>
</div>

<div class="container">
  <div class="info-bar">
    <div class="update-time">自动更新：<span id="autoUpdateTime">__UPDATE_TIME__</span> ｜ 手动更新：<span id="manualUpdateTime">尚未手动更新</span></div>
    <div style="display:flex; gap:10px; align-items:center;">
      __EXCEL_LINK__
      <button class="btn-download" id="refreshBtn" style="background:#283593;" onclick="manualRefresh()">手动实时更新</button>
    </div>
  </div>

  <div class="refresh-note" id="refreshNote">提示：点击「手动实时更新」仅刷新本页展示数据，<b>底稿 Excel 不会同步更新</b>。如需下载最新底稿 Excel，请联系管理员在 GitHub Actions 触发更新后再下载。</div>

  <div class="section">
    <div class="section-title">日期选择</div>
    <div class="controls">
      <label>截止日期：</label>
      <input type="date" id="cutoffDate" min="__MIN_DATE__" max="__MAX_DATE__" value="__MAX_DATE__" onchange="onCutoffChange()">
      <div class="preset-btns" id="presetBtns"></div>
    </div>
    <div style="font-size: 13px; color: #666; margin-top: 4px;">
      <span>当前查看：<span class="cutoff-info" id="cutoffDisplay">__MAX_DATE__</span></span>
      <span style="margin-left: 12px;">该日无数据或某币种尚未发布时，自动取最近一个已发布工作日的汇率，并在卡片上标注实际数据日期（滞后会标红）</span>
    </div>
  </div>

  <div class="section">
    <div class="section-title">印尼央行汇率 (IDR) <span id="ortaxDateLabel" style="font-size:12px;color:#999;font-weight:400;"></span></div>
    <div class="ortax-section" id="ortaxSection"></div>
  </div>

  <div class="section">
    <div class="section-title">人民币汇率中间价 <span id="rmbDateLabel" style="font-size:12px;color:#999;font-weight:400;"></span></div>
    <div class="sub-title">直接标价法（100外币折合人民币）</div>
    <div class="rates-grid" id="ratesGridDirect"></div>
    <div class="sub-title">间接标价法（100人民币折合外币）</div>
    <div class="rates-grid" id="ratesGridIndirect"></div>
  </div>

  <div class="section">
    <div class="section-title">汇率趋势图</div>
    <div class="controls">
      <label>选择币种：</label>
      <select id="currencySelect" onchange="updateChart()">
        <option value="ortax_cny">印尼央行 CNY/IDR</option>
        <option value="ortax_usd">印尼央行 USD/IDR</option>
      </select>
      <label>显示范围：</label>
      <select id="rangeSelect" onchange="updateChart()">
        <option value="30">截止日前30天</option>
        <option value="90" selected>截止日前90天</option>
        <option value="180">截止日前180天</option>
        <option value="365">截止日前1年</option>
        <option value="all">截止日前全部</option>
      </select>
    </div>
    <div class="chart-container">
      <canvas id="rateChart"></canvas>
    </div>
    <div class="chart-quote" id="chartQuote"></div>
    <div class="stats-row" id="statsRow"></div>
    <div class="stat-note" id="statNote"></div>
  </div>

  <div class="section">
    <div class="section-title">历史数据明细（截止日期前）</div>
    <div class="table-toolbar">
      <button class="btn-export" onclick="exportSingleCurrency()">导出当前币种CSV</button>
      <button class="btn-export" onclick="exportAllCurrencies()">导出全部币种CSV</button>
    </div>
    <div style="max-height: 400px; overflow-y: auto;">
      <table id="dataTable">
        <thead><tr id="tableHeader"></tr></thead>
        <tbody id="tableBody"></tbody>
      </table>
    </div>
  </div>
</div>

<div class="footer">
  汇率底稿自动化系统 | 数据仅供参考，以官方发布为准
</div>

<script>
var rmbData = __RMB_JSON__;
var rmbByCurrency = __RMB_BY_CURRENCY_JSON__;
var ortaxData = __ORTAX_JSON__;
var converterData = __CONVERTER_JSON__;
var currencies = __CURRENCIES_JSON__;
var currencyNames = __CURRENCY_NAMES_JSON__;
var excelFiles = __EXCEL_FILES_JSON__;
var quoteInfo = __QUOTE_INFO_JSON__;
var minDate = '__MIN_DATE__';
var maxDate = '__MAX_DATE__';
var updateTime = '__UPDATE_TIME__';

var chart = null;

// ===================== 初始化 =====================
function rebuildAll() {
  initPresetBtns();
  initCurrencySelect();
  updateRateCards();
  updateChart();
  updateDownloadLink();
  document.getElementById('autoUpdateTime').textContent = updateTime;
}

function initDashboard() {
  rebuildAll();
}

// ===================== 手动实时更新 =====================
function manualRefresh() {
  var btn = document.getElementById('refreshBtn');
  var oldText = btn.textContent;
  btn.textContent = '更新中...';
  btn.disabled = true;
  fetch('data.json?t=' + Date.now(), {cache: 'no-store'})
    .then(function(r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function(d) {
      applyData(d);
      var now = new Date();
      var pad = function(n) { return String(n).padStart(2, '0'); };
      var ts = now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate()) + ' ' +
               pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds());
      document.getElementById('manualUpdateTime').textContent = ts;
      var note = document.getElementById('refreshNote');
      if (note) {
        note.innerHTML = '本页数据已于 ' + ts + ' 刷新（为最近一次已部署数据）。<b>注意：底稿 Excel 未更新</b>，如需最新 Excel，请联系管理员在 GitHub Actions 触发更新后再下载。';
      }
      btn.textContent = oldText;
      btn.disabled = false;
    })
    .catch(function(e) {
      btn.textContent = oldText;
      btn.disabled = false;
      alert('手动更新失败：无法获取最新数据。\\n请确认以网页方式打开（非本地文件），且数据文件已随最新抓取部署。\\n错误：' + e.message);
    });
}

// ===================== 应用数据包（初始 / 刷新） =====================
function applyData(d) {
  rmbData = d.rmbData;
  rmbByCurrency = d.rmbByCurrency;
  ortaxData = d.ortaxData;
  converterData = d.converterData;
  currencies = d.currencies;
  currencyNames = d.currencyNames;
  quoteInfo = d.quoteInfo;
  excelFiles = d.excelFiles;
  updateTime = d.updateTime;
  minDate = d.minDate;
  maxDate = d.maxDate;

  var cd = document.getElementById('cutoffDate');
  cd.min = minDate;
  cd.max = maxDate;
  if (cd.value > maxDate) cd.value = maxDate;
  if (cd.value < minDate) cd.value = minDate;

  var sel = document.getElementById('currencySelect');
  sel.innerHTML = '<option value="ortax_cny">印尼央行 CNY/IDR</option><option value="ortax_usd">印尼央行 USD/IDR</option>';

  rebuildAll();
}

// ===================== 截止日期 =====================
function getCutoffDate() {
  return document.getElementById('cutoffDate').value || maxDate;
}

function getLatestAsOf(data, cutoffStr) {
  var cutoff = new Date(cutoffStr + 'T00:00:00');
  var result = null;
  for (var i = 0; i < data.length; i++) {
    if (new Date(data[i].date + 'T00:00:00') <= cutoff) {
      result = data[i];
    } else {
      break;
    }
  }
  return result;
}

function filterByCutoff(data, cutoffStr) {
  var cutoff = new Date(cutoffStr + 'T00:00:00');
  return data.filter(function(r) { return new Date(r.date + 'T00:00:00') <= cutoff; });
}

function fmtNum(val, decimals) {
  if (val == null || isNaN(val)) return 'N/A';
  return Number(val).toLocaleString(undefined, {maximumFractionDigits: decimals || 4, minimumFractionDigits: decimals || 2});
}

function toDateString(d) {
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

function getLastDayOfMonth(d) {
  return toDateString(new Date(d.getFullYear(), d.getMonth() + 1, 0));
}

// ===================== 预设按钮 =====================
function initPresetBtns() {
  var container = document.getElementById('presetBtns');
  var now = new Date();
  var presets = [
    {label: '最新', date: maxDate},
    {label: '上月末', date: toDateString(new Date(now.getFullYear(), now.getMonth(), 0))},
    {label: '上月初', date: toDateString(new Date(now.getFullYear(), now.getMonth() - 1, 1))},
    {label: '今年初', date: toDateString(new Date(now.getFullYear(), 0, 1))},
    {label: '去年末', date: toDateString(new Date(now.getFullYear() - 1, 11, 31))},
  ];

  for (var i = 0; i < 12; i++) {
    var m = new Date(now.getFullYear(), now.getMonth() - i, 1);
    var monthEnd = getLastDayOfMonth(m);
    if (monthEnd >= minDate) {
      presets.push({label: (m.getFullYear() % 100) + '年' + (m.getMonth() + 1) + '月末', date: monthEnd, isMonth: true});
    }
  }

  container.innerHTML = '';
  presets.forEach(function(p) {
    var btn = document.createElement('button');
    btn.className = 'preset-btn' + (p.isMonth ? ' month-btn' : '');
    btn.textContent = p.label;
    btn.onclick = function() {
      document.getElementById('cutoffDate').value = p.date;
      onCutoffChange();
      document.querySelectorAll('.preset-btn').forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
    };
    container.appendChild(btn);
  });
}

// ===================== 汇率卡片 =====================
function updateRateCards() {
  var cutoff = getCutoffDate();
  document.getElementById('cutoffDisplay').textContent = cutoff;

  var cnyData = getLatestAsOf(ortaxData.CNY || [], cutoff);
  var usdData = getLatestAsOf(ortaxData.USD || [], cutoff);
  var cnyRate = cnyData ? fmtNum(cnyData.rate, 2) : 'N/A';
  var usdRate = usdData ? fmtNum(usdData.rate, 2) : 'N/A';
  var cnyDate = cnyData ? cnyData.date : 'N/A';
  var usdDate = usdData ? usdData.date : 'N/A';
  var cnyLag = (cnyDate !== 'N/A' && cnyDate < cutoff);
  var usdLag = (usdDate !== 'N/A' && usdDate < cutoff);

  document.getElementById('ortaxSection').innerHTML =
    '<div class="ortax-card' + (cnyLag ? ' card-lag' : '') + '">' +
      '<div class="label">CNY 人民币中间价</div>' +
      '<div class="value">' + cnyRate + '</div>' +
      '<div class="sub">1 CNY = ' + cnyRate + ' IDR | 日期：' + cnyDate + (cnyLag ? ' (滞后)' : '') + '</div>' +
    '</div>' +
    '<div class="ortax-card' + (usdLag ? ' card-lag' : '') + '">' +
      '<div class="label">USD 美元中间价</div>' +
      '<div class="value">' + usdRate + '</div>' +
      '<div class="sub">1 USD = ' + usdRate + ' IDR | 日期：' + usdDate + (usdLag ? ' (滞后)' : '') + '</div>' +
    '</div>';

  var ortaxLagNote = [];
  if (cnyLag) ortaxLagNote.push('CNY(' + cnyDate + ')');
  if (usdLag) ortaxLagNote.push('USD(' + usdDate + ')');
  var ortaxLabel = document.getElementById('ortaxDateLabel');
  if (ortaxLagNote.length > 0) {
    ortaxLabel.textContent = '(数据滞后: ' + ortaxLagNote.join('、') + ')';
    ortaxLabel.style.color = '#e65100';
  } else {
    ortaxLabel.textContent = (cnyDate !== 'N/A') ? '(数据日期: ' + cnyDate + ')' : '';
    ortaxLabel.style.color = '#999';
  }

  var gridDirect = document.getElementById('ratesGridDirect');
  var gridIndirect = document.getElementById('ratesGridIndirect');

  var cardsDirect = '';
  var cardsIndirect = '';
  var laggedList = [];
  var maxAsOf = '';
  var hasAnyData = false;
  for (var i = 0; i < currencies.length; i++) {
    var name = currencies[i];
    var code = currencyNames[name] || name;
    var series = rmbByCurrency[name] || [];
    var pt = getLatestAsOf(series, cutoff);
    var val = pt ? pt.rate : null;
    var asOf = pt ? pt.date : null;
    if (val != null && !isNaN(val)) hasAnyData = true;
    var valStr = (val != null && !isNaN(val)) ? fmtNum(val, 4) : 'N/A';
    var q = quoteInfo[name];
    var quoteStr = q ? q.desc : '';
    var isLag = (asOf && asOf < cutoff);
    if (isLag) {
      laggedList.push(name + '(' + asOf + ')');
    }
    if (asOf && asOf > maxAsOf) maxAsOf = asOf;
    var asOfHtml = asOf
      ? '<div class="rate-asof' + (isLag ? ' lag' : '') + '">数据日期: ' + asOf + (isLag ? ' (滞后)' : '') + '</div>'
      : '<div class="rate-asof">无数据</div>';
    var card = '<div class="rate-card' + (isLag ? ' card-lag' : '') + '"><div class="rate-code">' + code + '</div><div class="rate-name">' + name + '</div><div class="rate-value">' + valStr + '</div><div class="rate-quote">' + quoteStr + '</div>' + asOfHtml + '</div>';
    if (q && q.type === 'indirect') {
      cardsIndirect += card;
    } else {
      cardsDirect += card;
    }
  }

  if (!hasAnyData) {
    gridDirect.innerHTML = '<div style="color:#999;padding:20px;">该日期范围内无数据</div>';
    gridIndirect.innerHTML = '';
    document.getElementById('rmbDateLabel').textContent = '';
    return;
  }

  gridDirect.innerHTML = cardsDirect;
  gridIndirect.innerHTML = cardsIndirect;

  var rmbLabel = document.getElementById('rmbDateLabel');
  if (laggedList.length > 0) {
    rmbLabel.textContent = '(部分币种数据滞后: ' + laggedList.join('、') + ')';
    rmbLabel.style.color = '#e65100';
  } else if (maxAsOf) {
    rmbLabel.textContent = '(数据日期: ' + maxAsOf + ')';
    rmbLabel.style.color = '#999';
  } else {
    rmbLabel.textContent = '';
  }
}

// ===================== 币种选择器 =====================
function initCurrencySelect() {
  var select = document.getElementById('currencySelect');
  currencies.forEach(function(c) {
    var opt = document.createElement('option');
    opt.value = 'rmb_' + c;
    opt.textContent = '人民币中间价 - ' + c + ' (' + (currencyNames[c] || c) + ')';
    select.appendChild(opt);
  });
}

// ===================== 图表 =====================
function getQuoteDesc(currencyKey) {
  if (currencyKey === 'ortax_cny') return '1 CNY = X IDR（印尼央行中间价）';
  if (currencyKey === 'ortax_usd') return '1 USD = X IDR（印尼央行中间价）';
  if (currencyKey.indexOf('rmb_') === 0) {
    var n = currencyKey.substring(4);
    return (quoteInfo[n] && quoteInfo[n].desc) ? quoteInfo[n].desc : '';
  }
  return '';
}

function getChartData(currencyKey, range) {
  var data = [];
  var label = '';
  var color = '#1a237e';

  if (currencyKey === 'ortax_cny') {
    data = (ortaxData.CNY || []).slice();
    label = 'CNY/IDR 印尼央行中间价';
    color = '#e65100';
  } else if (currencyKey === 'ortax_usd') {
    data = (ortaxData.USD || []).slice();
    label = 'USD/IDR 印尼央行中间价';
    color = '#1565c0';
  } else if (currencyKey.indexOf('rmb_') === 0) {
    var currencyName = currencyKey.substring(4);
    data = rmbData.map(function(r) { return {date: r.date, rate: r[currencyName]}; }).filter(function(r) { return r.rate != null; });
    label = '人民币中间价 - ' + currencyName + ' (' + (currencyNames[currencyName] || currencyName) + ')';
    color = '#c62828';
  }

  var cutoff = getCutoffDate();
  data = filterByCutoff(data, cutoff);

  if (range !== 'all') {
    var days = parseInt(range);
    var cutoffDate = new Date(cutoff + 'T00:00:00');
    cutoffDate.setDate(cutoffDate.getDate() - days);
    data = data.filter(function(r) { return new Date(r.date + 'T00:00:00') >= cutoffDate; });
  }

  return { data: data, label: label, color: color };
}

function updateChart() {
  var currencyKey = document.getElementById('currencySelect').value;
  var range = document.getElementById('rangeSelect').value;
  var chartData = getChartData(currencyKey, range);
  var data = chartData.data;
  var label = chartData.label;
  var color = chartData.color;

  var labels = data.map(function(r) { return r.date; });
  var values = data.map(function(r) { return r.rate; });

  var quoteDesc = getQuoteDesc(currencyKey);
  var latestDate = data.length ? data[data.length - 1].date : 'N/A';
  var note = (quoteDesc ? ('注：' + quoteDesc) : '') + (data.length ? (' ｜ 最新数据日期: ' + latestDate) : '');
  document.getElementById('chartQuote').textContent = quoteDesc ? ('注：' + quoteDesc) : '';
  document.getElementById('statNote').textContent = note;

  if (chart) chart.destroy();

  chart = new Chart(document.getElementById('rateChart'), {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: label,
        data: values,
        borderColor: color,
        backgroundColor: color + '15',
        borderWidth: 2,
        pointRadius: 2,
        pointHoverRadius: 5,
        fill: true,
        tension: 0.3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        tooltip: {
          callbacks: {
            label: function(ctx) {
              return label + ': ' + ctx.parsed.y.toLocaleString(undefined, {maximumFractionDigits: 6});
            }
          }
        }
      },
      scales: {
        x: { maxTicksLimit: 12, grid: { display: false } },
        y: { grid: { color: '#f0f0f0' } }
      }
    }
  });

  updateStats(data);
  updateTable(data, label, quoteDesc);
}

// ===================== 统计 =====================
function updateStats(data) {
  var statsRow = document.getElementById('statsRow');
  if (data.length === 0) {
    statsRow.innerHTML = '<div class="stat-item"><div class="stat-label">无数据</div><div class="stat-value" style="color:#999;">-</div></div>';
    return;
  }

  var values = data.map(function(r) { return r.rate; });
  var latest = values[values.length - 1];
  var first = values[0];
  var max = Math.max.apply(null, values);
  var min = Math.min.apply(null, values);
  var avg = values.reduce(function(a, b) { return a + b; }, 0) / values.length;
  var change = ((latest - first) / first * 100);
  var changeClass = change >= 0 ? 'stat-up' : 'stat-down';
  var changeSymbol = change >= 0 ? '+' : '';

  statsRow.innerHTML =
    '<div class="stat-item"><div class="stat-label">最新值</div><div class="stat-value">' + latest.toLocaleString(undefined, {maximumFractionDigits: 4}) + '</div></div>' +
    '<div class="stat-item"><div class="stat-label">期间变动</div><div class="stat-value ' + changeClass + '">' + changeSymbol + change.toFixed(2) + '%</div></div>' +
    '<div class="stat-item"><div class="stat-label">最高值</div><div class="stat-value stat-up">' + max.toLocaleString(undefined, {maximumFractionDigits: 4}) + '</div></div>' +
    '<div class="stat-item"><div class="stat-label">最低值</div><div class="stat-value stat-down">' + min.toLocaleString(undefined, {maximumFractionDigits: 4}) + '</div></div>' +
    '<div class="stat-item"><div class="stat-label">平均值</div><div class="stat-value">' + avg.toLocaleString(undefined, {maximumFractionDigits: 4}) + '</div></div>';
}

// ===================== 数据表（含币种名称） =====================
function updateTable(data, currencyLabel, quoteDesc) {
  var header = document.getElementById('tableHeader');
  var body = document.getElementById('tableBody');
  header.innerHTML = '<th>日期</th><th>币种</th><th>汇率</th>';
  var recent = data.slice(-50).reverse();
  var noteHtml = quoteDesc ? '<br><span style="font-size:11px;color:#999;">' + quoteDesc + '</span>' : '';
  body.innerHTML = recent.map(function(r) {
    return '<tr><td>' + r.date + '</td><td style="text-align:left;">' + currencyLabel + noteHtml + '</td><td>' + r.rate.toLocaleString(undefined, {maximumFractionDigits: 6}) + '</td></tr>';
  }).join('');
}

// ===================== CSV 导出 =====================
function downloadCSV(csvContent, filename) {
  var blob = new Blob(['\uFEFF' + csvContent], {type: 'text/csv;charset=utf-8;'});
  var link = document.createElement('a');
  var url = URL.createObjectURL(blob);
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function exportSingleCurrency() {
  var currencyKey = document.getElementById('currencySelect').value;
  var range = document.getElementById('rangeSelect').value;
  var chartData = getChartData(currencyKey, range);
  var data = chartData.data;
  var label = chartData.label;

  var csv = '日期,币种,汇率\\n';
  var quoteDesc = getQuoteDesc(currencyKey);
  var csvLabel = label + (quoteDesc ? '｜' + quoteDesc : '');
  data.forEach(function(r) {
    csv += r.date + ',' + csvLabel + ',' + r.rate + '\\n';
  });

  var cutoff = getCutoffDate();
  var safeLabel = label.replace(/[/\\\\?*:|<>]/g, '_');
  downloadCSV(csv, '汇率数据_' + safeLabel + '_' + cutoff + '.csv');
}

function exportAllCurrencies() {
  var cutoff = getCutoffDate();
  var rmbFiltered = filterByCutoff(rmbData, cutoff);
  var ortaxCnyFiltered = filterByCutoff(ortaxData.CNY || [], cutoff);
  var ortaxUsdFiltered = filterByCutoff(ortaxData.USD || [], cutoff);

  var allDatesSet = {};
  rmbFiltered.forEach(function(r) { allDatesSet[r.date] = true; });
  ortaxCnyFiltered.forEach(function(r) { allDatesSet[r.date] = true; });
  ortaxUsdFiltered.forEach(function(r) { allDatesSet[r.date] = true; });
  var allDates = Object.keys(allDatesSet).sort();

  var header = '日期';
  header += ',印尼央行CNY/IDR,印尼央行USD/IDR';
  currencies.forEach(function(c) {
    header += ',' + c + '(' + (currencyNames[c] || c) + ')';
  });
  header += '\\n';

  var rmbMap = {};
  rmbFiltered.forEach(function(r) { rmbMap[r.date] = r; });
  var cnyMap = {};
  ortaxCnyFiltered.forEach(function(r) { cnyMap[r.date] = r.rate; });
  var usdMap = {};
  ortaxUsdFiltered.forEach(function(r) { usdMap[r.date] = r.rate; });

  var csv = header;
  allDates.forEach(function(d) {
    var row = d;
    row += ',' + (cnyMap[d] != null ? cnyMap[d] : '');
    row += ',' + (usdMap[d] != null ? usdMap[d] : '');
    var rmbRow = rmbMap[d];
    currencies.forEach(function(c) {
      row += ',' + (rmbRow && rmbRow[c] != null ? rmbRow[c] : '');
    });
    csv += row + '\\n';
  });

  downloadCSV(csv, '全部币种汇率数据_' + cutoff + '.csv');
}

// ===================== 截止日期变更 =====================
function onCutoffChange() {
  document.querySelectorAll('.preset-btn').forEach(function(b) { b.classList.remove('active'); });
  updateRateCards();
  updateChart();
  updateDownloadLink();
}

// ===================== 下载链接 =====================
function updateDownloadLink() {
  var cutoff = getCutoffDate();
  var parts = cutoff.split('-');
  var year = parseInt(parts[0]);
  var month = parseInt(parts[1]);
  var filename = '汇率底稿_' + year + String(month).padStart(2, '0') + '.xlsx';
  var link = document.getElementById('downloadLink');

  if (excelFiles.indexOf(filename) >= 0) {
    link.href = filename;
    link.download = filename;
    link.textContent = '下载' + year + '年' + month + '月汇率底稿Excel';
    link.style.opacity = '1';
    link.style.pointerEvents = 'auto';
    link.style.background = '#c62828';
  } else {
    link.href = '#';
    link.textContent = year + '年' + month + '月底稿暂未生成';
    link.style.opacity = '0.5';
    link.style.pointerEvents = 'none';
    link.style.background = '#999';
  }
}

// ===================== 自动初始化 =====================
initDashboard();
</script>
</body>
</html>'''

    # 替换占位符
    html = template
    html = html.replace('__UPDATE_TIME__', update_time)
    html = html.replace('__EXCEL_LINK__', excel_link)
    html = html.replace('__MIN_DATE__', min_date)
    html = html.replace('__MAX_DATE__', max_date)
    html = html.replace('__RMB_JSON__', rmb_json)
    html = html.replace('__RMB_BY_CURRENCY_JSON__', rmb_by_currency_json)
    html = html.replace('__ORTAX_JSON__', ortax_json)
    html = html.replace('__CONVERTER_JSON__', converter_json)
    html = html.replace('__CURRENCIES_JSON__', currencies_json)
    html = html.replace('__CURRENCY_NAMES_JSON__', currency_names_json)
    html = html.replace('__QUOTE_INFO_JSON__', quote_info_json)
    html = html.replace('__EXCEL_FILES_JSON__', excel_files_json)
    html = html.replace('__AUTH_PASSWORD__', auth_password)

    return html

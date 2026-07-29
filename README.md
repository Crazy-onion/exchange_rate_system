# 汇率底稿自动化系统（GitHub Pages 云端版）

自动抓取 **SAFE 国家外汇管理局** 与 **Ortax 印尼央行** 的汇率数据，按模板公式生成 7-Sheet Excel 底稿，并发布为可在线查看的汇率波动看板。

> 本版本不依赖你的电脑在线：抓取、Excel 生成、看板发布全部在 GitHub 云端定时运行。

## 数据源
1. **Ortax 印尼央行**（CNY / USD 中间价）：https://datacenter.ortax.org/ortax/kursbi/list
2. **SAFE 货币折算率**（各货币对美元月末折算率）：https://www.safe.gov.cn/safe/gzhbdmyzslb/index.html
3. **SAFE 人民币中间价**（每日中间价，25 个币种）：https://www.safe.gov.cn/safe/rmbhlzjj/index.html

## 目录结构
```
exchange_rate_system/
├── .github/workflows/deploy.yml   # GitHub Actions：定时 + 手动触发 + 发布 Pages
├── template/汇率底稿模版.xlsx      # 内置 Excel 模板（已提交，云端可用）
├── scrapers.py                    # 三个数据源抓取
├── holidays.py                    # 中国公众假期
├── excel_generator.py             # 生成 7-Sheet Excel 底稿
├── dashboard.py                   # 生成 HTML 看板 + data.json
├── main.py                        # 主入口：抓取 → Excel → 看板 → dist/
├── regen_all.py                   # 从缓存重新生成（不重新抓取）
├── requirements.txt               # Python 依赖
├── .nojekyll                      # 让 Pages 正确托管 data.json / xlsx
└── dist/                          # 产物：index.html + data.json + 13 个月度 xlsx
```

## 本地运行（可选，用于调试）
```bash
pip install -r requirements.txt
python main.py            # 完整流程：抓取 + 生成
python regen_all.py       # 仅从缓存重新生成（不联网抓取）
```
本地 Excel 模板兜底路径为 `D:\Users\rfuser\Desktop\【发送】汇率底稿模版.xlsx`；仓库内置 `template/` 下的模板优先，因此云端也能运行。

## 发布到 GitHub Pages
1. 在 GitHub 新建一个**空仓库**（如 `exchange-rate-system`）。
2. 将本目录推送上去：
   ```bash
   git remote add origin https://github.com/<你的用户名>/<仓库名>.git
   git branch -M main
   git push -u origin main
   ```
3. 仓库 **Settings → Pages → Source** 选择 **GitHub Actions**。
4. 首次推送后，到 **Actions** 页等 `汇率底稿自动更新` 工作流跑完，Pages 即上线。
5. 站点地址：`https://<你的用户名>.github.io/<仓库名>/`

## 自动化说明
- **定时**：每个工作日 **18:00（北京时间）** 自动抓取 + 生成 + 发布（Workflow `cron: 0 10 * * 1-5`，即 UTC 周一至周五 10:00）。
- **手动触发**：仓库 **Actions → 汇率底稿自动更新 → Run workflow**（可填写触发原因）。用于定时之外随时刷新。
- 注意：GitHub Actions 定时任务可能因平台负载有数分钟至数十分钟延迟，属正常现象。

## 看板上的「手动实时更新」按钮（重要边界）
该按钮仅从已部署的站点**重新拉取最新的 `data.json` 并重绘页面**，它本身**不会去网站重新抓取**。
- 若云端工作流已运行过（定时到点、或你点了 Run workflow），点此按钮即可看到最新数字。
- 若想真正"重新抓取"，请在 GitHub Actions 页点 **Run workflow**，等其完成后刷新页面（或点看板按钮）。
- 因此 **Excel 也只随工作流重新生成而更新**，看板按钮不单独改动 Excel。

## 数据滞后标注
各币种独立取「截止日或之前最近一个已发布工作日」的值，并在卡片标注 `数据日期: X`；若某币种取自更早日期（如当日该汇率尚未发布），卡片标红显示 `(滞后)`，区块标题汇总列出滞后期币种。

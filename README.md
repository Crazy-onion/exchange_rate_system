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

## 启用网页一键更新（可选，推荐手机端）

看板上的「手动实时更新」按钮默认只从已部署站点重新拉取 `data.json` 重绘页面（Excel 不变）。若希望**点一下按钮就真正重新抓取并重算 Excel**（尤其手机打不开 github.com 时），需要一个持有你 GitHub 令牌的云端小函数——Cloudflare Worker。本仓库已提供 `cloudflare-worker.js`，你只需做一次配置。

### 前提：准备一枚 GitHub PAT（令牌）
1. github.com → 右上头像 → **Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (classic)**。
2. Note 填 `exchange-update-worker`；Expiration 选一个较长周期（如 90 天）。
3. **只勾选 `workflow`**（已包含触发 Actions 的权限），其余全部不勾。
4. 点 **Generate token**，复制生成的令牌（只显示一次，存好）。

### 步骤：创建并配置 Cloudflare Worker
1. 打开 https://cloudflare.com 注册/登录（免费）。
2. 左侧菜单 **Workers & Pages**（或 Compute → Workers）→ 点 **Create** → 选 **Create Worker**。
3. Worker 名称填 `exchange-update`，进入在线代码编辑器（默认是 hello world 示例）。
4. **清空编辑器全部内容**，把本仓库 `cloudflare-worker.js` 的**全部内容**粘贴进去 → 点 **Deploy**。
5. 进入该 Worker → 顶部 **Settings → Variables**（或 Runtime）→ 点 **Add variable** 并选择 **Secret** 类型：
   - Name: `GH_TOKEN`　Value: 粘贴刚才复制的 PAT → 保存（加密存储）。
6. 修改 secret 后建议再 **Deploy** 一次使其生效。回到 Worker 概览，复制其地址，形如：
   `https://exchange-update.<你的子域>.workers.dev`
7. 把这个地址发给助手，填进 `config.json` 的 `update_worker_url` 并提交、Push。此后看板按钮即变为**一键云端更新**（触发重抓 + 重算 Excel + 自动刷新）。

### 说明
- 令牌仅存于 Cloudflare 的加密 secret 中，**不进网页、不进仓库**，安全。
- Worker 免费额度（每日 10 万次请求）远超需求。
- 未配置 Worker 前，按钮仍退化为"仅刷新页面"，行为不变。

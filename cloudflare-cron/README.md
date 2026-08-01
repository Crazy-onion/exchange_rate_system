# Cloudflare 定时触发（汇率底稿自动更新）

解决 GitHub Actions 自带 `schedule` 不可靠（会延迟 6~9 小时甚至漏跑）的问题。
改为由 **Cloudflare 服务端定时**调用 GitHub 接口触发更新，免费、稳定、不需要你浏览器访问 workers.dev。

---

## 一、创建 GitHub 令牌（fine-grained PAT）

1. GitHub 右上角头像 → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**
2. Token name：`exchange-rate-cron`（随意）
3. Expiration：自选（建议 1 年，到期前记得换）
4. Resource owner：`Crazy-onion`
5. Repository access：**Only select repositories** → 选 `exchange_rate_system`
6. Repository permissions：
   - **Workflows：Read and write**（触发 workflow 必需）
   - **Contents：Read-only**（让令牌能定位仓库）
7. 点 **Generate token** → **复制 token**（只显示一次，妥善保管）

## 二、在 Cloudflare 建 Worker

1. 控制台 → **Workers & Pages → Create → 新建 Worker**，命名如 `exchange-rate-cron`
2. 把本目录 `worker.js` 的内容**粘贴进编辑器** → **Deploy**
3. （若用命令行：`npx wrangler deploy`，需先 `npx wrangler secret put GH_TOKEN` 设好密钥）

## 三、设置密钥

1. 进入该 Worker → **Settings → Variables**
2. **Add variable**，名称 `GH_TOKEN`，值 = 第一步复制的 PAT，**务必勾选 Secret** → Save

## 四、添加定时触发

1. 该 Worker → **Triggers → Cron Triggers → Add**
2. 添加两条（均为 UTC，等于北京时间 10:30 / 14:30）：
   - `30 2 * * *`
   - `30 6 * * *`
3. Save

> 免费版每个 Worker 支持多个 Cron，无需绑定域名。

## 五、验证

- 在 **Triggers** 页，对应 Cron 右边点 **Test**，可立即触发一次；
- 去 GitHub 仓库 **Actions** 页，应出现一条 `workflow_dispatch` 事件的新运行；
- 跑完看板上「自动更新时间」应变为触发时刻。

---

## 与 GitHub 自带 schedule 的关系

- `deploy.yml` 里原本的 `schedule` 块建议**保留作为冗余备份**（两边同时跑无害，只是偶尔多一次部署）；
  若想完全避免重复，可删掉 `deploy.yml` 的 `schedule` 段，仅由本 Worker 负责定时。
- 本 Worker 的 cron 时间（UTC）与看板抬头标注的「每天 10:30、14:30 自动更新」一致。

// Cloudflare Worker —— 服务端定时触发 GitHub Actions 工作流（汇率底稿自动更新）
//
// 作用：到点在 Cloudflare 服务器上自动调用 GitHub 的 workflow_dispatch 接口，
//       触发仓库的「汇率底稿自动更新」工作流重新抓取+生成 Excel+发布。
// 优点：跑在 Cloudflare 机房，不依赖你本机在线，也不需要你浏览器访问 workers.dev（和之前的"按钮"是两码事）。
//
// 部署（控制台，无需命令行，详见 README.md）：
//   1. Cloudflare 控制台 → Workers & Pages → Create → 新建 Worker（如 exchange-rate-cron）
//   2. 把本文件粘贴进编辑器 → Deploy
//   3. Settings → Variables → 添加 Secret：GH_TOKEN = 你的 GitHub fine-grained PAT（需本仓库 Actions: Read and write 权限，Contents: Read-only）
//   4. Triggers → Cron Triggers → 添加两条：30 2 * * *  和  30 6 * * *（UTC，等于北京 10:30 / 14:30）
//
// 说明：本 Worker 不绑定域名、不暴露公网接口，仅由 Cloudflare 定时调用。

const REPO = 'Crazy-onion/exchange_rate_system';
const WORKFLOW = 'deploy.yml';
const REF = 'main';

async function triggerDispatch(token) {
  if (!token) {
    console.error('GH_TOKEN 未配置（请在 Worker Settings → Variables 里添加 Secret）');
    return { ok: false, error: 'GH_TOKEN missing' };
  }
  const url = `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Accept': 'application/vnd.github+json',
      'Authorization': `Bearer ${token}`,
      'X-GitHub-Api-Version': '2022-11-28',
      'Content-Type': 'application/json',
      'User-Agent': 'cloudflare-cron-trigger'
    },
    body: JSON.stringify({ ref: REF, inputs: { reason: 'Cloudflare定时触发' } })
  });
  const text = await res.text();
  console.log(`GitHub dispatch -> HTTP ${res.status}: ${text}`);
  return { ok: res.status >= 200 && res.status < 300, status: res.status, body: text };
}

// 定时触发（Cron Triggers 调用）
export default {
  async scheduled(event, env) {
    const r = await triggerDispatch(env.GH_TOKEN);
    // 把结果记到日志，便于在 Cloudflare 控制台 → Worker → Logs 里查看
    event.waitUntil(Promise.resolve());
    return new Response(JSON.stringify(r), { status: r.ok ? 200 : 502, headers: { 'content-type': 'application/json' } });
  },
  // 可选：在 Cloudflare 控制台手动 "Send a test request" 时也能触发一次（用于验证）
  async fetch(request, env) {
    const r = await triggerDispatch(env.GH_TOKEN);
    return new Response(JSON.stringify(r), { status: r.ok ? 200 : 502, headers: { 'content-type': 'application/json' } });
  }
};

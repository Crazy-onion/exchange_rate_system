// Cloudflare Worker —— 让网页按钮一键触发 GitHub Actions 工作流（重抓+重生成Excel+发布）
//
// 部署步骤（一次性）：
//   1. 注册 https://cloudflare.com （免费）
//   2. 控制台 → Workers & Pages → Create → 新建一个 Worker（随便起名，如 exchange-update）
//   3. 把本文件内容粘贴进编辑器 → Deploy
//   4. Worker 设置 → Variables → 添加 secret：
//        GH_TOKEN = 你的 GitHub PAT（需勾 workflow/actions:write 权限）
//        （可选）GH_REPO = Crazy-onion/exchange_rate_system
//   5. 部署后得到的地址形如 https://exchange-update.<子域>.workers.dev ，把它发给助手填进看板
//
// 接口：
//   POST /trigger  -> 触发 workflow_dispatch，返回 {ok, run_id, html_url}
//   GET  /status?run_id=xxx -> 返回 {status, conclusion}

export default {
  async fetch(request, env, ctx) {
    const REPO = env.GH_REPO || 'Crazy-onion/exchange_rate_system';
    const WF = 'deploy.yml';
    const TOKEN = env.GH_TOKEN;
    const corsHeaders = {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*'
    };
    const preflightHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      'Access-Control-Max-Age': '86400'
    };

    const url = new URL(request.url);

    // 处理浏览器 CORS 预检请求
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: preflightHeaders });
    }

    if (request.method === 'POST' && url.pathname === '/trigger') {
      if (!TOKEN) {
        return new Response(JSON.stringify({ ok: false, error: 'GH_TOKEN 未配置' }),
          { status: 500, headers: corsHeaders });
      }
      try {
        const disp = await fetch(
          `https://api.github.com/repos/${REPO}/actions/workflows/${WF}/dispatches`,
          {
            method: 'POST',
            headers: {
              'Authorization': 'Bearer ' + TOKEN,
              'Accept': 'application/vnd.github+json',
              'Content-Type': 'application/json',
              'User-Agent': 'exchange-update-worker'
            },
            body: JSON.stringify({ ref: 'main', inputs: { reason: '网页手动触发' } })
          }
        );
        if (!disp.ok) {
          const t = await disp.text();
          return new Response(JSON.stringify({ ok: false, status: disp.status, error: t.slice(0, 400) }),
            { status: 502, headers: corsHeaders });
        }
        // 取最新一次 run 用于轮询
        const runsRes = await fetch(
          `https://api.github.com/repos/${REPO}/actions/runs?per_page=1`,
          {
            headers: {
              'Authorization': 'Bearer ' + TOKEN,
              'Accept': 'application/vnd.github+json',
              'User-Agent': 'exchange-update-worker'
            }
          }
        );
        const runs = await runsRes.json();
        const run = runs.workflow_runs && runs.workflow_runs[0];
        return new Response(JSON.stringify({
          ok: true,
          run_id: run ? run.id : null,
          html_url: run ? run.html_url : null
        }), { headers: corsHeaders });
      } catch (e) {
        return new Response(JSON.stringify({ ok: false, error: String(e) }),
          { status: 500, headers: corsHeaders });
      }
    }

    if (url.pathname === '/status') {
      const runId = url.searchParams.get('run_id');
      if (!runId) {
        return new Response(JSON.stringify({ error: 'missing run_id' }), { status: 400, headers: corsHeaders });
      }
      const res = await fetch(`https://api.github.com/repos/${REPO}/actions/runs/${runId}`, {
        headers: {
          'Authorization': 'Bearer ' + TOKEN,
          'Accept': 'application/vnd.github+json',
          'User-Agent': 'exchange-update-worker'
        }
      });
      const d = await res.json();
      return new Response(JSON.stringify({ status: d.status, conclusion: d.conclusion }),
        { headers: corsHeaders });
    }

    return new Response('exchange update worker', { headers: corsHeaders });
  }
};

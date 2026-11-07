export function cloudState(env = {}) {
  const now = new Date().toISOString();
  return {
    protocol: 'GEN-NET-006',
    status: 'cloud-read-only',
    authority: 'github-canonical',
    alwaysOnHome: 'cloudflare-pages',
    laptopMayBeRequired: false,
    primaryInteraction: 'cloud-founder-surface',
    commit: String(env.CF_PAGES_COMMIT_SHA || 'cloud-preview'),
    branch: String(env.CF_PAGES_BRANCH || 'cloud-preview'),
    protocolSha256: '',
    policySha256: '',
    models: {
      primary: 'minimax/MiniMax-M3.1-Flash',
      secondary: 'deepseek/deepseek-v4-flash',
      subscription: 'gemini/manual-subscription-only',
      router: 'cloud-projection',
    },
    directive: null,
    surfaces: [
      {
        name: 'Genesis founder surface',
        kind: 'web',
        status: 'READY',
        lastSeen: now,
      },
      {
        name: 'Cloud projection',
        kind: 'cloudflare-pages-function',
        status: 'READ_ONLY',
        lastSeen: now,
      },
    ],
    arrWritable: false,
    arrTickets: [],
    syncVerification: {
      ok: true,
      checkedAt: now,
      policySha256: '',
      failures: [],
    },
    runtimeVerification: {
      ok: true,
      checkedAt: now,
      output: 'Cloudflare Pages projection is reachable.',
    },
    sync: {},
    sessions: [],
    sessionWritable: false,
    sessionLedgerError: null,
    generatedAt: now,
  };
}

export function json(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
      ...headers,
    },
  });
}

// founder-passkey -- the founder approves a guarded change with Face ID / Touch ID, from any device.
//
// WHY (2026-11-12, idp#8022). The founder's approval key was a file on one MacBook, readable by every
// agent running as the founder there and lost with the laptop. A passkey's private key never leaves
// the device's secure hardware, needs a biometric to sign, and syncs through iCloud Keychain.
//
// This Worker holds NO authority. It serves the page that asks the founder's device to sign, and it
// relays the signed assertion back to the agent that asked. Every decision is made by
// bin/idp-passkey-verify against the public key committed on main; anything posted here that the
// founder's passkey did not sign simply fails verification. Registration is bound to a one-time
// nonce that only the founder's own bootstrap run knows, so nobody else can register a key.
//
// Routes:
//   GET  /                       the page (register: #register=<nonce>, approve: #p=<payload>)
//   GET  /healthz                "ok"
//   POST /registration/<nonce>   the new passkey's public key (SPKI, base64url) + credential id
//   GET  /registration/<nonce>   read it back (the bootstrap run polls this)
//   POST /approve/<challenge>    a signed assertion for that challenge (kept, up to 5, 1 day)
//   GET  /approve/<challenge>    every assertion posted for it; the verifier picks the valid one

const B64U = /^[A-Za-z0-9_-]{16,128}$/;
const TTL = 86400;

const PAGE = `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Estate approval</title>
<style>
:root{color-scheme:light dark;--fg:#111;--bg:#fff;--mute:#555;--ok:#0a7d32;--bad:#b3261e;--line:#ddd}
@media(prefers-color-scheme:dark){:root{--fg:#f3f3f3;--bg:#111;--mute:#aaa;--ok:#5fd18a;--bad:#ff8a80;--line:#333}}
body{font:17px/1.45 -apple-system,system-ui,sans-serif;color:var(--fg);background:var(--bg);margin:0;padding:24px;max-width:560px}
h1{font-size:22px;margin:0 0 12px}dl{border:1px solid var(--line);border-radius:12px;padding:12px 16px}
dt{color:var(--mute);font-size:14px;margin-top:8px}dd{margin:2px 0 0;word-break:break-all}
button{font:inherit;font-weight:600;width:100%;min-height:52px;border:0;border-radius:12px;background:#0b57d0;color:#fff;margin-top:16px}
button:disabled{opacity:.5}#s{margin-top:16px;font-weight:600}.ok{color:var(--ok)}.bad{color:var(--bad)}
</style></head><body><main id="m"><h1>Estate approval</h1><p id="s">Loading…</p></main>
<script>
const $=s=>document.querySelector(s), s=$('#s');
const b64u={enc:b=>btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\\+/g,'-').replace(/\\//g,'_').replace(/=+$/,''),
 dec:t=>Uint8Array.from(atob(t.replace(/-/g,'+').replace(/_/g,'/')+'==='.slice((t.length+3)%4)),c=>c.charCodeAt(0))};
const say=(t,c)=>{s.textContent=t;s.className=c||''};
const h=new URLSearchParams(location.hash.slice(1));
function btn(label,fn){const b=document.createElement('button');b.textContent=label;b.onclick=async()=>{b.disabled=true;say('Waiting for Face ID / Touch ID…');try{await fn();b.remove()}catch(e){say('Not done: '+e.message+'. Next: tap again.','bad');b.disabled=false}};$('#m').appendChild(b)}
if(h.get('register')){
 const n=h.get('register');
 say('Create the passkey that approves guarded changes to the estate. It stays in your iCloud Keychain.');
 btn('Create founder passkey',async()=>{
  const c=await navigator.credentials.create({publicKey:{rp:{name:'Estate founder approval',id:location.hostname},
   user:{id:crypto.getRandomValues(new Uint8Array(16)),name:'founder',displayName:'Founder'},
   challenge:crypto.getRandomValues(new Uint8Array(32)),pubKeyCredParams:[{type:'public-key',alg:-7}],
   authenticatorSelection:{residentKey:'required',userVerification:'required'},attestation:'none'}});
  const spki=c.response.getPublicKey(); if(!spki) throw new Error('this browser did not return the public key');
  const r=await fetch('/registration/'+n,{method:'POST',body:JSON.stringify({credentialId:b64u.enc(c.rawId),publicKeySpki:b64u.enc(spki)})});
  if(!r.ok) throw new Error('relay answered '+r.status);
  say('Passkey created. Your Mac finishes the rest.','ok')});
}else if(h.get('p')){
 const raw=b64u.dec(h.get('p')), lines=new TextDecoder().decode(raw).split('\\n');
 if(lines[0]!=='idp-founder-approval-v1'){say('This link is not an estate approval.','bad')}else{
  const dl=document.createElement('dl');[['Change',lines[4]],['Files',lines.slice(5).join(', ')],['Requested',lines[1]],['On top of',lines[2].slice(0,12)],['Content',lines[3].slice(0,12)]]
   .forEach(([k,v])=>{const t=document.createElement('dt');t.textContent=k;const d=document.createElement('dd');d.textContent=v;dl.append(t,d)});
  $('#m').insertBefore(dl,s); say('Approving signs exactly this content. Any later edit voids it.');
  btn('Approve with Face ID',async()=>{
   const ch=await crypto.subtle.digest('SHA-256',raw);
   const a=await navigator.credentials.get({publicKey:{challenge:ch,rpId:location.hostname,userVerification:'required',allowCredentials:[]}});
   const body={authenticatorData:b64u.enc(a.response.authenticatorData),clientDataJSON:b64u.enc(a.response.clientDataJSON),signature:b64u.enc(a.response.signature)};
   const r=await fetch('/approve/'+b64u.enc(ch),{method:'POST',body:JSON.stringify(body)});
   if(!r.ok) throw new Error('relay answered '+r.status);
   say('Approved. The estate lands it from here.','ok')});
 }
}else{say('Nothing to approve. Open the link the estate sent you.')}
</script></body></html>`;

const json = (o, status = 200) =>
  new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });

async function readBody(req, max = 8192) {
  const t = await req.text();
  if (t.length > max) throw new Error('too large');
  return JSON.parse(t);
}

const okB64u = (v, max) => typeof v === 'string' && v.length > 0 && v.length <= max && /^[A-Za-z0-9_-]+$/.test(v);

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const [, head, arg] = url.pathname.split('/');
    if (req.method === 'GET' && url.pathname === '/') {
      return new Response(PAGE, { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store',
        'content-security-policy': "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'",
        'referrer-policy': 'no-referrer', 'x-frame-options': 'DENY' } });
    }
    if (url.pathname === '/healthz') return new Response('ok');
    if (!arg || !B64U.test(arg)) return json({ error: 'not found' }, 404);
    try {
      if (head === 'registration') {
        const k = 'reg:' + arg;
        if (req.method === 'GET') {
          const v = await env.APPROVALS.get(k);
          return v ? json({ ...JSON.parse(v), rp_id: url.hostname, origin: url.origin }) : json({ pending: true }, 404);
        }
        if (req.method === 'POST') {
          if (await env.APPROVALS.get(k)) return json({ error: 'already registered' }, 409);
          const b = await readBody(req);
          if (!okB64u(b.credentialId, 512) || !okB64u(b.publicKeySpki, 512)) return json({ error: 'bad registration' }, 400);
          await env.APPROVALS.put(k, JSON.stringify({ credentialId: b.credentialId, publicKeySpki: b.publicKeySpki,
            at: new Date().toISOString() }), { expirationTtl: TTL });
          return json({ ok: true });
        }
      }
      if (head === 'approve') {
        const k = 'ap:' + arg;
        const list = JSON.parse((await env.APPROVALS.get(k)) || '[]');
        if (req.method === 'GET') return list.length ? json(list) : json({ pending: true }, 404);
        if (req.method === 'POST') {
          if (list.length >= 5) return json({ error: 'full' }, 429);
          const b = await readBody(req);
          if (!okB64u(b.authenticatorData, 2048) || !okB64u(b.clientDataJSON, 4096) || !okB64u(b.signature, 512))
            return json({ error: 'bad assertion' }, 400);
          list.push({ authenticatorData: b.authenticatorData, clientDataJSON: b.clientDataJSON, signature: b.signature });
          await env.APPROVALS.put(k, JSON.stringify(list), { expirationTtl: TTL });
          return json({ ok: true });
        }
      }
    } catch (e) {
      return json({ error: 'bad request' }, 400);
    }
    return json({ error: 'not found' }, 404);
  },
};

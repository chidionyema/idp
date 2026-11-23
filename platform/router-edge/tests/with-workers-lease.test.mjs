import { test } from 'node:test';
import assert from 'node:assert/strict';
import { runWithLease, requiredReleaseContext } from '../scripts/with-workers-lease.mjs';

const SHA='a'.repeat(40), ACCOUNT='b'.repeat(32), ZONE_ID='c'.repeat(32);
const ROOT='root-secret-example-not-real-1234567890', WRK='workers-fake-token-abcdefghijklmnopqrstuvwxyz';
const BASE={GITHUB_REF:'refs/heads/main',GITHUB_SHA:SHA,RELEASE_SHA:SHA,
  CLOUDFLARE_ROOT_TOKEN:ROOT,CLOUDFLARE_ACCOUNT_ID:ACCOUNT,
  MERIDIAN_CLIENT_KEY:'client-secret-example',MERIDIAN_ADMIN_KEY:'admin-secret-example'};
const groups=[
 {name:'Zone Read',id:'d'.repeat(32),scopes:['com.cloudflare.api.account.zone.read']},
 {name:'Workers Scripts Write',id:'e'.repeat(32),scopes:['com.cloudflare.api.account']},
 {name:'Workers Routes Write',id:'f'.repeat(32),scopes:['com.cloudflare.api.account.zone']},
 {name:'Workers AI Write',id:'9'.repeat(32),scopes:['com.cloudflare.api.account']},
];
function mock(opts={}) {
 const calls=[];
 const fetchImpl=async (url,init)=>{
  const u=new URL(url),p=u.pathname,auth=init.headers.authorization;
  let value={success:true,result:null};
  calls.push({method:init.method,path:p,query:u.search,authority: auth === `Bearer ${ROOT}`?'ROOT':auth===`Bearer ${WRK}`?'WORKERS':'READER',body:init.body?JSON.parse(init.body):null});
  if(opts.badRoot && p==='/client/v4/user/tokens/verify' && auth===`Bearer ${ROOT}`) value.result={status:'revoked'};
  else if(p==='/client/v4/user/tokens/verify') value.result={status:'active'};
  else if(p==='/client/v4/user/tokens/permission_groups') value.result=opts.noGroups?[]:groups;
  else if(p==='/client/v4/zones') value.result=auth===`Bearer ${ROOT}`?[]:[{id:ZONE_ID,name:'meridianlabs.cloud',account:{id:opts.wrongAccount?'0'.repeat(32):ACCOUNT}}];
  else if(p==='/client/v4/user/tokens' && init.method==='POST') {
    if(opts.mintDenied) {value={success:false,errors:[{code:10000}]};}
    else value.result=JSON.parse(init.body).name.startsWith('meridian-zone-read')?{id:'1'.repeat(32),value:'zone-read-token-abcdefghijklmnopqrstuvwxyz'}:{id:'2'.repeat(32),value:WRK};
  } else if(p.startsWith('/client/v4/accounts/') && p.endsWith('/workers/scripts')) value.result=[];
  else if(p.startsWith('/client/v4/user/tokens/') && init.method==='DELETE') {if(opts.revokeDenied && p.endsWith('2'.repeat(32)))value={success:false,errors:[{code:10000}]};else value.result={};}
  else throw Error('unexpected call '+p);
  return {ok:true,status:200,json:async()=>value};
 };
 return {calls,fetchImpl};
}
async function run(env=BASE,opt={},execute=async()=>0){
 const spy=mock(opt); const report=await runWithLease({env,fetchImpl:spy.fetchImpl,execute,clock:()=>1700000000000});
 return {exit:report,calls:spy.calls};
}
test('refuses non-main and wrong SHA before any credential use',async()=>{
 for(const e of [{...BASE,GITHUB_REF:'refs/heads/feature'}, {...BASE,RELEASE_SHA:'c'.repeat(40)}]){
  const r=await run(e);assert.equal(r.exit,1);assert.equal(r.calls.length,0);
 }
});
test('refuses missing root, account, and client identity before mint',async()=>{
 for(const bad of [{CLOUDFLARE_ROOT_TOKEN:''},{CLOUDFLARE_ACCOUNT_ID:''},{MERIDIAN_CLIENT_KEY:''},{MERIDIAN_ADMIN_KEY:''}]){
  assert.throws(()=>requiredReleaseContext({...BASE,...bad}));
 }
});
test('permitted zone-read and workers token, no R2, cleanup on successful release',async()=>{
 let invoked=false;
 const r=await run(BASE,{},async(child)=>{
  invoked=true;
  assert.equal(child.CLOUDFLARE_API_TOKEN,WRK);
  assert.equal(child.CLOUDFLARE_ROOT_TOKEN,undefined);
  assert.equal(child.MERIDIAN_CLIENT_KEY,BASE.MERIDIAN_CLIENT_KEY);
  return 0;
 });
 assert.equal(r.exit,0); assert.equal(invoked,true);
 assert.equal(r.calls.filter(x=>x.path==='/client/v4/user/tokens' && x.method==='POST').length,2);
 assert.equal(r.calls.filter(x=>x.method==='DELETE').length,2);
 assert.equal(r.calls.some(x=>x.path.includes('/r2/')),false);
 const mint=r.calls.filter(x=>x.path==='/client/v4/user/tokens'&&x.method==='POST');
 assert.equal(mint[1].body.policies[0].resources['com.cloudflare.api.account.'+ACCOUNT],'*');
 assert.equal(mint[1].body.policies[1].resources['com.cloudflare.api.account.zone.'+ZONE_ID],'*');
});
test('exact zone ownership mismatch refuses deployment and revokes reader',async()=>{
 let called=false;const r=await run(BASE,{wrongAccount:true},async()=>{called=true;return 0;});
 assert.equal(r.exit,1);assert.equal(called,false);assert.equal(r.calls.filter(x=>x.method==='DELETE').length,1);
});
test('Cloudflare root revoked prevents any children',async()=>{
 const r=await run(BASE,{badRoot:true});assert.equal(r.exit,1);
 assert.equal(r.calls.filter(x=>x.method==='POST').length,0);
});
test('missing permission group prevents mint and protected identity weakening',async()=>{
 const r=await run(BASE,{noGroups:true});assert.equal(r.exit,1);
 assert.equal(r.calls.filter(x=>x.method==='POST').length,0);
});
test('mint provider denied means no release',async()=>{
 let released=false;const r=await run(BASE,{mintDenied:true},async()=>{released=true;return 0;});
 assert.equal(r.exit,1);assert.equal(released,false);
});
test('failed release revokes Workers token even on exit 2',async()=>{
 const r=await run(BASE,{},async()=>2);
 assert.equal(r.exit,1);assert.equal(r.calls.filter(x=>x.method==='DELETE').length,2);
});
test('token revoke failure rejects certification even after child success',async()=>{
 const r=await run(BASE,{revokeDenied:true},async()=>0);
 assert.equal(r.exit,1);assert.equal(r.calls.filter(x=>x.method==='DELETE').length,2);
});
test('no secret material is included in thrown errors for unknown provider responses',async()=>{
 const spy=mock({mintDenied:true});
 let output='';const orig=console.log;console.log=(x)=>{output+=x;};
 try{await runWithLease({env:BASE,fetchImpl:spy.fetchImpl,execute:async()=>0});}
 finally{console.log=orig;}
 assert(!output.includes(ROOT));assert(!output.includes(WRK));assert(!output.includes(BASE.MERIDIAN_CLIENT_KEY));
});

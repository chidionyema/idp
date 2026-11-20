import test from 'node:test';
import assert from 'node:assert/strict';
import { checkPage, checkScene, checkContact, scenes, widths } from './investor-acceptance.mjs';
const investor = { status: 200, pathname: '/investors', headings: 1, landmarks: true, scrollWidth: 375, clipped: [], investor: true, chronosLink: true, contactLink: true, investorDisclosure: true, privateEffectLinks: false };
const chronos = { ...investor, pathname: '/products/chronos', chronos: true, concept: true, disclaimer: true, investorLink: true };
test('valid candidate observations and boundary widths', () => {
  checkPage(investor, '/investors', 375);
  checkPage(chronos, '/products/chronos', 375);
  assert.deepEqual(widths, [320, 375, 768, 1000, 1001, 1440]);
});
for (const [name, change] of Object.entries({ notFound: {status:404}, redirect: {pathname:'/'}, duplicateHeading:{headings:2}, missingLandmarks:{landmarks:false}, overflow:{scrollWidth:390}, clipped:{clipped:['A:CTA']}, noInvestor:{investor:false}, noChronosLink:{chronosLink:false}, noContactLink:{contactLink:false}, noDisclosure:{investorDisclosure:false}, privilegedLink:{privateEffectLinks:true} })) {
  test(`rejects investor ${name}`, () => assert.throws(() => checkPage({...investor,...change}, '/investors', 375)));
}
for (const key of ['chronos','concept','disclaimer','investorLink']) {
  test(`rejects Chronos ${key}`, () => assert.throws(() => checkPage({...chronos,[key]:false}, '/products/chronos',375)));
}
const state = i => ({ pressed: scenes.map((_,j)=>i===j?'true':'false'),time: scenes[i],heading:'A heading',example:'An example',disclosed:true,live:'polite' });
test('all walkthrough states and reset',()=>{ for(const i of [0,1,2,0])checkScene(state(i),i); });
test('rejects stale scene',()=>assert.throws(()=>checkScene(state(0),1)));
test('rejects multiple pressed steps',()=>assert.throws(()=>checkScene({...state(1),pressed:['true','true','false']},1)));
test('rejects inaccessible announcement or misleading example',()=>{assert.throws(()=>checkScene({...state(1),live:null},1));assert.throws(()=>checkScene({...state(1),disclosed:false},1));});
test('contact fails closed unless ready',()=>{checkContact({form:false,paused:true},false);checkContact({form:true,paused:false},true);assert.throws(()=>checkContact({form:true,paused:false},false));assert.throws(()=>checkContact({form:false,paused:false},false));});

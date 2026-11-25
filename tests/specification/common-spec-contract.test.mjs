import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import {test} from "node:test";
import {canonicalSpec,validateSpec,founderView,prestart} from "../../platform/estate/specification-contract.mjs";
const hash = b => createHash("sha256").update(b).digest("hex");
const annex = Buffer.from("Synthetic technical annex; never a founder approval.");
const phrase = "Explicit bounded synthetic test fixture";
const spec = {schema:"meridian.spec/1",id:"TEST-001",instruction:phrase,class:"research",founder:{why:phrase,proposal:phrase,value:phrase,alternatives:[{option:"Preserve current approach",tradeoff:phrase},{option:"Evaluate candidate approach",tradeoff:phrase}],risks:[{risk:phrase,control:phrase}],decision:phrase,recommendation:phrase},scope:{owner:phrase,affected:[phrase],excluded:[phrase],base:"a".repeat(40)},outcomes:[{id:"OUTCOME-1",effect:phrase,acceptance:phrase,falsifier:phrase,independent_verifier:phrase}],topology:{snapshot:"b".repeat(64),dependencies:[{id:"DEPENDENCY-1",kind:"required",evidence:phrase,failure_domain:phrase}],unknowns:[],blast_radius:phrase,fault_model:phrase},resources:{max_incremental_pence:0,max_duration_seconds:600,basis:phrase,uncertainties:[]},delivery:[{id:"STEP-001",owner:phrase,action:phrase,exit_evidence:phrase,requires:[]}],assurance:{authority_boundary:phrase,proof_plan:phrase,negative_tests:[phrase],settlement:phrase},recovery:{rollback:phrase,independent_path:phrase,custody:phrase,deadline:phrase},annex:{ref:"synthetic-annex.md",sha256:hash(annex)}};
const bytes = s => Buffer.from(canonicalSpec(s));
const raw = bytes(spec);
const ctx = {verified:true,specDigest:hash(raw),instruction:spec.instruction,base:spec.scope.base,topology:spec.topology.snapshot,annexDigest:hash(annex),decision:"SCOPE_AUTHORIZED",policyCurrent:true,materialDependenciesVerified:true,now:100,expires:200,reservedPence:0,reservedSeconds:600};
let providerCalls=0;
function simulatedBoundary(r,a,c){const v=prestart(r,a,c);if(v.decision==="ELIGIBLE_FOR_EXISTING_AUTHORITY_GATE")providerCalls++;return v;}
function deny(r=raw,a=annex,c=ctx){const before=providerCalls;assert.equal(simulatedBoundary(r,a,c).decision,"DENY");assert.equal(providerCalls,before);}
test("valid schema and founder projection",()=>{assert.deepEqual(validateSpec(spec),[]);assert.equal(founderView(spec).decision,spec.founder.decision);assert.equal(founderView(spec).disposition,"PROPOSAL_ONLY");});
for(const k of Object.keys(spec))test("missing "+k,()=>{const s=structuredClone(spec);delete s[k];const r=bytes(s);deny(r,annex,{...ctx,specDigest:hash(r)});});
for(const [n,p] of [["missing receipt",null],["unverified receipt",{verified:false}],["stale base",{base:"c".repeat(40)}],["stale topology",{topology:"d".repeat(64)}],["stale policy",{policyCurrent:false}],["unresolved material dependencies",{materialDependenciesVerified:false}],["expired",{expires:100}],["insufficient time",{reservedSeconds:599}],["insufficient budget",{reservedPence:-1}],["unapproved",{decision:"PROPOSED"}],["wrong digest",{specDigest:"f".repeat(64)}]])test(n,()=>deny(raw,annex,p===null?null:{...ctx,...p}));
for(const [n,mutate] of [["empty founder why",s=>s.founder.why="TODO"],["no alternative",s=>s.founder.alternatives.pop()],["no falsifier",s=>delete s.outcomes[0].falsifier],["negative budget",s=>s.resources.max_incremental_pence=-1],["cyclic plan",s=>s.delivery[0].requires=["STEP-001"]],["approval injection",s=>s.approved=true]])test(n,()=>{const s=structuredClone(spec);mutate(s);const r=bytes(s);deny(r,annex,{...ctx,specDigest:hash(r)});});
test("valid-looking changed founder decision retains old receipt",()=>{const s=structuredClone(spec);s.founder.decision="A different decision changes the authorised scope";deny(bytes(s));});
test("actual annex mutation",()=>deny(raw,Buffer.from("Different annex bytes")));
test("duplicate JSON key",()=>deny(Buffer.from(raw.toString().replace('"schema":','"schema":"meridian.spec/1","schema":'))));
test("noncanonical JSON",()=>deny(Buffer.from(JSON.stringify(spec,null,2))));
test("malformed UTF-8",()=>deny(Buffer.from([255])));
test("missing bytes",()=>deny(Buffer.alloc(0)));
test("oversized specification",()=>deny(Buffer.alloc(262145)));
test("positive control reaches simulated provider once",()=>{const before=providerCalls;const v=simulatedBoundary(raw,annex,ctx);assert.equal(v.decision,"ELIGIBLE_FOR_EXISTING_AUTHORITY_GATE");assert.equal(v.specDigest,hash(raw));assert.equal(v.annexDigest,hash(annex));assert.equal(providerCalls,before+1);});

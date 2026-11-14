/**
 * HELM GROUND ADAPTER: a capability-reducing wrapper, not an executor.
 *
 * The founder owns shotPolicy. Ground troops receive ONLY two callbacks:
 * one registered read-only context probe and one REGISTERED estate intent
 * dispatcher. The adapter durably reserves each action BEFORE invoking the
 * underlying callback. A crash after a dispatch may leave the journal
 * AWAITING_GRADE, which must be reconciled by independent evidence and NEVER
 * silently retried.
 *
 * The caller MUST implement store.append(policy,event) as a compare-and-swap
 * transaction in the existing Argon instruction ledger / FLOW store. This
 * research adapter intentionally refuses when an atomic store is unavailable:
 * there is no second file or database that can falsely claim authority.
 */
import {helmDigest,advanceShot,replayShots,shotReport} from "./shot-control.mjs";

function no(reason) {
  throw new Error("HELM_GATE_REFUSED: "+reason);
}
function safeName(value) {
  return typeof value==="string" && /^[A-Za-z0-9._-]{3,100}$/.test(value);
}
const DELIVER_PHASES=["BUILD","TEST","COMMIT","PUSH","GREENLANE","VERIFY"];

export class HelmGroundGateway {
  // Private capability references prevent bypass by overriding public fields.
  #policy;
  #store;
  #contextProbe;
  #dispatchRegisteredIntent;
  #permitted;
  constructor({policy,store,contextProbe,dispatchRegisteredIntent,permittedIntents}={}){
    if(!policy || policy.schema!=="helm.shot-policy.v1")
      no("founder-issued policy required");
    if(!store || typeof store.read!=="function" || typeof store.append!=="function")
      no("authoritative transactional ledger adapter required");
    if(typeof contextProbe!=="function" || typeof dispatchRegisteredIntent!=="function")
      no("registered probe and intent door required");
    if(!Array.isArray(permittedIntents) || !permittedIntents.length ||
      permittedIntents.some(x=>!safeName(x)))
      no("explicit allowlisted estate intents required");
    this.#policy=policy;
    this.#store=store;
    this.#contextProbe=contextProbe;
    this.#dispatchRegisteredIntent=dispatchRegisteredIntent;
    this.#permitted=new Set(permittedIntents);
  }

  async snapshot(){
    const events=await this.#store.read(this.#policy.instructionId);
    if(!Array.isArray(events))no("authoritative ledger unavailable");
    const state=replayShots(this.#policy,events);
    return shotReport(this.#policy,state);
  }

  async commitEvent(event){
    // Admission is NOT an in-memory counter. The existing DB must atomically
    // compare journal head, insert the event, and commit BEFORE this returns.
    const journal=await this.#store.read(this.#policy.instructionId);
    if(!Array.isArray(journal))no("authoritative ledger unavailable");
    const before=replayShots(this.#policy,journal);
    const after=advanceShot(this.#policy,before,event);
    if(after.head===before.head)return after; // idempotent readback
    const saved=await this.#store.append({
      policy:this.#policy,instructionId:this.#policy.instructionId,
      previousHead:before.head,event,
      expectedNextHead:after.head
    });
    if(saved!==after.head)no("ledger commit/readback mismatch");
    const witnessed=await this.#store.read(this.#policy.instructionId);
    const recovered=replayShots(this.#policy,witnessed);
    if(recovered.head!==after.head)no("commit not visible from authoritative store");
    return recovered;
  }

  /** Exactly one read-only probe per instruction. Reserve BEFORE calling it. */
  async probeOnce(request){
    if(!request || request.opcode!=="CONTEXT_PROBE" ||
      request.taskDigest!==this.#policy.taskDigest ||
      request.sourceSha!==this.#policy.sourceSha)
      no("unrecognised or stale context request");
    const current=await this.snapshot();
    if(current.status!=="NEEDS_PROBE")no("probe budget spent");
    const event={
      kind:"PROBE",eventId:"PROBE-001",
      instructionId:this.#policy.instructionId,
      // Hash the requested context, not a result obtained before admission.
      probeDigest:helmDigest(request),sourceSha:this.#policy.sourceSha
    };
    await this.commitEvent(event);
    // Never retry automatically on an exception; an I/O failure consumes the
    // probe so the "one probe" rule survives an interrupted worker process.
    return this.#contextProbe(Object.freeze({...request}));
  }

  /**
   * Accept exactly ONE all-in-one candidate per shot.
   * Only registered YAML intents are legal; never interpret arbitrary model
   * text as a shell command. The existing executor is responsible for auth,
   * build/test/commit/push/Greenlane and actual CI/prod readback.
   */
  async deliver(candidate){
    if(!candidate || !this.#permitted.has(candidate.intent) ||
      !candidate.args || typeof candidate.args!=="object" ||
      Array.isArray(candidate.args) ||
      !Array.isArray(candidate.declaredPhases) ||
      JSON.stringify(candidate.declaredPhases)!==JSON.stringify(DELIVER_PHASES))
      no("one complete registered delivery intent with all phases required");
    const current=await this.snapshot();
    if(current.status!=="READY")no("no unconsumed delivery shot");
    const attempt=current.candidateSubmissions+1;
    const candidateDigest=helmDigest({
      intent:candidate.intent,args:candidate.args,phases:candidate.declaredPhases
    });
    const reservation={
      kind:"SHOT",eventId:"SHOT-"+attempt,
      instructionId:this.#policy.instructionId,
      candidateDigest,opcode:"DISPATCH_LEGION",model:this.#policy.model
    };
    await this.commitEvent(reservation);
    // A crash or timeout HERE is indeterminate, not permission to rerun.
    // The caller must use reconcile() with proof from a distinct observer.
    return this.#dispatchRegisteredIntent(Object.freeze({
      instructionId:this.#policy.instructionId,
      intent:candidate.intent,args:structuredClone(candidate.args),
      candidateDigest,attempt
    }));
  }

  /** Grade an already-reserved shot without replaying its side effects. */
  async reconcile({candidateDigest,evidenceDigest,passed,verifier}={}){
    const journal=await this.#store.read(this.#policy.instructionId);
    if(!Array.isArray(journal))no("journal unavailable");
    const state=replayShots(this.#policy,journal);
    if(state.phase!=="AWAITING_GRADE")
      no("no pending candidate; NEVER resubmit the original execution");
    if(candidateDigest!==state.currentShot?.digest)
      no("verdict for wrong candidate");
    if(!safeName(verifier) || verifier!==this.#policy.verifier)
      no("independent verifier identity mismatch");
    if(typeof passed!=="boolean" ||
      typeof evidenceDigest!=="string" ||
      !/^[0-9a-f]{64}$/.test(evidenceDigest))
      no("external evidence digest and explicit verdict required");
    const after=await this.commitEvent({
      kind:"GRADE",eventId:"GRADE-"+state.shots,
      instructionId:this.#policy.instructionId,
      candidateDigest,passed,verifier,evidenceDigest
    });
    return shotReport(this.#policy,after);
  }
}

/** Tests-only owner. Production callers must use transactional DB CAS. */
export class FixtureShotStore {
  constructor(){this.rows=new Map();}
  async read(id){return structuredClone(this.rows.get(id)||[]);}
  async append({policy,instructionId,previousHead,event,expectedNextHead}){
    const original=this.rows.get(instructionId)||[];
    const state=replayShots(policy,original);
    if(state.head!==previousHead)no("optimistic lock conflict");
    const next=advanceShot(policy,state,event);
    if(next.head!==expectedNextHead)no("unexpected event digest");
    this.rows.set(instructionId,structuredClone(next.events));
    return next.head;
  }
}

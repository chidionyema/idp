/**
 * HELM CAS adapter for ARGON's existing instruction_ledger SQLite database.
 *
 * No separate authority database: a policy cannot be admitted until the
 * canonical Argon instruction_id row already exists. The founder-authenticated
 * Genesis API owns admitFounderPolicy; agents see only read + append and cannot
 * silently install or widen their own helmet.
 *
 * The caller must mount a durable cloud SQLite volume at an EXPLICIT path.
 * A Mac-local /tmp file or ephemeral pod filesystem is NOT durable in prod.
 */
import {existsSync} from "node:fs";
import {DatabaseSync} from "node:sqlite";
import {helmDigest,advanceShot,replayShots} from "./shot-control.mjs";

const ID=/^[A-Za-z0-9._-]{3,100}$/;
function nope(message){
  const err=new Error("HELM_SQLITE_REFUSED: "+message);
  err.code="HELM_SQLITE_REFUSED";
  throw err;
}
function assertedPolicy(policy){
  if(!policy || policy.schema!=="helm.shot-policy.v1" ||
    typeof policy.instructionId!=="string" || !ID.test(policy.instructionId))
    nope("canonical HELM policy required");
}

export class ArgonHelmSqliteStore {
  constructor(dbPath){
    if(typeof dbPath!=="string" || !dbPath.startsWith("/") || !existsSync(dbPath))
      nope("existing shared absolute Argon database required; never create shadow DB");
    this.db=new DatabaseSync(dbPath);
    this.db.exec("PRAGMA busy_timeout=5000");
    this.db.exec("PRAGMA foreign_keys=ON");
    this.db.exec("PRAGMA journal_mode=WAL");
    const present=this.db.prepare(
      "SELECT name FROM sqlite_master WHERE type='table' AND name='instruction_ledger'"
    ).get();
    if(!present){
      this.db.close();
      nope("existing Argon instruction_ledger not found");
    }
    // Additive tables in the SAME estate database, not a competing instruction table.
    this.db.exec(
      "CREATE TABLE IF NOT EXISTS helm_instruction_policy ("+
      "instruction_id TEXT PRIMARY KEY NOT NULL REFERENCES instruction_ledger(instruction_id),"+
      "policy_sha256 TEXT NOT NULL,policy_json TEXT NOT NULL,admitted_at_ms INTEGER NOT NULL);"+
      "CREATE TABLE IF NOT EXISTS helm_instruction_events ("+
      "instruction_id TEXT NOT NULL REFERENCES helm_instruction_policy(instruction_id),"+
      "sequence INTEGER NOT NULL,event_id TEXT NOT NULL,"+
      "event_json TEXT NOT NULL,chain_sha256 TEXT NOT NULL,"+
      "PRIMARY KEY(instruction_id,sequence),UNIQUE(instruction_id,event_id));"+
      "CREATE INDEX IF NOT EXISTS helm_instruction_events_latest "+
      "ON helm_instruction_events(instruction_id,sequence)"
    );
  }

  close(){this.db.close();}

  /*
   * Control-plane operation ONLY. Owner must call after existing Genesis
   * requireAdmin() authenticated the founder. This module cannot authenticate
   * HTTP itself, and agents must never receive its owner-side instance.
   */
  admitFounderPolicy(policy){
    assertedPolicy(policy);
    const id=policy.instructionId;
    this.db.exec("BEGIN IMMEDIATE");
    try{
      const instruction=this.db.prepare(
        "SELECT instruction_id FROM instruction_ledger WHERE instruction_id=?"
      ).get(id);
      if(!instruction)nope("unknown canonical Argon instruction");
      const old=this.db.prepare(
        "SELECT policy_sha256 FROM helm_instruction_policy WHERE instruction_id=?"
      ).get(id);
      const expected=helmDigest(policy);
      if(old){
        if(old.policy_sha256!==expected)
          nope("founder policy immutable after admission");
        this.db.exec("COMMIT");
        return {instructionId:id,policySha256:expected,existing:true};
      }
      this.db.prepare(
        "INSERT INTO helm_instruction_policy "+
        "(instruction_id,policy_sha256,policy_json,admitted_at_ms) VALUES (?,?,?,?)"
      ).run(id,expected,JSON.stringify(policy),Date.now());
      this.db.exec("COMMIT");
      return {instructionId:id,policySha256:expected,existing:false};
    }catch(error){
      this.db.exec("ROLLBACK");
      throw error;
    }
  }

  policyFor(id){
    if(!ID.test(id))nope("invalid instruction_id");
    const row=this.db.prepare(
      "SELECT policy_json,policy_sha256 FROM helm_instruction_policy WHERE instruction_id=?"
    ).get(id);
    if(!row)nope("founder helmet not admitted");
    const policy=JSON.parse(row.policy_json);
    if(helmDigest(policy)!==row.policy_sha256)
      nope("stored founder helmet integrity mismatch");
    return Object.freeze(policy);
  }

  async read(id){
    this.policyFor(id);
    return this.db.prepare(
      "SELECT event_json FROM helm_instruction_events "+
      "WHERE instruction_id=? ORDER BY sequence"
    ).all(id).map(r=>JSON.parse(r.event_json));
  }

  async append({policy,instructionId,previousHead,event,expectedNextHead}){
    assertedPolicy(policy);
    if(instructionId!==policy.instructionId ||
       event?.instructionId!==instructionId)
      nope("cross-instruction write refused");
    this.db.exec("BEGIN IMMEDIATE");
    try{
      const owner=this.policyFor(instructionId);
      if(helmDigest(owner)!==helmDigest(policy))
        nope("model attempted to widen founder policy");
      const records=this.db.prepare(
        "SELECT event_json FROM helm_instruction_events "+
        "WHERE instruction_id=? ORDER BY sequence"
      ).all(instructionId).map(x=>JSON.parse(x.event_json));
      const before=replayShots(owner,records);
      if(before.head!==previousHead)
        nope("CAS conflict / stale ground agent");
      const after=advanceShot(owner,before,event);
      if(after.head!==expectedNextHead)
        nope("candidate hash differs from admitted action");
      if(after.head===before.head){
        this.db.exec("COMMIT");
        return before.head;
      }
      const entry=after.events.at(-1);
      this.db.prepare(
        "INSERT INTO helm_instruction_events "+
        "(instruction_id,sequence,event_id,event_json,chain_sha256) "+
        "VALUES (?,?,?,?,?)"
      ).run(instructionId,entry.sequence,entry.eventId,
        JSON.stringify(entry),entry.chain);
      this.db.exec("COMMIT");
      return after.head;
    }catch(error){
      this.db.exec("ROLLBACK");
      throw error;
    }
  }
}

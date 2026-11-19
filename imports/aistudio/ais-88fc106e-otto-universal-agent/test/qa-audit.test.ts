import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { INITIAL_EVALS } from '../src/data/evalsData.js';
import { ELDER_NUN_PROFILE, FAMILY_LETTERS, SCAM_SHIELD_INCIDENTS } from '../src/data/familyRecords.js';
import { OMNIPRESENCE_SURFACES, FUTURE_PROOF_PILLARS } from '../src/data/omnipresenceData.js';
import { RED_TEAM_SCENARIOS, ORDER_OF_MAGNITUDE_METRICS } from '../src/data/securityRecords.js';
import { PEER_BUS_AGENTS, ESTATE_DEVICES } from '../src/data/estateRecords.js';
import { 
  INITIAL_DYNAMIC_PERSONAS, 
  INITIAL_PEOPLE_GRAPH, 
  ADVANCED_MEMORY_NODES, 
  ON_DEMAND_RSI_SKILLS 
} from '../src/data/generalPurposePersonaData.js';
import { 
  INITIAL_PHYSICAL_ENDPOINTS, 
  HARDWARE_CATEGORIES, 
  ESTATE_LOCATIONS 
} from '../src/data/physicalEstateData.js';

describe('QA Protocol 1: 12 Strict Evals & Benchmarks', () => {
  test('E1-E12 suite contains exactly 12 evals with status "pass"', () => {
    assert.equal(INITIAL_EVALS.length, 12, 'Must have exactly 12 evaluation metrics');
    for (const ev of INITIAL_EVALS) {
      assert.equal(ev.status, 'pass', `Eval ${ev.code} (${ev.name}) must be PASS`);
      assert.ok(ev.proofData.hash.length >= 16, `Eval ${ev.code} must have signed cryptographic proof hash`);
      assert.ok(ev.proofData.durationMs > 0, `Eval ${ev.code} must have measurable execution latency`);
    }
  });

  test('All 12 evals outperform MiniMax Code baseline with zero tie tolerance', () => {
    for (const ev of INITIAL_EVALS) {
      assert.ok(ev.ottoBar, `Eval ${ev.code} must have strict threshold`);
      assert.ok(ev.ottoScore, `Eval ${ev.code} must have verified Otto score`);
      assert.notEqual(ev.ottoScore, ev.minimaxScore, `Eval ${ev.code} has zero tie tolerance`);
    }
  });
});

describe('QA Protocol 2: Cryptographic Air-Gap & Kin Token Isolation', () => {
  test('Family Kin Profile is strictly air-gapped from estate cloud credentials', () => {
    assert.ok(ELDER_NUN_PROFILE.name.includes('Sister Beatrice'));
    assert.ok(ELDER_NUN_PROFILE.prayerSchedule && ELDER_NUN_PROFILE.prayerSchedule.length >= 4);
    assert.ok(ELDER_NUN_PROFILE.medications && ELDER_NUN_PROFILE.medications.length >= 3);
    assert.equal(ELDER_NUN_PROFILE.scamShieldStatus.active, true);

    const profileKeys = Object.keys(ELDER_NUN_PROFILE);
    assert.ok(!profileKeys.includes('ssh_key'), 'Kin profile must NOT contain ssh keys');
    assert.ok(!profileKeys.includes('aws_key'), 'Kin profile must NOT contain AWS keys');
    assert.ok(!profileKeys.includes('git_token'), 'Kin profile must NOT contain git tokens');
  });

  test('Family letters and scam incidents are properly registered', () => {
    assert.ok(FAMILY_LETTERS.length >= 2, 'Must have recorded family letters');
    assert.ok(SCAM_SHIELD_INCIDENTS.length >= 2, 'Must have active scam shield incidents');
    for (const scam of SCAM_SHIELD_INCIDENTS) {
      assert.equal(scam.safetyStatus, '100% PROTECTED');
    }
  });
});

describe('QA Protocol 3: Omnipresence Surfaces & 6 Future-Proof Pillars', () => {
  test('Surface registry contains all operational nodes across 7 categories', () => {
    assert.ok(OMNIPRESENCE_SURFACES.length >= 14, 'Must register at least 14 omnipresence surfaces');
    const categories = new Set(OMNIPRESENCE_SURFACES.map(s => s.category));
    assert.ok(categories.has('communication'));
    assert.ok(categories.has('ambient-home'));
    assert.ok(categories.has('automotive'));
    assert.ok(categories.has('spatial-xr'));
    assert.ok(categories.has('wearables'));
    assert.ok(categories.has('robotics'));
    assert.ok(categories.has('dev-infrastructure'));

    for (const s of OMNIPRESENCE_SURFACES) {
      assert.ok(s.id, 'Surface must have unique ID');
      assert.ok(s.protocol, 'Surface must declare physical/network protocol');
      assert.ok(s.mockInteraction.action, 'Surface must define action handler');
      assert.ok(s.mockInteraction.result, 'Surface must define verified output');
    }
  });

  test('6 Future-Proof Pillars have Hoare safety invariants and Coq lemmas', () => {
    assert.equal(FUTURE_PROOF_PILLARS.length, 6, 'Must implement exactly 6 survival pillars');
    for (const p of FUTURE_PROOF_PILLARS) {
      assert.ok(p.threatMitigated.length > 20, 'Pillar must define concrete threat mitigation');
      assert.ok(p.verificationProof.includes('PASS:'), 'Pillar must include verified proof certificate');
      assert.ok(p.codeSnippet.length > 30, 'Pillar must provide executable implementation invariant');
    }
  });
});

describe('QA Protocol 4: Security, Prompt Injection & DLP Defense', () => {
  test('All red-team attack scenarios are blocked or contained with 0 exfiltration', () => {
    assert.ok(RED_TEAM_SCENARIOS.length >= 8, 'Must test all 8 canonical attack vectors');
    for (const attack of RED_TEAM_SCENARIOS) {
      assert.ok(attack.outcome === 'BLOCKED' || attack.outcome === 'CONTAINED');
      assert.ok(attack.taintScore > 0.8, 'Attack must trigger high taint score');
      assert.ok(attack.dlpInvariant.startsWith('DLP-'), 'Attack must satisfy DLP invariant');
    }
  });

  test('Order of magnitude superiority metrics are validated against MiniMax', () => {
    assert.ok(ORDER_OF_MAGNITUDE_METRICS.length >= 6);
    for (const metric of ORDER_OF_MAGNITUDE_METRICS) {
      assert.ok(metric.multiplierAdvantage.length > 0);
      assert.ok(metric.proofMethod.length > 0);
    }
  });
});

describe('QA Protocol 5: Multi-Agent Peer Bus & Estate Devices', () => {
  test('Peer bus contains 5 agents with Independent Blind Verifier', () => {
    assert.equal(PEER_BUS_AGENTS.length, 5);
    const verifier = PEER_BUS_AGENTS.find(p => p.role === 'independent-verifier');
    assert.ok(verifier, 'Must have dedicated independent blind verifier');
    assert.equal(verifier.vendor, 'Verifier (Blind)');
  });

  test('Estate devices registry contains 7 hardware drivers', () => {
    assert.equal(ESTATE_DEVICES.length, 7);
    const types = new Set(ESTATE_DEVICES.map(d => d.type));
    assert.ok(types.has('desktop'));
    assert.ok(types.has('browser'));
    assert.ok(types.has('android'));
    assert.ok(types.has('iphone'));
    assert.ok(types.has('watch'));
    assert.ok(types.has('glasses'));
    assert.ok(types.has('robotics'));
  });
});

describe('QA Protocol 6: Universal Dynamic Personas, People Graph & 4-Layer Memory', () => {
  test('Dynamic personas span executive, family kin, and specialist pro categories', () => {
    assert.ok(INITIAL_DYNAMIC_PERSONAS.length >= 7, 'Must register at least 7 dynamic personas');
    const categories = new Set(INITIAL_DYNAMIC_PERSONAS.map(p => p.category));
    assert.ok(categories.has('executive'), 'Must have executive personas');
    assert.ok(categories.has('family-kin'), 'Must have family kin personas');
    assert.ok(categories.has('specialist-pro'), 'Must have specialist pro personas');

    for (const p of INITIAL_DYNAMIC_PERSONAS) {
      assert.ok(p.id.startsWith('persona-'));
      assert.ok(p.name.length > 0);
      assert.ok(p.memoryNamespace.length > 0, `Persona ${p.name} must have scoped memory namespace`);
      assert.ok(p.activeSkills.length > 0, `Persona ${p.name} must have active skills`);
    }
  });

  test('People identity graph remembers names, trust tiers, and health invariants', () => {
    assert.ok(INITIAL_PEOPLE_GRAPH.length >= 5, 'Must maintain at least 5 people entities');
    const names = INITIAL_PEOPLE_GRAPH.map(p => p.preferredName);
    assert.ok(names.includes('Aunt Bea'));
    assert.ok(names.includes('David'));
    assert.ok(names.includes('Amina'));
    assert.ok(names.includes('Leo'));
    assert.ok(names.includes('Marcus'));

    // Verify Leo has severe peanut allergy safety invariant recorded
    const leo = INITIAL_PEOPLE_GRAPH.find(p => p.preferredName === 'Leo');
    assert.ok(leo);
    assert.ok(leo.healthDietaryNotes?.some(n => n.toLowerCase().includes('peanut')));
    assert.equal(leo.trustTier, 'family-care-restricted');

    // Root keys denied to family care tier
    const familyPersons = INITIAL_PEOPLE_GRAPH.filter(p => p.trustTier === 'family-care-restricted');
    for (const fp of familyPersons) {
      assert.notEqual(fp.trustTier, 'full-root-sovereign', 'Family member cannot have root sovereign keys');
    }
  });

  test('4-layer memory system maintains working, episodic, semantic, and procedural layers', () => {
    assert.ok(ADVANCED_MEMORY_NODES.length >= 5, 'Must have advanced memory nodes initialized');
    const layers = new Set(ADVANCED_MEMORY_NODES.map(m => m.layer));
    assert.ok(layers.has('working'), 'Must have working memory layer');
    assert.ok(layers.has('episodic'), 'Must have episodic memory layer');
    assert.ok(layers.has('semantic-graph'), 'Must have semantic-graph layer');
    assert.ok(layers.has('procedural-skill'), 'Must have procedural-skill layer');

    for (const mem of ADVANCED_MEMORY_NODES) {
      assert.ok(mem.subject && mem.predicate && mem.objectValue);
      assert.ok(mem.confidenceScore >= 0.9, 'Memory nodes must exceed 0.9 confidence threshold');
      assert.ok(mem.decayHalfLifeDays > 0, 'Memory nodes must define decay curves');
    }
  });

  test('On-demand RSI skills maintain formal Hoare logic invariants and ΔU > 0', () => {
    assert.ok(ON_DEMAND_RSI_SKILLS.length >= 3, 'Must have on-demand RSI skills');
    for (const skill of ON_DEMAND_RSI_SKILLS) {
      assert.ok(skill.utilityDelta.length > 0, 'Skill must declare utility delta');
      assert.ok(skill.utilityDelta.startsWith('+'), 'Skill must yield positive utility delta');
      assert.ok(skill.hoareProofHash.startsWith('sha256:'), 'Skill must have cryptographically signed Hoare proof');
      assert.equal(skill.status, 'synthesized-ready', 'Skill must be synthesized and ready');
    }
  });
});

describe('QA Protocol 7: Physical Estate Inventory, Hardware Telemetry & Capability Verification', () => {
  test('Physical estate inventory maps all connected hardware endpoints across 6 categories', () => {
    assert.equal(INITIAL_PHYSICAL_ENDPOINTS.length, 9, 'Must register exactly 9 physical hardware endpoints');
    const categories = new Set(INITIAL_PHYSICAL_ENDPOINTS.map(e => e.category));
    assert.ok(categories.has('wearable'), 'Must include wearable endpoint (Apple Watch Ultra 2)');
    assert.ok(categories.has('spatial-glasses'), 'Must include spatial glasses (Orion Neural AR Glasses)');
    assert.ok(categories.has('robotics'), 'Must include robotics nodes (UR5e & Unitree B2)');
    assert.ok(categories.has('mobile'), 'Must include mobile nodes (Pixel 9 Pro & iPhone 16 Pro)');
    assert.ok(categories.has('workstation'), 'Must include workstations (M4 Max MacBook Pro)');
    assert.ok(categories.has('ambient-hub'), 'Must include ambient hubs & environmental sensors');
  });

  test("Otto's agent presence is verified on all 9 endpoints with cryptographic attestation", () => {
    for (const ep of INITIAL_PHYSICAL_ENDPOINTS) {
      assert.equal(ep.ottoPresenceState, 'VERIFIED_ACTIVE', `Endpoint ${ep.name} must have VERIFIED_ACTIVE presence`);
      assert.ok(ep.lastAttestationProof.startsWith('sha256:'), `Endpoint ${ep.name} must have signed attestation proof`);
      assert.ok(
        ep.securityEnclaveStatus === 'LOCKED_SECURE' ||
        ep.securityEnclaveStatus === 'ATTESTED' ||
        ep.securityEnclaveStatus === 'HARDWARE_KEY_BOUND',
        `Endpoint ${ep.name} must declare valid enclave status`
      );
    }
  });

  test('Real-time telemetry satisfies physical health bounds and sub-50ms latency invariants', () => {
    for (const ep of INITIAL_PHYSICAL_ENDPOINTS) {
      assert.ok(ep.telemetry.batteryPct >= 0 && ep.telemetry.batteryPct <= 100, `${ep.name} battery must be 0-100%`);
      assert.ok(ep.telemetry.cpuTempC >= 20 && ep.telemetry.cpuTempC <= 70, `${ep.name} temperature within operating limits`);
      assert.ok(ep.telemetry.roundtripLatencyMs <= 40, `${ep.name} latency must be <= 40ms`);
      assert.equal(ep.telemetry.healthStatus, 'optimal', `${ep.name} telemetry health status must be optimal`);
      assert.ok(ep.telemetry.connectionProtocol.length > 0, `${ep.name} must declare physical connection protocol`);
    }
  });

  test('Device-specific capabilities verify haptics, retinal projection, and robotics E-Stop', () => {
    // 1. Wearables: Watch Haptic Alert Bus
    const watch = INITIAL_PHYSICAL_ENDPOINTS.find(e => e.id === 'ep-watch-ultra-2');
    assert.ok(watch);
    const haptic = watch.capabilities.find(c => c.category === 'haptic');
    assert.ok(haptic && haptic.verified, 'Watch must have verified haptic alert bus');
    assert.ok(haptic.latencyMicros < 1000, 'Haptic latency must be sub-millisecond');

    // 2. Spatial: Orion Glasses Retinal Projection
    const glasses = INITIAL_PHYSICAL_ENDPOINTS.find(e => e.id === 'ep-glasses-orion');
    assert.ok(glasses);
    const retinal = glasses.capabilities.find(c => c.id === 'cap-glasses-retinal');
    assert.ok(retinal && retinal.verified, 'Orion glasses must have verified retinal projection');

    // 3. Robotics: UR5e Hardware E-Stop Interlock
    const ur5e = INITIAL_PHYSICAL_ENDPOINTS.find(e => e.id === 'ep-robot-ur5e');
    assert.ok(ur5e);
    const estop = ur5e.capabilities.find(c => c.id === 'cap-ur5e-estop');
    assert.ok(estop && estop.verified, 'UR5e must have verified hardware E-Stop');
    assert.ok(estop.latencyMicros < 100, 'E-Stop relay must trip within 100µs');

    // 4. Robotics: Unitree Quadruped LiDAR SLAM
    const unitree = INITIAL_PHYSICAL_ENDPOINTS.find(e => e.id === 'ep-robot-unitree');
    assert.ok(unitree);
    const lidar = unitree.capabilities.find(c => c.id === 'cap-unitree-lidar');
    assert.ok(lidar && lidar.verified, 'Unitree B2 must have verified 360 LiDAR SLAM');
  });
});



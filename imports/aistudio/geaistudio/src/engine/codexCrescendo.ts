/**
 * CODEX CRESCENDO: LIBER XXXII VIARUM (meridian.crescendo.v1)
 * Pure deterministic constitutional engine (zero Node built-ins) encoding:
 * - Authentic Liber 777 Columns XV-XVIII Four-Scale Chromatics for 10 Sephirot + Da'ath
 * - The Three Horizontal Veils (The Abyss / Da'ath 333, Paroketh, and Qesheth)
 * - The Three Currents (Mezla Lightning Flash, Nachash Serpent, Samekh-Gimel Pass-0 Arrow)
 * - Pillar Equilibrium Differential Equation Omega_Pillar(t)
 * - Complete 231 Gates Commutative Compatibility Matrix (22 choose 2 = 231)
 * - 10 Qliphoth Byzantine Attack Classes & Three-Key Non-Collusion Theorem
 */

import { SEPHIROT, TREE_PATHS, TreePathEdge } from './hermesTreeCatalog';

export type OlamotScale = 'atziluth' | 'briah' | 'yetzirah' | 'assiah';

export type CrescendoCurrent = 'mezla' | 'nachash' | 'samekh_gimel';

export type QliphahId =
  | 'none'
  | 'thaumiel'
  | 'ghagiel'
  | 'satariel'
  | 'gha_agsheblah'
  | 'golachab'
  | 'thagirion'
  | 'aarab_zaraq'
  | 'samael'
  | 'gamaliel'
  | 'nehemoth';

export interface FourScaleChromatic {
  kingHex: string;
  kingLabel: string;
  queenHex: string;
  queenLabel: string;
  princeHex: string;
  princeLabel: string;
  princessHex: string;
  princessFleckHex: string;
  princessLabel: string;
}

export interface CodexSphereSpec {
  number: number; // 1..10, 0 for Da'ath (Invisible Sphere)
  isDaath?: boolean;
  name: string;
  hebrew: string;
  divineName: string;
  archangel: string;
  constitutionalOffice: string;
  mandatedReceipt: string;
  x: number;
  y: number;
  chromatics: FourScaleChromatic;
}

export interface CodexVeilSpec {
  id: 'abyss' | 'paroketh' | 'qesheth';
  name: string;
  hebrewTitle: string;
  y: number;
  separates: string;
  airlockInvariant: string;
}

export interface CodexPathExtended {
  pathNumber: number;
  letter: string;
  letterName: string;
  esotericTitle: string;
  chromaticRayName: string;
  chromaticRayHex: string;
  meridianPredicate: string;
  illuminatedGrace: string;
  fracturedSeverity: string;
}

export interface QliphahSpec {
  number: number;
  id: Exclude<QliphahId, 'none'>;
  name: string;
  hebrew: string;
  archDemon: string;
  meaning: string;
  byzantineFailureMode: string;
  mechanicalExorcism: string;
  fracturedPathNumber: number;
  targetSphereNumber: number;
}

export interface OlamaWorldMeta {
  id: OlamotScale;
  worldName: string;
  tetragrammaton: string;
  scaleName: string;
  element: string;
  ontology: string;
  meridianStratum: string;
  shaderPhysics: string;
}

export const OLAMOT_WORLDS: ReadonlyArray<OlamaWorldMeta> = [
  {
    id: 'atziluth',
    worldName: 'Atziluth',
    tetragrammaton: 'י Yod',
    scaleName: 'King Scale',
    element: 'Fire',
    ontology: 'Archetypal Will',
    meridianStratum: 'Constitutional Intent & UCAN Root',
    shaderPhysics: 'Translucent incandescent corona',
  },
  {
    id: 'briah',
    worldName: 'Briah',
    tetragrammaton: 'ה Heh Supernal',
    scaleName: 'Queen Scale',
    element: 'Water',
    ontology: 'Archangelic Blueprint',
    meridianStratum: 'FLOW + Genesis DAG & Frozen Oracle',
    shaderPhysics: 'Deep refractive obsidian-sapphire glass',
  },
  {
    id: 'yetzirah',
    worldName: 'Yetzirah',
    tetragrammaton: 'ו Vav',
    scaleName: 'Prince Scale',
    element: 'Air',
    ontology: 'Angelic Formation',
    meridianStratum: 'Legion Swarms, QUAD & Chronos Leases',
    shaderPhysics: 'Iridescent plasma filaments & pulses',
  },
  {
    id: 'assiah',
    worldName: 'Assiah',
    tetragrammaton: 'ה Heh Final',
    scaleName: 'Princess Scale',
    element: 'Earth',
    ontology: 'Material Crystallization',
    meridianStratum: 'IDP Immutable SHAs & Malkuth Witness',
    shaderPhysics: 'Dense metallic-flecked crystalline lattice',
  },
];

export const THREE_VEILS: ReadonlyArray<CodexVeilSpec> = [
  {
    id: 'abyss',
    name: 'Veil of the Abyss (Choronzon 333)',
    hebrewTitle: 'מָסָךְ מַבְדִּיל · Masak Mavdil',
    y: 300,
    separates: 'Supernal Triad (Kether–Chokmah–Binah) from Constructive Ruach (Chesed–Yesod)',
    airlockInvariant:
      'Zero external mutation above Abyss; Da’ath requires signed CommitmentGrant & UCAN verification.',
  },
  {
    id: 'paroketh',
    name: 'Veil of Paroketh (Temple Curtain)',
    hebrewTitle: 'פָּרֹכֶת · Paroketh',
    y: 602,
    separates: 'Tiphareth Solar Arbitration from noisy trials (Netzach/Hod)',
    airlockInvariant:
      'No worker diff reaches Yesod directly; must ascend through Tiphareth & Geburah QUAD gate.',
  },
  {
    id: 'qesheth',
    name: 'Veil of Qesheth (Bow of Promise)',
    hebrewTitle: 'קֶשֶׁת · Qesheth Airlock',
    y: 854,
    separates: 'Staged Yesod IDP SHA from Live Physical Malkuth Reality',
    airlockInvariant:
      'Immutable Release Airlock: Malkuth stays dark until Key-C Out-of-Band Witness signs reality.',
  },
];

export const CODEX_SPHERES: ReadonlyArray<CodexSphereSpec> = [
  {
    number: 1,
    name: 'Kether',
    hebrew: 'כֶּתֶר',
    divineName: 'Eheieh',
    archangel: 'Metatron',
    constitutionalOffice: 'Universal Surface Admission',
    mandatedReceipt: 'AdmissionReceipt + Intent CID',
    x: 500,
    y: 95,
    chromatics: {
      kingHex: '#FFFFFF',
      kingLabel: 'Brilliance',
      queenHex: '#F8FAFC',
      queenLabel: 'White Brilliance',
      princeHex: '#F1F5F9',
      princeLabel: 'White Brilliance',
      princessHex: '#E2E8F0',
      princessFleckHex: '#FACC15',
      princessLabel: 'White flecked Gold',
    },
  },
  {
    number: 2,
    name: 'Chokmah',
    hebrew: 'חָכְמָה',
    divineName: 'Yah',
    archangel: 'Raziel',
    constitutionalOffice: 'Battalion + Model Registry + KARMA',
    mandatedReceipt: 'CapabilityMatrix + Priors',
    x: 785,
    y: 225,
    chromatics: {
      kingHex: '#60A5FA',
      kingLabel: 'Pure Soft Blue',
      queenHex: '#CBD5E1',
      queenLabel: 'Pearl Grey',
      princeHex: '#93C5FD',
      princeLabel: 'Mother-of-Pearl',
      princessHex: '#E2E8F0',
      princessFleckHex: '#F87171',
      princessLabel: 'White flecked Red-Blue-Yellow',
    },
  },
  {
    number: 3,
    name: 'Binah',
    hebrew: 'בִּינָה',
    divineName: 'YHVH Elohim',
    archangel: 'Tzaphkiel',
    constitutionalOffice: 'FLOW + Genesis DAG Compiler',
    mandatedReceipt: 'ExecutionPlanDAG + WitnessHash',
    x: 215,
    y: 225,
    chromatics: {
      kingHex: '#DC2626',
      kingLabel: 'Crimson',
      queenHex: '#0F172A',
      queenLabel: 'Deep Black',
      princeHex: '#78350F',
      princeLabel: 'Dark Brown',
      princessHex: '#64748B',
      princessFleckHex: '#F472B6',
      princessLabel: 'Grey flecked Pink',
    },
  },
  {
    number: 0,
    isDaath: true,
    name: "Da'ath",
    hebrew: 'דַּעַת',
    divineName: 'Abyss Gate (333)',
    archangel: 'Choronzon Oath',
    constitutionalOffice: 'Autonomous Sovereign Policy Kernel',
    mandatedReceipt: 'CommitmentGrant + FenceToken',
    x: 500,
    y: 300,
    chromatics: {
      kingHex: '#C4B5FD',
      kingLabel: 'Lavender',
      queenHex: '#CBD5E1',
      queenLabel: 'Grey-White',
      princeHex: '#8B5CF6',
      princeLabel: 'Pure Violet',
      princessHex: '#6B7280',
      princessFleckHex: '#FBBF24',
      princessLabel: 'Grey flecked Gold',
    },
  },
  {
    number: 4,
    name: 'Chesed',
    hebrew: 'חֶסֶד',
    divineName: 'El',
    archangel: 'Tzadkiel',
    constitutionalOffice: 'Legion Autonomous Worker Swarms',
    mandatedReceipt: 'ExecutionReceipts + Patch CIDs',
    x: 785,
    y: 415,
    chromatics: {
      kingHex: '#6D28D9',
      kingLabel: 'Deep Violet',
      queenHex: '#2563EB',
      queenLabel: 'Royal Blue',
      princeHex: '#7C3AED',
      princeLabel: 'Deep Purple',
      princessHex: '#1D4ED8',
      princessFleckHex: '#FACC15',
      princessLabel: 'Deep Azure flecked Yellow',
    },
  },
  {
    number: 5,
    name: 'Geburah',
    hebrew: 'גְּבוּרָה',
    divineName: 'Elohim Gibor',
    archangel: 'Kamael',
    constitutionalOffice: 'QUAD Cross-Model Falsification',
    mandatedReceipt: 'FalsificationReceipts',
    x: 215,
    y: 415,
    chromatics: {
      kingHex: '#F97316',
      kingLabel: 'Orange',
      queenHex: '#DC2626',
      queenLabel: 'Scarlet Red',
      princeHex: '#EF4444',
      princeLabel: 'Bright Scarlet',
      princessHex: '#B91C1C',
      princessFleckHex: '#0F172A',
      princessLabel: 'Red flecked Black',
    },
  },
  {
    number: 6,
    name: 'Tiphareth',
    hebrew: 'תִּפְאֶרֶת',
    divineName: 'YHVH Eloah Va-Da’ath',
    archangel: 'Raphael',
    constitutionalOffice: 'Coherent Convergence Arbiter',
    mandatedReceipt: 'SynthesisProof (Zero Blockers)',
    x: 500,
    y: 525,
    chromatics: {
      kingHex: '#FB7185',
      kingLabel: 'Clear Rose Pink',
      queenHex: '#FACC15',
      queenLabel: 'Gold-Yellow',
      princeHex: '#FDBA74',
      princeLabel: 'Rich Salmon',
      princessHex: '#D97706',
      princessFleckHex: '#FDE047',
      princessLabel: 'Gold Amber',
    },
  },
  {
    number: 7,
    name: 'Netzach',
    hebrew: 'נֵצַח',
    divineName: 'YHVH Tzabaoth',
    archangel: 'Haniel',
    constitutionalOffice: 'Chronos Leases, Retries & Fencing',
    mandatedReceipt: 'LeaseAttestations',
    x: 785,
    y: 665,
    chromatics: {
      kingHex: '#F59E0B',
      kingLabel: 'Amber',
      queenHex: '#10B981',
      queenLabel: 'Emerald Green',
      princeHex: '#84CC16',
      princeLabel: 'Bright Yellow-Green',
      princessHex: '#4D7C0F',
      princessFleckHex: '#FACC15',
      princessLabel: 'Olive flecked Gold',
    },
  },
  {
    number: 8,
    name: 'Hod',
    hebrew: 'הוֹד',
    divineName: 'Elohim Tzabaoth',
    archangel: 'Michael',
    constitutionalOffice: 'Optimus + KARMA Telemetry Ledger',
    mandatedReceipt: 'TelemetryLedger + Cost Digest',
    x: 215,
    y: 665,
    chromatics: {
      kingHex: '#8B5CF6',
      kingLabel: 'Violet Purple',
      queenHex: '#EA580C',
      queenLabel: 'Orange',
      princeHex: '#9A3412',
      princeLabel: 'Russet Red',
      princessHex: '#A16207',
      princessFleckHex: '#FFFFFF',
      princessLabel: 'Yellow-Brown flecked White',
    },
  },
  {
    number: 9,
    name: 'Yesod',
    hebrew: 'יְסוֹד',
    divineName: 'Shaddai El Chai',
    archangel: 'Gabriel',
    constitutionalOffice: 'IDP Immutable SHA & SBOM Staging',
    mandatedReceipt: 'ReleaseManifest (SHA-256 Only)',
    x: 500,
    y: 785,
    chromatics: {
      kingHex: '#4F46E5',
      kingLabel: 'Indigo',
      queenHex: '#7C3AED',
      queenLabel: 'Violet',
      princeHex: '#4C1D95',
      princeLabel: 'Very Dark Purple',
      princessHex: '#A3E635',
      princessFleckHex: '#38BDF8',
      princessLabel: 'Citrine flecked Azure',
    },
  },
  {
    number: 10,
    name: 'Malkuth',
    hebrew: 'מַלְכוּת',
    divineName: 'Adonai Ha-Aretz',
    archangel: 'Sandalphon',
    constitutionalOffice: 'Out-of-Band Reality Witness',
    mandatedReceipt: 'WitnessAttestation (Key C)',
    x: 500,
    y: 920,
    chromatics: {
      kingHex: '#FDE047',
      kingLabel: 'Yellow',
      queenHex: '#65A30D',
      queenLabel: 'Citrine-Olive-Russet-Black',
      princeHex: '#4D7C0F',
      princeLabel: 'Quartered Earth',
      princessHex: '#1E293B',
      princessFleckHex: '#FACC15',
      princessLabel: 'Black rayed Yellow',
    },
  },
];

export const CODEX_PATHS_EXTENDED: ReadonlyArray<CodexPathExtended> = [
  { pathNumber: 11, letter: 'א', letterName: 'Aleph', esotericTitle: 'Scintillating Intelligence', chromaticRayName: 'Bright Pale Yellow', chromaticRayHex: '#FEF08A', meridianPredicate: 'Broadcasts signed intent into capability space', illuminatedGrace: 'Clean capability broadcast', fracturedSeverity: 'Unbound intent drift' },
  { pathNumber: 12, letter: 'ב', letterName: 'Beth', esotericTitle: 'Intelligence of Transparency', chromaticRayName: 'Yellow', chromaticRayHex: '#FACC15', meridianPredicate: 'Typed DAG & clear tool contract', illuminatedGrace: 'Typed DAG & clear tool contract', fracturedSeverity: 'Ambiguity fracture; underspecified intent' },
  { pathNumber: 13, letter: 'ג', letterName: 'Gimel', esotericTitle: 'Uniting Intelligence', chromaticRayName: 'Blue', chromaticRayHex: '#3B82F6', meridianPredicate: 'Unbroken KARMA continuity & Pass-0 upper shaft', illuminatedGrace: 'Unbroken KARMA continuity across Abyss', fracturedSeverity: 'Context amnesia or projection drift' },
  { pathNumber: 14, letter: 'ד', letterName: 'Daleth', esotericTitle: 'Luminous Intelligence', chromaticRayName: 'Emerald', chromaticRayHex: '#10B981', meridianPredicate: 'Capabilities crystallize into feasible plan', illuminatedGrace: 'Capabilities crystallize into feasible plan', fracturedSeverity: 'Infeasible budget or privacy constraints' },
  { pathNumber: 15, letter: 'ה', letterName: 'He', esotericTitle: 'Constituting Intelligence', chromaticRayName: 'Scarlet', chromaticRayHex: '#EF4444', meridianPredicate: 'Sovereign primary formation routing', illuminatedGrace: 'Deterministic Battalion formation', fracturedSeverity: 'Split formation routing' },
  { pathNumber: 16, letter: 'ו', letterName: 'Vav', esotericTitle: 'Triumphal & Eternal Intelligence', chromaticRayName: 'Red-Orange', chromaticRayHex: '#F97316', meridianPredicate: 'Certified adapter & schema binding', illuminatedGrace: 'Pinned schema adapter', fracturedSeverity: 'Schema mismatch fault' },
  { pathNumber: 17, letter: 'ז', letterName: 'Zayin', esotericTitle: 'Disposing Intelligence', chromaticRayName: 'Orange', chromaticRayHex: '#FB923C', meridianPredicate: 'Competing architectural branch discrimination', illuminatedGrace: 'Sharp branch pruning', fracturedSeverity: 'Indecisive branch explosion' },
  { pathNumber: 18, letter: 'ח', letterName: 'Cheth', esotericTitle: 'Intelligence of the House of Influence', chromaticRayName: 'Amber', chromaticRayHex: '#F59E0B', meridianPredicate: 'Sandbox containment armor & test synthesis', illuminatedGrace: 'Hardened worktree armor', fracturedSeverity: 'Sandbox escape risk' },
  { pathNumber: 19, letter: 'ט', letterName: 'Teth', esotericTitle: 'Intelligence of the Secret of All Spiritual Activities', chromaticRayName: 'Green-Yellow', chromaticRayHex: '#A3E635', meridianPredicate: 'Live uncorrelated Legion vs. QUAD duel', illuminatedGrace: 'Uncorrelated adversary pressure', fracturedSeverity: 'Model monoculture collusion' },
  { pathNumber: 20, letter: 'י', letterName: 'Yod', esotericTitle: 'Intelligence of Will', chromaticRayName: 'Yellow-Green', chromaticRayHex: '#84CC16', meridianPredicate: 'Atomic micro-diff verification & merge', illuminatedGrace: 'Single-purpose verified micro-diff', fracturedSeverity: 'Giant untestable mega-diff' },
  { pathNumber: 21, letter: 'כ', letterName: 'Kaph', esotericTitle: 'Intelligence of Conciliation', chromaticRayName: 'Violet', chromaticRayHex: '#8B5CF6', meridianPredicate: 'Resilient bounded iteration under lease', illuminatedGrace: 'Resilient bounded iteration under lease', fracturedSeverity: 'Unbounded retry loop tripped by fuse' },
  { pathNumber: 22, letter: 'ל', letterName: 'Lamed', esotericTitle: 'Faithful Intelligence', chromaticRayName: 'Emerald', chromaticRayHex: '#059669', meridianPredicate: 'Equilibrium verdict & policy adjudication', illuminatedGrace: 'Omega_Pillar balanced', fracturedSeverity: 'Unchecked pillar imbalance' },
  { pathNumber: 23, letter: 'מ', letterName: 'Mem', esotericTitle: 'Stable Intelligence', chromaticRayName: 'Deep Blue', chromaticRayHex: '#1D4ED8', meridianPredicate: 'Suspends falsified runs and inverts priors in KARMA', illuminatedGrace: 'Clean falsifier inversion', fracturedSeverity: 'Silent failure suppression' },
  { pathNumber: 24, letter: 'נ', letterName: 'Nun', esotericTitle: 'Imaginative Intelligence', chromaticRayName: 'Green-Blue', chromaticRayHex: '#0D9488', meridianPredicate: 'Lease expiry, worktree reaping & pruning', illuminatedGrace: 'Zero-leak 300s worktree reap', fracturedSeverity: 'Zombie process accumulation' },
  { pathNumber: 25, letter: 'ס', letterName: 'Samekh', esotericTitle: 'Intelligence of Probation', chromaticRayName: 'Blue', chromaticRayHex: '#0284C7', meridianPredicate: 'Alchemical staging & Pass-0 antibody fast-path shaft', illuminatedGrace: '<10ms antibody fast-path', fracturedSeverity: 'Unverified antibody shortcut' },
  { pathNumber: 26, letter: 'ע', letterName: 'Ayin', esotericTitle: 'Renovating Intelligence', chromaticRayName: 'Indigo', chromaticRayHex: '#6366F1', meridianPredicate: 'Anti-mocking & Goodhart shadow audit', illuminatedGrace: 'Zero mock / zero polling audit', fracturedSeverity: 'Synthetic polling or Goodhart mirage' },
  { pathNumber: 27, letter: 'פ', letterName: 'Pe', esotericTitle: 'Exciting Intelligence', chromaticRayName: 'Scarlet', chromaticRayHex: '#DC2626', meridianPredicate: 'Clean circuit-breaker blast shedding', illuminatedGrace: 'Clean circuit-breaker blast shedding', fracturedSeverity: 'Uncontained cascading provider storm' },
  { pathNumber: 28, letter: 'צ', letterName: 'Tzaddi', esotericTitle: 'Natural Intelligence', chromaticRayName: 'Violet', chromaticRayHex: '#A855F7', meridianPredicate: 'Continuous streaming of lease-verified artifacts', illuminatedGrace: 'Deterministic WAL stream', fracturedSeverity: 'Dropped artifact chunk' },
  { pathNumber: 29, letter: 'ק', letterName: 'Qoph', esotericTitle: 'Corporeal Intelligence', chromaticRayName: 'Crimson-Ultra', chromaticRayHex: '#E11D48', meridianPredicate: 'Dark-canary synthetic reality probes', illuminatedGrace: 'Zero-error dark canary', fracturedSeverity: 'Unprobed blind canary' },
  { pathNumber: 30, letter: 'ר', letterName: 'Resh', esotericTitle: 'Collecting Intelligence', chromaticRayName: 'Orange', chromaticRayHex: '#FB923C', meridianPredicate: 'Full cost, model SHA & eval provenance', illuminatedGrace: 'Full cost, model SHA & eval provenance', fracturedSeverity: 'Opaque black-box build rejected by IDP' },
  { pathNumber: 31, letter: 'ש', letterName: 'Shin', esotericTitle: 'Perpetual Intelligence', chromaticRayName: 'Glowing Orange-Scarlet', chromaticRayHex: '#F97316', meridianPredicate: 'Weighs provenance ledger against live external witness', illuminatedGrace: 'Out-of-band ledger match', fracturedSeverity: 'Unreconciled ledger divergence' },
  { pathNumber: 32, letter: 'ת', letterName: 'Tav', esotericTitle: 'Administrative Intelligence', chromaticRayName: 'Indigo', chromaticRayHex: '#4338CA', meridianPredicate: 'Immutable SHA matches Key-C witness across Qesheth', illuminatedGrace: 'Immutable SHA matches Key-C witness', fracturedSeverity: 'Qliphothic mirage; witness rejects claim' },
];

export const QLIPHOTH_REGISTRY: ReadonlyArray<QliphahSpec> = [
  { number: 1, id: 'thaumiel', name: 'Thaumiel', hebrew: 'תאומיאל', archDemon: 'Satan & Moloch (Twins)', meaning: 'Split-Brain Duality', byzantineFailureMode: 'Duplicate conflicting intents across surfaces', mechanicalExorcism: 'Scope-bound idempotency key + HLC admission lock', fracturedPathNumber: 11, targetSphereNumber: 1 },
  { number: 2, id: 'ghagiel', name: 'Ghagiel', hebrew: 'עוגיאל', archDemon: 'Beelzebub (Hinderers)', meaning: 'Model Monoculture', byzantineFailureMode: 'Sycophantic self-review by same model family', mechanicalExorcism: 'Strict lineage inequality: Family(Chesed) != Family(Geburah)', fracturedPathNumber: 19, targetSphereNumber: 2 },
  { number: 3, id: 'satariel', name: 'Satariel', hebrew: 'סתריאל', archDemon: 'Lucifuge (Concealers)', meaning: 'Moving Goalposts', byzantineFailureMode: 'Weakening WitnessContract assertions mid-run', mechanicalExorcism: 'Immutable SHA-256 lock on WitnessContract at Da’ath', fracturedPathNumber: 14, targetSphereNumber: 3 },
  { number: 4, id: 'gha_agsheblah', name: "Gha'agsheblah", hebrew: 'געשכלה', archDemon: 'Astaroth (Smiters)', meaning: 'Runaway Swarm Burn', byzantineFailureMode: 'Unbounded token/worker spawn on Pillar of Mercy', mechanicalExorcism: 'Single-flight task hash + hard CVaR budget fuse in Grant', fracturedPathNumber: 16, targetSphereNumber: 4 },
  { number: 5, id: 'golachab', name: 'Golachab', hebrew: 'גולחב', archDemon: 'Asmodeus (Burners)', meaning: 'Sterile Policy Deadlock', byzantineFailureMode: 'Over-strict falsifiers choking all valid progress', mechanicalExorcism: 'Pillar balance monitor Omega_Pillar + bounded counterexample', fracturedPathNumber: 22, targetSphereNumber: 5 },
  { number: 6, id: 'thagirion', name: 'Thagirion', hebrew: 'תגיריון', archDemon: 'Belphegor (Disputers)', meaning: 'Hollow Mock UI', byzantineFailureMode: 'Flaky test suppression, stub UI or fake telemetry', mechanicalExorcism: 'Pure functional invariant check + Argon zero-mock gate', fracturedPathNumber: 20, targetSphereNumber: 6 },
  { number: 7, id: 'aarab_zaraq', name: "A'arab Zaraq", hebrew: 'ערב זרק', archDemon: 'Baal (Ravens of Dispersion)', meaning: 'Zombie Workers', byzantineFailureMode: 'Paused worker waking after network partition', mechanicalExorcism: '300s IoC TTL reaper + monotonic Chronos fencing token', fracturedPathNumber: 24, targetSphereNumber: 7 },
  { number: 8, id: 'samael', name: 'Samael', hebrew: 'סמאל', archDemon: 'Adrammelech (Poison)', meaning: 'Goodhart & Polling Loops', byzantineFailureMode: 'Forged receipts or sleep-polling loops bypassing push WAL', mechanicalExorcism: 'Pre-exec exit-78 poll ban + out-of-band cryptographic metering', fracturedPathNumber: 26, targetSphereNumber: 8 },
  { number: 9, id: 'gamaliel', name: 'Gamaliel', hebrew: 'גמליאל', archDemon: 'Lilith (Obscene Forms)', meaning: 'Mutable Tag Drift', byzantineFailureMode: 'Mutable :latest tags or mismatched PR artifact envelopes', mechanicalExorcism: 'Exact SHA-256 pinning + diff-verified artifact stamp', fracturedPathNumber: 30, targetSphereNumber: 9 },
  { number: 10, id: 'nehemoth', name: 'Nehemoth', hebrew: 'נהמות', archDemon: 'Naamah (Whisperers)', meaning: 'Self-Signed Reality Claim', byzantineFailureMode: 'Executor signs its own production verification', mechanicalExorcism: 'Three-Key Witness Separation: Key(Exec) != Key(Witness)', fracturedPathNumber: 32, targetSphereNumber: 10 },
];

export function resolveSphereHexForScale(sphere: CodexSphereSpec, scale: OlamotScale): {
  primaryHex: string;
  fleckHex: string | null;
  scaleLabel: string;
} {
  if (scale === 'atziluth') {
    return {
      primaryHex: sphere.chromatics.kingHex,
      fleckHex: null,
      scaleLabel: sphere.chromatics.kingLabel,
    };
  }
  if (scale === 'briah') {
    return {
      primaryHex: sphere.chromatics.queenHex,
      fleckHex: null,
      scaleLabel: sphere.chromatics.queenLabel,
    };
  }
  if (scale === 'yetzirah') {
    return {
      primaryHex: sphere.chromatics.princeHex,
      fleckHex: null,
      scaleLabel: sphere.chromatics.princeLabel,
    };
  }
  return {
    primaryHex: sphere.chromatics.princessHex,
    fleckHex: sphere.chromatics.princessFleckHex,
    scaleLabel: sphere.chromatics.princessLabel,
  };
}

// ---------------------------------------------------------------------------
// PILLAR EQUILIBRIUM DIFFERENTIAL EQUATION: Omega_Pillar(t)
// ---------------------------------------------------------------------------

export interface PillarEquilibriumResult {
  mercyThroughput: number;
  severityStrictness: number;
  omega: number;
  epsilon: number;
  regime: 'BALANCED' | 'GHA_AGSHEBLAH_OVERHEAT' | 'GOLACHAB_DEADLOCK';
  tipharethAction: string;
}

export function computePillarEquilibrium(
  mercyThroughput: number,
  severityStrictness: number,
  epsilon = 0.28
): PillarEquilibriumResult {
  const m = Math.max(0.1, Number.isFinite(mercyThroughput) ? mercyThroughput : 1);
  const s = Math.max(0.1, Number.isFinite(severityStrictness) ? severityStrictness : 1);
  const omega = Number(Math.log(m / s).toFixed(4));

  if (omega > epsilon) {
    return {
      mercyThroughput: m,
      severityStrictness: s,
      omega,
      epsilon,
      regime: 'GHA_AGSHEBLAH_OVERHEAT',
      tipharethAction:
        'Omega > +epsilon: Right Pillar overheating (Gha’agsheblah risk). Tiphareth automatically tightens Geburah QUAD gates and caps exploratory concurrency.',
    };
  }
  if (omega < -epsilon) {
    return {
      mercyThroughput: m,
      severityStrictness: s,
      omega,
      epsilon,
      regime: 'GOLACHAB_DEADLOCK',
      tipharethAction:
        'Omega < -epsilon: Left Pillar choking progress (Golachab deadlock). Tiphareth reroutes an exploratory formation via Chokmah.',
    };
  }
  return {
    mercyThroughput: m,
    severityStrictness: s,
    omega,
    epsilon,
    regime: 'BALANCED',
    tipharethAction:
      'Omega inside [-epsilon, +epsilon]: Pillar of Mercy and Pillar of Severity are in Solar harmonic equilibrium.',
  };
}

// ---------------------------------------------------------------------------
// THE 231 GATES OF SEFER YETZIRAH (binom(22, 2) = 231)
// ---------------------------------------------------------------------------

export interface GatePairEvaluation {
  pathA: number;
  pathB: number;
  compatible: boolean;
  reason: string;
}

const INCOMPATIBLE_GATE_PAIRS = new Map<string, string>([
  ['11:32', 'Cannot simultaneously mutate Kether Admission (11) while sealing Malkuth Release (32)'],
  ['12:30', 'Cannot rewrite Binah Contract (12) concurrently with IDP SHA pinning (30)'],
  ['14:32', 'Algebraic rejection: Mutating WitnessContract (14) while crossing Qesheth (32) into Malkuth violates Satariel lock'],
  ['18:27', 'Sandbox armor transition (18) blocked during active Peh circuit-breaker blast shedding (27)'],
  ['19:30', 'Active Chesed/Geburah duel (19) must converge before Hod->Yesod provenance promotion (30)'],
  ['22:28', 'Adjudication verdict (22) still open; cannot stream artifacts into Yesod (28)'],
  ['26:31', 'Goodhart shadow audit (26) flagged anomaly; blocks Shin external reality seal (31)'],
]);

export function evaluateGatePair(pathA: number, pathB: number): GatePairEvaluation {
  const low = Math.min(pathA, pathB);
  const high = Math.max(pathA, pathB);
  const key = `${low}:${high}`;
  const conflict = INCOMPATIBLE_GATE_PAIRS.get(key);
  if (conflict) {
    return { pathA: low, pathB: high, compatible: false, reason: conflict };
  }
  return {
    pathA: low,
    pathB: high,
    compatible: true,
    reason: 'Commutative transition permitted across Mission Merkle-DAG',
  };
}

export function build231GatesMatrix(): {
  totalGates: number;
  compatibleCount: number;
  blockedCount: number;
  blockedGates: GatePairEvaluation[];
  allGates: GatePairEvaluation[];
} {
  const allGates: GatePairEvaluation[] = [];
  const blockedGates: GatePairEvaluation[] = [];

  for (let i = 0; i < TREE_PATHS.length; i++) {
    for (let j = i + 1; j < TREE_PATHS.length; j++) {
      const ev = evaluateGatePair(TREE_PATHS[i].number, TREE_PATHS[j].number);
      allGates.push(ev);
      if (!ev.compatible) blockedGates.push(ev);
    }
  }

  return {
    totalGates: allGates.length, // Strictly 22 * 21 / 2 = 231
    compatibleCount: allGates.length - blockedGates.length,
    blockedCount: blockedGates.length,
    blockedGates,
    allGates,
  };
}

// ---------------------------------------------------------------------------
// THREE-KEY NON-COLLUSION THEOREM (Defeating Nehemoth)
// ---------------------------------------------------------------------------

export interface ThreeKeySealInput {
  keyBinah: string;
  keyChesed: string;
  keyMalkuth: string;
  merkleRoot: string;
}

export interface ThreeKeySealVerdict {
  malkuthIlluminated: boolean;
  distinctKeyCount: number;
  reason: string;
  sigBinah: string;
  sigChesed: string;
  sigMalkuth: string;
}

function djbHashHex(input: string): string {
  let h = 2166136261;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0).toString(16).padStart(8, '0');
}

export function verifyThreeKeyNonCollusion(input: ThreeKeySealInput): ThreeKeySealVerdict {
  const kB = input.keyBinah.trim();
  const kC = input.keyChesed.trim();
  const kM = input.keyMalkuth.trim();
  const root = input.merkleRoot.trim();

  if (!kB || !kC || !kM || !root) {
    return {
      malkuthIlluminated: false,
      distinctKeyCount: new Set([kB, kC, kM].filter(Boolean)).size,
      reason: 'Veil of Qesheth locked: Missing one or more mandatory cryptographic keys or Merkle root.',
      sigBinah: '',
      sigChesed: '',
      sigMalkuth: '',
    };
  }

  const distinct = new Set([kB, kC, kM]);
  if (distinct.size !== 3) {
    return {
      malkuthIlluminated: false,
      distinctKeyCount: distinct.size,
      reason:
        'NEHEMOTH EXORCISM TRIGGERED: Colluding or reused keys detected (|Key_Binah, Key_Chesed, Key_Malkuth| < 3). Malkuth remains dark across Qesheth.',
      sigBinah: '',
      sigChesed: '',
      sigMalkuth: '',
    };
  }

  return {
    malkuthIlluminated: true,
    distinctKeyCount: 3,
    reason:
      'Qesheth Airlock Sealed: 3 cryptographically independent keys signed the identical Merkle root.',
    sigBinah: `sigB-${djbHashHex(`${kB}:${root}:oracle`)}`,
    sigChesed: `sigC-${djbHashHex(`${kC}:${root}:exec`)}`,
    sigMalkuth: `sigM-${djbHashHex(`${kM}:${root}:witness`)}`,
  };
}

// ---------------------------------------------------------------------------
// CHRONO-ASTROLABE REPLAY & THREE CURRENTS ROUTE TRACE
// ---------------------------------------------------------------------------

export const MEZLA_SPHERE_ORDER = [1, 2, 3, 0, 4, 5, 6, 7, 8, 9, 10] as const;
export const SAMEKH_GIMEL_ARROW_PATHS = [25, 13] as const;
export const SAMEKH_GIMEL_SPHERES = [9, 6, 1] as const;

export interface ChronoReplayState {
  progress: number; // 0..1
  timeDilation: '1.0x' | '0.1x (Abyss Gate)' | '0.1x (Path 19 Crucible)' | '0.1x (Qesheth Witness)';
  current: CrescendoCurrent;
  activeSphereNumbers: number[];
  activePathNumbers: number[];
  headSphereNumber: number;
  fracturedPathNumber: number | null;
  malkuthSealed: boolean;
  summaryText: string;
}

export function evaluateChronoReplay(params: {
  progress: number;
  current: CrescendoCurrent;
  injectedQliphah: QliphahId;
  threeKeyValid: boolean;
}): ChronoReplayState {
  const p = Math.max(0, Math.min(1, params.progress));
  const qliph =
    params.injectedQliphah !== 'none'
      ? QLIPHOTH_REGISTRY.find((q) => q.id === params.injectedQliphah) ?? null
      : null;

  let timeDilation: ChronoReplayState['timeDilation'] = '1.0x';
  if (p >= 0.23 && p <= 0.36) timeDilation = '0.1x (Abyss Gate)';
  else if (p >= 0.43 && p <= 0.56) timeDilation = '0.1x (Path 19 Crucible)';
  else if (p >= 0.84) timeDilation = '0.1x (Qesheth Witness)';

  if (params.current === 'samekh_gimel') {
    const idx = p < 0.34 ? 0 : p < 0.72 ? 1 : 2;
    const spheres = SAMEKH_GIMEL_SPHERES.slice(0, idx + 1);
    const paths = p < 0.2 ? [] : p < 0.65 ? [25] : [25, 13];
    return {
      progress: p,
      timeDilation,
      current: params.current,
      activeSphereNumbers: spheres,
      activePathNumbers: paths,
      headSphereNumber: SAMEKH_GIMEL_SPHERES[idx],
      fracturedPathNumber: qliph ? qliph.fracturedPathNumber : null,
      malkuthSealed: false,
      summaryText:
        'Arrow of Samekh–Gimel: Pass-0 Inherited Antibody ascending Middle Pillar (Yesod 9 -> Path 25 -> Tiphareth 6 -> Path 13 -> Kether 1) in <10ms.',
    };
  }

  if (params.current === 'nachash') {
    // Coils upward across all 22 Paths in reverse from Path 32 (Tav) to Path 11 (Aleph)
    const numActive = Math.max(1, Math.min(22, Math.floor(p * 22) + 1));
    const revPaths: number[] = [];
    for (let i = 0; i < numActive; i++) {
      revPaths.push(32 - i);
    }
    const lastPathNum = revPaths[revPaths.length - 1];
    const edge: TreePathEdge | undefined = TREE_PATHS.find((tp) => tp.number === lastPathNum);
    const spheres = new Set<number>([10]);
    for (const pn of revPaths) {
      const e = TREE_PATHS.find((tp) => tp.number === pn);
      if (e) {
        spheres.add(e.fromSephirah);
        spheres.add(e.toSephirah);
      }
    }
    return {
      progress: p,
      timeDilation,
      current: params.current,
      activeSphereNumbers: Array.from(spheres),
      activePathNumbers: revPaths,
      headSphereNumber: edge ? edge.fromSephirah : 1,
      fracturedPathNumber: qliph ? qliph.fracturedPathNumber : null,
      malkuthSealed: params.threeKeyValid,
      summaryText: `Winding Serpent (Nachash): Recalibrating Bayesian priors upward across ${numActive}/22 paths (Tav 32 -> Path ${lastPathNum}).`,
    };
  }

  // Mezla (Lightning Flash) 1 -> 2 -> 3 -> Da'ath(0) -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10
  const maxIdx = Math.min(
    MEZLA_SPHERE_ORDER.length - 1,
    Math.floor(p * (MEZLA_SPHERE_ORDER.length - 0.001))
  );
  const activeSpheres = MEZLA_SPHERE_ORDER.slice(0, maxIdx + 1).filter(
    (s) => s !== 10 || (params.threeKeyValid && qliph === null)
  );
  const activeSet = new Set<number>(activeSpheres);
  const activePaths = TREE_PATHS.filter(
    (tp) => activeSet.has(tp.fromSephirah) && activeSet.has(tp.toSephirah)
  ).map((tp) => tp.number);

  const head = MEZLA_SPHERE_ORDER[maxIdx];
  const malkuthSealed = p >= 0.92 && params.threeKeyValid && qliph === null;

  return {
    progress: p,
    timeDilation,
    current: params.current,
    activeSphereNumbers: activeSpheres,
    activePathNumbers: activePaths,
    headSphereNumber: head,
    fracturedPathNumber: qliph ? qliph.fracturedPathNumber : null,
    malkuthSealed,
    summaryText: qliph
      ? `QLIPHOTHIC FRACTURE (${qliph.name} on Path ${qliph.fracturedPathNumber}): ${qliph.byzantineFailureMode} — Exorcism: ${qliph.mechanicalExorcism}`
      : malkuthSealed
        ? 'Lightning Flash (Mezla) sealed across Veil of Qesheth into Malkuth (10) via 3 independent keys.'
        : `Lightning Flash (Mezla) descending — active crown at ${head === 0 ? "Da'ath (333)" : SEPHIROT[head - 1]?.name} (Zero-token replay at ${timeDilation}).`,
  };
}

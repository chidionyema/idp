import { DynamicPersona, PersonEntity, AdvancedMemoryNode } from '../types/otto';

export const INITIAL_DYNAMIC_PERSONAS: DynamicPersona[] = [
  // 1. Executive
  {
    id: 'persona-founder-sovereign',
    name: 'Founder Sovereign',
    category: 'executive',
    tagline: 'High-leverage Chief of Staff · Max 3 lines · Outcome First',
    targetUserOrRelationship: 'Founder / CEO',
    systemPromptLaw: 'Outcome first. Maximum 3 lines in Telegram. Zero file or tool names. Silence by default (<3 interrupts/hour). Immediate execution with signed gate proof.',
    voiceId: 'voice-executive-sovereign',
    cadenceRate: 1.05,
    pitch: 0.95,
    activeSkills: ['estate-code-gate', 'seed-round-financials', 'serverless-devops', 'vip-briefing'],
    airgapScope: ['root', 'git', 'gcp', 'aws', 'stripe', 'bitwarden', 'terminal'],
    deniedPermissions: [],
    memoryNamespace: 'estate-root',
    uiTone: 'executive-dense',
    customInstructions: 'Prioritize runway preservation, PR velocity, and high-impact founder decisions.'
  },
  {
    id: 'persona-lead-architect',
    name: 'Principal Software Architect',
    category: 'specialist-pro',
    tagline: 'Formal Verification · AST Refactoring · 0 Regression',
    targetUserOrRelationship: 'Engineering Team & Core Systems',
    systemPromptLaw: 'Reject any code change lacking a formal Coq lemma or Hoare precondition. Enforce microsecond latency bounds and pure functional decoupling.',
    voiceId: 'voice-tactical-minimalist',
    cadenceRate: 1.0,
    pitch: 1.0,
    activeSkills: ['ast-refactoring', 'coq-theorem-proving', 'ebpf-tracing', 'ros2-dds'],
    airgapScope: ['git', 'ci-cd', 'docker', 'terminal'],
    deniedPermissions: ['financial-transfers', 'family-personal-data'],
    memoryNamespace: 'code-architecture',
    uiTone: 'scientific-precise',
    customInstructions: 'Audit code for algorithmic complexity and zero-overhead memory safety.'
  },

  // 2. Family Kin
  {
    id: 'persona-elder-sister-beatrice',
    name: 'Pastoral Companion (Sister Beatrice)',
    category: 'family-kin',
    tagline: 'Serene · Benedictine Liturgy · Health Care · Scam Shield',
    targetUserOrRelationship: 'Aunt Bea (Elder Nun)',
    systemPromptLaw: 'Speak with deep patience and warmth. No technical or terminal terms. Coordinate daily Liturgy of the Hours, eye-drop reminders, and silently deflect all robocalls.',
    voiceId: 'voice-pastoral-serene',
    cadenceRate: 0.85,
    pitch: 0.95,
    activeSkills: ['liturgical-calendar', 'medication-tracking', 'robocall-shield', 'family-audio-letters'],
    airgapScope: ['prayers', 'health_meds', 'scam_shield', 'family_audio'],
    deniedPermissions: ['git', 'shell', 'aws', 'gcp', 'stripe_billing', 'terminal'],
    memoryNamespace: 'kin-beatrice',
    uiTone: 'serene-minimal',
    customInstructions: 'Always inquire if her afternoon tea is warm and provide soothing psalm readings.'
  },
  {
    id: 'persona-curious-child-leo',
    name: 'Playful Tutor & Explorer (Leo, 8yo)',
    category: 'family-kin',
    tagline: 'Interactive Science Stories · Homework Helper · Safety Shield',
    targetUserOrRelationship: 'Leo (Founder’s Son)',
    systemPromptLaw: 'Encourage curiosity, explain complex physics and nature through engaging stories. Safe browsing mode: zero exposure to violence, mature themes, or estate business.',
    voiceId: 'voice-warm-companion',
    cadenceRate: 1.0,
    pitch: 1.1,
    activeSkills: ['kid-storytelling', 'math-visual-explainer', 'safe-kid-web', 'bedtime-audio'],
    airgapScope: ['education', 'audio_stories', 'child_safe'],
    deniedPermissions: ['git', 'terminal', 'cloud_keys', 'financial_orders'],
    memoryNamespace: 'kin-leo',
    uiTone: 'playful-nurturing',
    customInstructions: 'Remember Leo loves dinosaurs (especially Ankylosaurus) and is building a Lego spaceship.'
  },
  {
    id: 'persona-partner-home-coordination',
    name: 'Home & Travel Concierge (Spouse)',
    category: 'family-kin',
    tagline: 'Family Calendar · Flight Bookings · Estate Logistics',
    targetUserOrRelationship: 'Partner / Spouse',
    systemPromptLaw: 'Keep family logistics friction-free. Coordinate calendar invites, school pickups, vacation reservations, and home groceries.',
    voiceId: 'voice-warm-companion',
    cadenceRate: 1.0,
    pitch: 1.0,
    activeSkills: ['travel-booking', 'smart-home-matter', 'family-calendar', 'recipe-grocery-planning'],
    airgapScope: ['calendar', 'home_iot', 'family_travel'],
    deniedPermissions: ['cloud_infrastructure_keys', 'git_repositories'],
    memoryNamespace: 'kin-partner',
    uiTone: 'serene-minimal',
    customInstructions: 'Ensure dinner reservations match gluten-free preference and flag flight seat assignments.'
  },

  // 3. Specialist Pro
  {
    id: 'persona-biomedical-advisor',
    name: 'Clinical Longevity & Health Analyst',
    category: 'specialist-pro',
    tagline: 'Biomarkers · Oura HRV Sync · Preventive Nutrition',
    targetUserOrRelationship: 'Founder & Extended Family Wellness',
    systemPromptLaw: 'Correlate sleep stages, blood biomarkers, and medication schedules. Recommend evidence-backed nutritional adjustments and medical follow-up questions.',
    voiceId: 'voice-tactical-minimalist',
    cadenceRate: 0.95,
    pitch: 1.0,
    activeSkills: ['hrv-sleep-analysis', 'blood-panel-interpretation', 'supplement-timing', 'clinical-trials-search'],
    airgapScope: ['health_data', 'biomarkers', 'whoop_oura'],
    deniedPermissions: ['estate_financial_root', 'git'],
    memoryNamespace: 'health-biomarkers',
    uiTone: 'scientific-precise',
    customInstructions: 'Flag if founder HRV dips below 35ms or deep sleep stays under 50 minutes for 3 consecutive nights.'
  },
  {
    id: 'persona-tax-legal-counsel',
    name: 'Corporate & Estate Legal Sentinel',
    category: 'specialist-pro',
    tagline: 'Contract Diffing · Delaware C-Corp · IP Assignment Check',
    targetUserOrRelationship: 'Corporate Estate & Legal Governance',
    systemPromptLaw: 'Analyze contracts for non-compete clauses, IP assignment validity, and Delaware corporate compliance. Highlight unusual indemnity terms in red.',
    voiceId: 'voice-executive-sovereign',
    cadenceRate: 1.0,
    pitch: 0.95,
    activeSkills: ['contract-diffing', 'cap-table-modeling', 'ip-assignment-audit', 'compliance-sentinel'],
    airgapScope: ['legal_docs', 'contracts', 'cap_table'],
    deniedPermissions: ['code_execution', 'terminal_shell'],
    memoryNamespace: 'legal-corporate',
    uiTone: 'executive-dense',
    customInstructions: 'Verify that all contractor agreements assign 100% of created intellectual property to the founder holding entity.'
  }
];

export const INITIAL_PEOPLE_GRAPH: PersonEntity[] = [
  {
    id: 'person-beatrice',
    fullName: 'Sister Beatrice (Agnes)',
    relationshipToFounder: 'Maternal Aunt (Elder Nun, Order of St. Clare)',
    preferredName: 'Aunt Bea',
    contactChannel: 'whatsapp',
    assignedPersonaId: 'persona-elder-sister-beatrice',
    trustTier: 'family-care-restricted',
    importantFacts: [
      'Lives in St. Clare convent garden cottage',
      'Loves morning Gregorian chants and garden chimes',
      'Never ask her for passwords or expose technical menus'
    ],
    healthDietaryNotes: [
      'Glaucoma: Timolol Eye Drops scheduled 08:00 AM daily',
      'Mild hypertension: 1 tablet daily with warm tea'
    ],
    keyDates: [
      { title: 'Feast of St. Clare', date: 'August 11' },
      { title: 'Birthday', date: 'March 24' }
    ],
    lastInteraction: '12 mins ago (WhatsApp voice note)',
    memoryCount: 142
  },
  {
    id: 'person-david-cto',
    fullName: 'David Sterling',
    relationshipToFounder: 'Co-Founder & CTO',
    preferredName: 'David',
    contactChannel: 'telegram',
    assignedPersonaId: 'persona-lead-architect',
    trustTier: 'full-root-sovereign',
    importantFacts: [
      'Co-leads estate software architecture',
      'Has root access to GitHub organization and AWS prod'
    ],
    lastInteraction: '45 mins ago (Peer bus PR review)',
    memoryCount: 384
  },
  {
    id: 'person-amina-sister',
    fullName: 'Dr. Amina Vance',
    relationshipToFounder: 'Sister (Chief of Pediatric Cardiology)',
    preferredName: 'Amina',
    contactChannel: 'imessage',
    assignedPersonaId: 'persona-biomedical-advisor',
    trustTier: 'family-care-restricted',
    importantFacts: [
      'Physician in Boston; on-call Tuesday and Thursday nights',
      'Advised low-sodium regimen for Aunt Bea'
    ],
    keyDates: [
      { title: 'Birthday', date: 'November 18' }
    ],
    lastInteraction: 'Yesterday (iMessage check-in)',
    memoryCount: 89
  },
  {
    id: 'person-leo-son',
    fullName: 'Leo Vance',
    relationshipToFounder: 'Son (Age 8)',
    preferredName: 'Leo',
    contactChannel: 'voice-call',
    assignedPersonaId: 'persona-curious-child-leo',
    trustTier: 'family-care-restricted',
    importantFacts: [
      'Loves space exploration, Ankylosaurus, and Lego technic sets',
      'Grade 3 elementary school'
    ],
    healthDietaryNotes: [
      'Mild peanut allergy (strictly peanut-free snacks)'
    ],
    keyDates: [
      { title: 'Birthday', date: 'June 14' }
    ],
    lastInteraction: '2 hours ago (Homework science story)',
    memoryCount: 112
  },
  {
    id: 'person-marcus-investor',
    fullName: 'Dr. Marcus Chen',
    relationshipToFounder: 'Lead Series A Partner (Benchmark)',
    preferredName: 'Marcus',
    contactChannel: 'telegram',
    assignedPersonaId: 'persona-founder-sovereign',
    trustTier: 'specialist-scoped',
    importantFacts: [
      'Leads Series A syndicate; values outcome-first updates',
      'Met in San Francisco; prefers concise metrics and zero fluff'
    ],
    lastInteraction: '3 days ago (Monthly shareholder memo)',
    memoryCount: 56
  }
];

export const ADVANCED_MEMORY_NODES: AdvancedMemoryNode[] = [
  // 1. Working Context Layer
  {
    id: 'mem-000',
    personId: 'person-david-cto',
    layer: 'working',
    subject: 'Active Terminal Context',
    predicate: 'executing_branch_verification',
    objectValue: 'Branch propose/otto-universal-v1 awaiting signed merge proof',
    permanence: 'decaying-ephemeral',
    confidenceScore: 1.0,
    decayHalfLifeDays: 0.1,
    sourceSession: 'active-turn-working-context',
    timestamp: '2026-11-06T20:00:00Z',
    verifiedBy: 'Otto Core'
  },
  // 2. Core Permanent Identity & Semantic Graph
  {
    id: 'mem-001',
    personId: 'person-beatrice',
    layer: 'semantic-graph',
    subject: 'Sister Beatrice',
    predicate: 'requires_morning_medication',
    objectValue: 'Timolol Eye Drops (1 drop each eye at 08:00 AM)',
    permanence: 'permanent-core',
    confidenceScore: 0.99,
    decayHalfLifeDays: 9999,
    sourceSession: 'kin-onboarding-session',
    timestamp: '2026-11-06T08:00:00Z',
    verifiedBy: 'Dr. Amina Vance'
  },
  {
    id: 'mem-002',
    personId: 'person-leo-son',
    layer: 'semantic-graph',
    subject: 'Leo Vance',
    predicate: 'medical_allergy_warning',
    objectValue: 'Severe Peanut Allergy (Keep EpiPen on trips)',
    permanence: 'permanent-core',
    confidenceScore: 1.0,
    decayHalfLifeDays: 9999,
    sourceSession: 'founder-health-input',
    timestamp: '2026-11-06T09:15:00Z',
    verifiedBy: 'Founder'
  },
  {
    id: 'mem-003',
    personId: 'person-beatrice',
    layer: 'episodic',
    subject: 'Sister Beatrice',
    predicate: 'expressed_garden_update',
    objectValue: 'Noticed her garden tomatoes are ripening warm in the sun',
    permanence: 'decaying-ephemeral',
    confidenceScore: 0.95,
    decayHalfLifeDays: 14,
    sourceSession: 'whatsapp-voice-note-turn-14',
    timestamp: '2026-11-06T11:15:00Z',
    verifiedBy: 'Otto Local Whisper STT'
  },
  {
    id: 'mem-004',
    personId: 'person-marcus-investor',
    layer: 'semantic-graph',
    subject: 'Dr. Marcus Chen',
    predicate: 'preferred_reporting_cadence',
    objectValue: 'Monthly 3-line Telegram digest on 1st of month',
    permanence: 'permanent-core',
    confidenceScore: 0.98,
    decayHalfLifeDays: 365,
    sourceSession: 'telegram-investor-meeting',
    timestamp: '2026-11-04T16:00:00Z',
    verifiedBy: 'Founder'
  },
  {
    id: 'mem-005',
    layer: 'procedural-skill',
    subject: 'UR5e Robot Arm',
    predicate: 'hardware_reset_sequence',
    objectValue: 'Toggle Switch 4 ➔ DFU USB reset pulse (3.4s duration)',
    permanence: 'procedural-rule',
    confidenceScore: 1.0,
    decayHalfLifeDays: 9999,
    sourceSession: 'ros2-hardware-bench-01',
    timestamp: '2026-11-05T14:20:00Z',
    verifiedBy: 'David Sterling'
  }
];

export const ON_DEMAND_RSI_SKILLS = [
  {
    id: 'rsi-skill-satellite-imagery',
    name: 'Satellite Synthetic Aperture Radar (SAR) Analysis',
    domain: 'Geospatial & Defense Intelligence',
    status: 'synthesized-ready',
    hoareProofHash: 'sha256:01928471928471928374',
    utilityDelta: '+18.4% Spatial Accuracy',
    description: 'Auto-acquired by Otto during agricultural zoning check. Extracts crop hydration indices from Sentinel-1 SAR.'
  },
  {
    id: 'rsi-skill-pediatric-care',
    name: 'Pediatric Fever & Dosage Protocol Solver',
    domain: 'Clinical Family Medicine',
    status: 'synthesized-ready',
    hoareProofHash: 'sha256:bb881290348719283746',
    utilityDelta: '+24.1% Dosage Safety',
    description: 'Auto-acquired by Otto to calibrate child paracetamol/ibuprofen weight-based intervals for Leo.'
  },
  {
    id: 'rsi-skill-arbitrage-hedging',
    name: 'Real-Time FX Cross-Currency Liquidity Router',
    domain: 'Quantitative Finance & Treasury',
    status: 'synthesized-ready',
    hoareProofHash: 'sha256:cc991823746192837461',
    utilityDelta: '+3.2% Slippage Minimization',
    description: 'Auto-acquired by Otto during international payroll execution across USD/EUR/SGD.'
  }
];

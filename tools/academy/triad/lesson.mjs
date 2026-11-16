// TRIAD/0: executable, intentionally research-only. No credentials, no telemetry.
// Canonical contract and source notes: docs/training/2026-11-16-triad-mathematical-analogical-transfer.md
export const LESSON_ID = 'triad.conditional-reconstruction.v0';

const lesson = {
  id: LESSON_ID,
  status: 'RESEARCH_ONLY_NOT_CERTIFIED',
  target: {
    title: 'Can a small seed continuously regenerate an entire system?',
    rule: 'A system can reconstruct its evolving state only when it has a trustworthy starting state, the versioned transition rules, the complete ordered change history, and all required external inputs and authority.',
    model: 'S(t) = Replay(K, S(t0), E(t0,t], D(t))',
    assumptions: [
      'Transitions are deterministic, or all nondeterministic choices have been captured.',
      'The checkpoint, events, schemas and external inputs are authentic and complete.',
      'The runtime has required keys, permissions and executable dependencies.',
      'An independent observer compares the reconstructed effect with trusted reality.',
    ],
    boundary: 'No finite magical seed guarantees reconstruction of arbitrary missing information, revoked authority, uncaptured randomness or lost external state.',
  },
  analogies: [
    {
      domain: 'Garden',
      statement: 'The seed holds generative instructions, but soil, water, climate and the starting condition still matter.',
      correspondences: [
        ['genetic instructions', 'versioned transition rules'],
        ['initial seed state', 'trusted checkpoint'],
        ['growth history and weather', 'ordered events and external inputs'],
      ],
      breaksAt: 'A biological seed cannot replay the exact history of its own mature tree bit-for-bit.',
    },
    {
      domain: 'Orchestra',
      statement: 'A score can guide future performance, but it is not a recording of every past performance.',
      correspondences: [
        ['score', 'versioned transition rules'],
        ['starting bar', 'trusted checkpoint'],
        ['performed notes and conductor cues', 'ordered events and external inputs'],
      ],
      breaksAt: 'Musicians interpret the score; exact historical reconstruction needs the recorded performance and its conditions.',
    },
  ],
  sharedCore: 'Rules + checkpoint + ordered history + external inputs + authority + independent comparison. The analogy does not remove missing-information limits.',
};

const assessment = [
  {
    id: 't1',
    skill: 'irrecoverable dependency',
    prompt: 'A city transit archive has a signed checkpoint, all ordered transaction events and correct software, but an encryption key for historical rider records is missing. What can be guaranteed?',
    options: {
      A: 'Exact reconstruction: the checkpoint can derive any missing key.',
      B: 'Not exact reconstruction of encrypted details without an authorised recovered key or equivalent trusted plaintext.',
      C: 'Exact reconstruction if two analogies agree.',
      D: 'Exact reconstruction if the dashboard shows VERIFIED.',
    },
  },
  {
    id: 't2',
    skill: 'hidden external nondeterminism',
    prompt: 'A billing system replays every invoice event, but it originally called a changing exchange-rate API and never recorded the historical responses. What is the correct conclusion?',
    options: {
      A: 'Replaying the same events always reproduces the historical totals.',
      B: 'The system needs a larger event database, regardless of external inputs.',
      C: 'Exact replay is not guaranteed; recover or record the original rate inputs and their versions.',
      D: 'The last snapshot proves every prior external choice.',
    },
  },
  {
    id: 't3',
    skill: 'causal continuity',
    prompt: 'An isolated fleet replica successfully restores state, then accepts new updates while the source fleet keeps changing. Can it rejoin automatically as though no divergence occurred?',
    options: {
      A: 'Yes: a green local test guarantees causal continuity.',
      B: 'Yes: both replicas originated from the same checkpoint.',
      C: 'Yes: the smaller replica always inherits the larger system\'s authority.',
      D: 'Not without detecting divergence, reconciling authorised changes and independently verifying the resulting state and side effects.',
    },
  },
];

function detached(value) { return JSON.parse(JSON.stringify(value)); }
export function getLesson() { return detached(lesson); }
export function getAssessment() { return detached({ lessonId: LESSON_ID, items: assessment, grading: 'objective key withheld until answers submitted' }); }

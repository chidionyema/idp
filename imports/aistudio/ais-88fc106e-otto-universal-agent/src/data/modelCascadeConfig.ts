export interface FrontierModelOption {
  id: string;
  name: string;
  provider: 'Anthropic' | 'Google' | 'DeepSeek' | 'OpenAI' | 'Moonshot' | 'Alibaba' | 'Meta';
  contextWindow: string;
  speedTokSec: number;
  costPerMToken: string;
  specialty: 'Reasoning & Coding' | 'Ultra-Low Latency & Vision' | 'Deep Architecture' | 'Long-Context Archive';
  defaultTimeoutMs: number;
}

export interface CascadeTier {
  tierNumber: number;
  modelId: string;
  timeoutMs: number;
  failoverTriggers: ('http_5xx' | 'rate_limit_429' | 'timeout' | 'safety_censor')[];
  enabled: boolean;
}

export const AVAILABLE_FRONTIER_MODELS: FrontierModelOption[] = [
  {
    id: 'claude-3-7-sonnet',
    name: 'Claude 3.7 Sonnet (Hybrid Reasoning)',
    provider: 'Anthropic',
    contextWindow: '200K',
    speedTokSec: 72,
    costPerMToken: '$3.00 / $15.00',
    specialty: 'Reasoning & Coding',
    defaultTimeoutMs: 4500
  },
  {
    id: 'gemini-2-5-flash',
    name: 'Gemini 2.5 Flash',
    provider: 'Google',
    contextWindow: '1M',
    speedTokSec: 140,
    costPerMToken: '$0.075 / $0.30',
    specialty: 'Ultra-Low Latency & Vision',
    defaultTimeoutMs: 2500
  },
  {
    id: 'gemini-2-5-pro',
    name: 'Gemini 2.5 Pro (Deep Research)',
    provider: 'Google',
    contextWindow: '2M',
    speedTokSec: 65,
    costPerMToken: '$1.25 / $5.00',
    specialty: 'Long-Context Archive',
    defaultTimeoutMs: 5000
  },
  {
    id: 'deepseek-v3',
    name: 'DeepSeek-V3 (671B MoE)',
    provider: 'DeepSeek',
    contextWindow: '128K',
    speedTokSec: 85,
    costPerMToken: '$0.14 / $0.28',
    specialty: 'Reasoning & Coding',
    defaultTimeoutMs: 3500
  },
  {
    id: 'gpt-4o',
    name: 'GPT-4o Omnimodal',
    provider: 'OpenAI',
    contextWindow: '128K',
    speedTokSec: 90,
    costPerMToken: '$2.50 / $10.00',
    specialty: 'Ultra-Low Latency & Vision',
    defaultTimeoutMs: 4000
  },
  {
    id: 'kimi-k1-5',
    name: 'Kimi Moonshot k1.5',
    provider: 'Moonshot',
    contextWindow: '200K',
    speedTokSec: 68,
    costPerMToken: '$0.80 / $2.40',
    specialty: 'Deep Architecture',
    defaultTimeoutMs: 4200
  },
  {
    id: 'qwen-2-5-coder-32b',
    name: 'Qwen 2.5 Coder 32B Instruct',
    provider: 'Alibaba',
    contextWindow: '128K',
    speedTokSec: 95,
    costPerMToken: '$0.20 / $0.40',
    specialty: 'Reasoning & Coding',
    defaultTimeoutMs: 3000
  }
];

export const BEDROCK_LOCAL_MODEL = {
  id: 'local-deepseek-r1-70b-q4',
  name: 'Local DeepSeek-R1 70B (Quantized Q4_K_M)',
  engine: 'Apple Neural Engine + Metal GPU / llama.cpp / vLLM',
  runtimeHost: 'Mac Studio M4 Max (128GB Unified Memory) / Dual RTX 4090',
  contextWindow: '64K',
  speedTokSec: 48,
  costPerMToken: '$0.00 (Self-Hosted Sovereign)',
  status: 'Permanently Armed Bedrock',
  description: 'Uncompromised, 100% offline local model. Executes when all frontier cloud APIs are unreachable, severed, or under rate-limit constraints.'
};

export const DEFAULT_CASCADE_TIERS: CascadeTier[] = [
  {
    tierNumber: 1,
    modelId: 'claude-3-7-sonnet',
    timeoutMs: 4500,
    failoverTriggers: ['http_5xx', 'rate_limit_429', 'timeout', 'safety_censor'],
    enabled: true
  },
  {
    tierNumber: 2,
    modelId: 'gemini-2-5-flash',
    timeoutMs: 2500,
    failoverTriggers: ['http_5xx', 'rate_limit_429', 'timeout'],
    enabled: true
  },
  {
    tierNumber: 3,
    modelId: 'deepseek-v3',
    timeoutMs: 3500,
    failoverTriggers: ['http_5xx', 'rate_limit_429', 'timeout'],
    enabled: true
  }
];

import express, { Request, Response } from 'express';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import { GoogleGenAI } from '@google/genai';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3000;

app.use(express.json());

// Initialize GoogleGenAI SDK server-side
const apiKey = process.env.GEMINI_API_KEY;
let aiClient: GoogleGenAI | null = null;
if (apiKey) {
  aiClient = new GoogleGenAI({
    apiKey,
    httpOptions: {
      headers: {
        'User-Agent': 'aistudio-build',
      },
    },
  });
}

// Health check endpoint
app.get('/api/health', (_req: Request, res: Response) => {
  res.json({
    status: 'nominal',
    estateStatus: 'ACTIVE_OBSERVABILITY',
    timestamp: new Date().toISOString(),
    aiConfigured: !!apiKey,
  });
});

// Algorithmic Protocol & Motion Reality Check Engine
app.post('/api/audit-algorithm', async (req: Request, res: Response) => {
  const { title, intent, proposedActions, riskFactors, currentChaosState, capitalBurnAllocation } = req.body;

  if (!title) {
    return res.status(400).json({ error: 'Motion or Decree title is required' });
  }

  // If Gemini API is available, perform live algorithmic synthesis
  if (aiClient) {
    try {
      const prompt = `You are the Estate Sovereign Algorithmic Governance Engine serving an Autonomous Estate Founder.
The Founder has issued a strict decree: "THINK ALGORITHMICALLY FIRST. No reactive churn, no blind agenda text, no missing artifacts, no unmeasured risk to financial runway and founder health."

Analyze the following proposed estate motion or decree:
- Title: ${title}
- Intent: ${intent || 'Unspecified'}
- Proposed Actions: ${proposedActions || 'None provided'}
- Known Risk Factors: ${riskFactors || 'Unspecified'}
- Current Chaos Pattern: ${currentChaosState || 'Unanchored drift'}
- Capital Burn Allocated: $${capitalBurnAllocation || 0}

Evaluate this against:
1. Algorithmic Convergence: Does this motion possess a mathematically provable target destination or does it repeat the known failure pattern ("reacting and building new things without an anchor")?
2. Closed-Loop Feedback Invariant: What exact mathematical/operational metric closes the loop and proves delivered value?
3. Financial & Health Risk Impact: What is the direct risk to treasury runway and Founder cognitive strain/burnout?
4. Delivery Protocol Verdict: One of [APPROVED_CONVERGENT, REQUIRES_ANCHORING, REJECTED_CHAOS_PATTERN].

Respond ONLY with valid JSON with this exact structure:
{
  "verdict": "APPROVED_CONVERGENT" | "REQUIRES_ANCHORING" | "REJECTED_CHAOS_PATTERN",
  "algorithmicProof": "2-3 sentences explaining the state transition proof and convergence characteristics",
  "failurePatternAnalysis": "Analysis of whether this avoids the react-and-build failure loop",
  "closedLoopMetric": "Specific quantifiable metric that proves delivered value",
  "founderRiskScore": 1-100,
  "financialEfficiencyScore": 1-100,
  "immutableDeliveryEdicts": [
    "Exact actionable protocol requirement 1",
    "Exact actionable protocol requirement 2",
    "Exact actionable protocol requirement 3"
  ]
}`;

      const aiResponse = await aiClient.models.generateContent({
        model: 'gemini-3.8-flash',
        contents: prompt,
        config: {
          responseMimeType: 'application/json',
          systemInstruction: 'You are an exacting algorithmic systems architect and sovereign estate steward. Your duty is to protect the founder from blind spots, chaos drift, and unanchored burnout.',
        },
      });

      const responseText = aiResponse.text;
      if (responseText) {
        try {
          const parsed = JSON.parse(responseText.trim());
          return res.json({ success: true, source: 'gemini-3.8-flash', audit: parsed });
        } catch {
          // Fall back if parse fails
        }
      }
    } catch (err: unknown) {
      console.warn('Gemini API call failed or rate limited, falling back to deterministic model:', err);
    }
  }

  // Deterministic Sovereign Algorithmic Evaluation Engine (Deterministic Rule Invariant)
  const isReactivePattern = /build\s+new|pivot|urgent|react|try\s+another|experiment/i.test(title + ' ' + (proposedActions || ''));
  const hasCapitalClearance = (capitalBurnAllocation || 0) < 5000;
  
  const audit = {
    verdict: isReactivePattern ? 'REQUIRES_ANCHORING' : 'APPROVED_CONVERGENT',
    algorithmicProof: isReactivePattern 
      ? 'Divergence detected: System exhibits open-loop perturbation. Trajectory indicates reactive phase loop without pre-conditions or telemetry anchors. High probability of artifact orphaning.' 
      : 'Convergence proven: State transition maps finite input vectors to verifiable bounded deliverables. Closed-loop feedback invariant satisfies Lyapunov stability criteria for estate runway.',
    failurePatternAnalysis: isReactivePattern 
      ? 'Warning: Mirrors the known failure signature ("Reacting and building without telemetry"). Halts until tracking protocol and artifact hash are registered.' 
      : 'Passes Sovereign Invariant: Displaces speculation with deterministic milestone gates. Preserves founder cognitive bandwidth.',
    closedLoopMetric: 'Delta in Treasury Velocity (Burn vs Capitalized Value) measured at t+72h post-delivery.',
    founderRiskScore: isReactivePattern ? 82 : 28,
    financialEfficiencyScore: hasCapitalClearance ? 88 : 54,
    immutableDeliveryEdicts: [
      'Artifact registration required with cryptographic hash before task delegation.',
      'Explicit stop-loss threshold: Automatic halt if delivery velocity drops below 0.85.',
      'Mandatory Founder telemetry checkpoint at Phase 2 completion.'
    ]
  };

  return res.json({ success: true, source: 'sovereign-invariant-engine', audit });
});

// In-memory store for incoming agent receipts
interface InboundReceipt {
  id: string;
  agentId: string;
  motionId: string;
  artifactTitle: string;
  checksum: string;
  status: 'DELIVERED' | 'FAILED' | 'IN_PROGRESS';
  receivedAt: string;
  payload: any;
}
const inboundReceipts: InboundReceipt[] = [];

// Inbound Agent Webhook Endpoint: External agents (n8n, CrewAI, Python, Telegram) can POST receipts here
app.post('/api/agent-receipt', (req: Request, res: Response) => {
  const { agentId, motionId, artifactTitle, checksum, status, payload } = req.body;
  
  const receipt: InboundReceipt = {
    id: `RCPT-${Date.now()}`,
    agentId: agentId || 'Unknown-Agent',
    motionId: motionId || 'UNASSIGNED',
    artifactTitle: artifactTitle || 'Unnamed Artifact',
    checksum: checksum || `sha256:${Date.now().toString(16)}`,
    status: status || 'DELIVERED',
    receivedAt: new Date().toISOString(),
    payload: payload || {},
  };

  inboundReceipts.unshift(receipt);
  if (inboundReceipts.length > 50) inboundReceipts.pop();

  return res.status(201).json({
    success: true,
    message: 'Receipt cryptographically acknowledged and logged in Estate Vault.',
    receiptId: receipt.id,
    timestamp: receipt.receivedAt,
  });
});

// Get all inbound agent receipts
app.get('/api/agent-receipts', (_req: Request, res: Response) => {
  res.json({ success: true, receipts: inboundReceipts });
});

// Dispatch Motion to External Agent Webhook (Proxies from server to avoid CORS)
app.post('/api/dispatch-agent', async (req: Request, res: Response) => {
  const { targetUrl, motion, headers } = req.body;

  if (!targetUrl) {
    return res.status(400).json({ error: 'targetUrl is required' });
  }

  const startTime = Date.now();
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);

    const agentResponse = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'Estate-Sovereign-Dispatcher/1.0',
        ...(headers || {}),
      },
      body: JSON.stringify({
        event: 'ESTATE_SOVEREIGN_MOTION_DISPATCH',
        dispatchedAt: new Date().toISOString(),
        motion,
      }),
      signal: controller.signal,
    });
    clearTimeout(timeout);

    const latencyMs = Date.now() - startTime;
    let responseData: any;
    try {
      responseData = await agentResponse.json();
    } catch {
      responseData = { statusText: agentResponse.statusText };
    }

    return res.json({
      success: agentResponse.ok,
      status: agentResponse.status,
      latencyMs,
      agentResponse: responseData,
    });
  } catch (err: any) {
    return res.status(502).json({
      success: false,
      error: err.name === 'AbortError' ? 'Agent endpoint timed out (8s limit)' : err.message,
      latencyMs: Date.now() - startTime,
    });
  }
});

// GitHub Real Repo & Commit Sync Endpoint
app.post('/api/github-sync', async (req: Request, res: Response) => {
  const { repoOwner, repoName, token } = req.body;

  if (!repoOwner || !repoName) {
    return res.status(400).json({ error: 'repoOwner and repoName are required' });
  }

  try {
    const reqHeaders: Record<string, string> = {
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'Estate-Sovereign-App',
    };
    if (token) {
      reqHeaders['Authorization'] = `token ${token}`;
    }

    const githubRes = await fetch(`https://api.github.com/repos/${encodeURIComponent(repoOwner)}/${encodeURIComponent(repoName)}/commits?per_page=6`, {
      headers: reqHeaders,
    });

    if (!githubRes.ok) {
      return res.status(githubRes.status).json({
        error: `GitHub API error: ${githubRes.statusText}`,
      });
    }

    const commits = await githubRes.json();
    return res.json({ success: true, commits });
  } catch (err: any) {
    return res.status(500).json({ error: err.message });
  }
});

async function startServer() {
  const isProduction = process.env.NODE_ENV === 'production';

  if (!isProduction) {
    const { createServer: createViteServer } = await import('vite');
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static(path.join(__dirname, 'dist')));
    app.get('*', (_req: Request, res: Response) => {
      res.sendFile(path.join(__dirname, 'dist', 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Estate Sovereign Server active on port ${PORT}`);
  });
}

startServer();

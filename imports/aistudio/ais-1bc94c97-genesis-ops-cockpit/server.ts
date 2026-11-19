import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';
import { GoogleGenAI } from '@google/genai';
import { extractSessionBrief, parseJsonlLogs } from './src/utils/extractiveCore.js';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = Number(process.env.PORT) || 3000;

app.use(express.json({ limit: '10mb' }));

// Initialize Gemini client if API key is present
const apiKey = process.env.GEMINI_API_KEY;
let aiClient: GoogleGenAI | null = null;
if (apiKey && apiKey !== 'MY_GEMINI_API_KEY') {
  try {
    aiClient = new GoogleGenAI({ apiKey });
  } catch (err) {
    console.warn('Gemini client init skipped:', err);
  }
}

/**
 * Health & Telemetry endpoint
 */
app.get('/api/telemetry', (_req, res) => {
  res.json({
    geminiConfigured: !!aiClient,
    modelTarget: 'gemini-2.5-flash',
    costPerBriefEstUsd: 0.00011,
    estateComputeCostUsd: 0.0,
    dofGateStatus: 'LOCKED_AWAITING_CREDENTIAL',
    piperArmVm: {
      cores: 4,
      status: 'PR_READY_QUEUED',
      voice: 'en_US-ryan-medium',
      latencyEstMs: 420,
    },
    spooler: {
      activeChannels: ['genesis-ops-cockpit', 'telegram-genesis-host-spooler'],
      persistedCount: 18,
    },
  });
});

/**
 * Condense & Enrich Endpoint:
 * Accepts raw JSONL or pre-parsed session logs, with toggle for Gemini enrichment.
 */
app.post('/api/enrich', async (req, res) => {
  try {
    const { legionName = 'Legion Alpha', jsonlText, enableGeminiEnrichment = false, rawLogs } = req.body;

    // Step 1: $0 Extractive Core heuristic pass
    const logs = rawLogs || (jsonlText ? parseJsonlLogs(jsonlText) : []);
    const baseBrief = extractSessionBrief(legionName, logs);

    // If Gemini enrichment is NOT enabled or no API key, return the $0 baseline immediately
    if (!enableGeminiEnrichment || !aiClient) {
      return res.json({
        ...baseBrief,
        enrichedWithGemini: false,
        modelUsed: 'estate-dream-cycle-extractive-v2 ($0.00)',
        tokenStats: {
          inputTokens: 0,
          outputTokens: 0,
          estimatedCostUsd: 0.0,
        },
      });
    }

    // Step 2: Gemini 2.5 Flash Spoken Cadence Enrichment
    const prompt = `You are the executive briefing voice agent for ${legionName} in the Genesis Autonomous Ops Cockpit.
Transform the following extracted technical session milestones into a crisp, spoken 60-to-80-second founder briefing script.

Format Requirements:
- Keep spoken pacing natural and confident for audio delivery (approx 140-160 words total).
- Structure clearly into:
  1. "What shipped": 1-2 sentences summarizing key merged features, PRs, or accomplishments.
  2. "What's blocked": 1-2 sentences on external dependencies or gate locks (e.g. DOF-gate credentials).
  3. "Needs founder": 1-2 direct sentences stating the exact decision, credential rotation, or PR merge sign-off required from the founder.
- Conclude with "Receipt confirmed and verified."
- Do NOT include markdown headers, emojis, asterisks, or timestamps in the spoken text.

Extracted Data:
- Shipped: ${JSON.stringify(baseBrief.whatShipped)}
- Blocked: ${JSON.stringify(baseBrief.whatIsBlocked)}
- Founder Actions: ${JSON.stringify(baseBrief.needsFounder)}`;

    const response = await aiClient.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: prompt,
      config: {
        temperature: 0.3,
        maxOutputTokens: 350,
      },
    });

    const enrichedText = response.text?.trim() || baseBrief.spokenScript;
    const words = enrichedText.split(/\s+/).filter(Boolean);
    const wordCount = words.length;
    const estimatedDurationSec = Math.max(30, Math.round((wordCount / 140) * 60));

    // Recalculate karaoke timestamps for the enriched script
    const sentences = enrichedText.match(/[^.!?]+[.!?]+/g) || [enrichedText];
    let timeAccumulator = 0;
    const timeSlice = estimatedDurationSec / Math.max(1, sentences.length);
    const karaokeLines = sentences.map((s, idx) => {
      const startTime = Math.round(timeAccumulator * 10) / 10;
      timeAccumulator += timeSlice;
      const endTime = Math.round(timeAccumulator * 10) / 10;
      return {
        id: `enriched-line-${idx}`,
        startTime,
        endTime,
        text: s.trim(),
      };
    });

    // Token accounting: input ~500 tokens, output ~200 tokens
    const estInputTokens = 520;
    const estOutputTokens = wordCount * 1.3;
    const costUsd = (estInputTokens * 0.000000075) + (estOutputTokens * 0.0000003);

    return res.json({
      ...baseBrief,
      spokenScript: enrichedText,
      karaokeLines,
      wordCount,
      estimatedDurationSec,
      enrichedWithGemini: true,
      modelUsed: 'gemini-2.5-flash',
      tokenStats: {
        inputTokens: estInputTokens,
        outputTokens: Math.round(estOutputTokens),
        estimatedCostUsd: Number(costUsd.toFixed(6)),
      },
    });
  } catch (error: any) {
    console.error('Gemini enrichment error:', error);
    // Graceful fallback to pure $0 baseline on any API issue
    const logs = req.body.rawLogs || (req.body.jsonlText ? parseJsonlLogs(req.body.jsonlText) : []);
    const fallbackBrief = extractSessionBrief(req.body.legionName || 'Legion Alpha', logs);
    return res.json({
      ...fallbackBrief,
      enrichedWithGemini: false,
      fallbackNotice: 'Fell back to $0 estate extractive core: ' + (error.message || 'API unavailable'),
      modelUsed: 'estate-dream-cycle-extractive-v2 ($0.00)',
      tokenStats: {
        inputTokens: 0,
        outputTokens: 0,
        estimatedCostUsd: 0.0,
      },
    });
  }
});

// Mount Vite in development or serve static in production
async function startServer() {
  if (process.env.NODE_ENV !== 'production') {
    const { createServer: createViteServer } = await import('vite');
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static(path.resolve(__dirname, 'dist')));
    app.get('*', (_req, res) => {
      res.sendFile(path.resolve(__dirname, 'dist', 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Genesis Ops Cockpit server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();

/**
 * SmolLM2 Intent Compiler
 *
 * Parses transcribed text into structured intents using SmolLM2.
 * Runs entirely client-side via Transformers.js.
 */

import { pipeline, env } from '@xenova/transformers';
import type { Intent, IntentCategory, ModelProgress } from './types';

// Disable local model loading attempts
env.allowLocalModels = false;

/** Intent model configuration */
const MODEL_ID = 'HuggingFaceTB/SmolLM2-135M-Instruct';

/** Intent classification prompt template */
const INTENT_PROMPT = `You are an intent classifier for a voice-controlled application. Parse the user's speech into a structured intent.

Categories:
- navigation: Moving between screens/pages (go to, open, show, navigate)
- action: Performing an operation (create, delete, update, send, deploy)
- query: Asking for information (what is, how many, show me, list)
- control: Voice control commands (stop, cancel, pause, repeat)
- system: System commands (settings, help, logout)
- unknown: Cannot determine intent

User said: "{transcript}"

Respond with JSON only:
{{"category": "<category>", "action": "<specific_action>", "entities": {{}}, "confidence": <0-1>}}`;

/**
 * Intent processor using SmolLM2
 */
export class IntentProcessor {
  private generator: Awaited<ReturnType<typeof pipeline>> | null = null;

  /**
   * Initialize the intent model
   */
  async init(onProgress?: (progress: ModelProgress) => void): Promise<void> {
    this.generator = await pipeline('text-generation', MODEL_ID, {
      progress_callback: (data: { status: string; progress?: number; loaded?: number; total?: number }) => {
        if (data.status === 'progress' && onProgress && data.progress !== undefined) {
          onProgress({
            model: 'intent',
            progress: data.progress / 100,
            loaded: data.loaded || 0,
            total: data.total || 0,
          });
        }
      },
    });
  }

  /**
   * Parse transcript into intent
   */
  async parse(transcript: string): Promise<Intent> {
    if (!this.generator) {
      throw new Error('Intent processor not initialized');
    }

    const prompt = INTENT_PROMPT.replace('{transcript}', transcript);

    try {
      const result = await this.generator(prompt, {
        max_new_tokens: 100,
        temperature: 0.1,
        do_sample: false,
      });

      // Extract JSON from response
      const responseText = Array.isArray(result)
        ? result[0]?.generated_text || ''
        : (result as { generated_text: string }).generated_text;

      // Find JSON in response
      const jsonMatch = responseText.match(/\{[^}]+\}/);
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0]);

        return {
          transcript,
          category: this.validateCategory(parsed.category),
          action: parsed.action || 'unknown',
          entities: parsed.entities || {},
          confidence: Math.min(1, Math.max(0, parsed.confidence || 0.5)),
          timestamp: Date.now(),
        };
      }
    } catch (error) {
      console.warn('Intent parsing failed, using fallback:', error);
    }

    // Fallback: use simple keyword matching
    return this.fallbackParse(transcript);
  }

  /**
   * Validate category string
   */
  private validateCategory(category: string): IntentCategory {
    const valid: IntentCategory[] = [
      'navigation', 'action', 'query', 'control', 'system', 'unknown'
    ];

    const normalized = category?.toLowerCase();
    return valid.includes(normalized as IntentCategory)
      ? normalized as IntentCategory
      : 'unknown';
  }

  /**
   * Fallback parsing using keyword matching
   */
  private fallbackParse(transcript: string): Intent {
    const lower = transcript.toLowerCase();

    let category: IntentCategory = 'unknown';
    let action = 'unknown';
    let confidence = 0.5;

    // Navigation keywords
    if (/\b(go to|navigate|open|show|display)\b/.test(lower)) {
      category = 'navigation';
      action = lower.match(/\b(go to|navigate|open|show|display)\b/)?.[0] || 'navigate';
      confidence = 0.7;
    }
    // Action keywords
    else if (/\b(create|delete|remove|update|send|deploy|start|stop|run)\b/.test(lower)) {
      category = 'action';
      action = lower.match(/\b(create|delete|remove|update|send|deploy|start|stop|run)\b/)?.[0] || 'action';
      confidence = 0.7;
    }
    // Query keywords
    else if (/\b(what|how|where|when|why|list|find|search|show me)\b/.test(lower)) {
      category = 'query';
      action = 'query';
      confidence = 0.6;
    }
    // Control keywords
    else if (/\b(stop|cancel|pause|resume|repeat|undo)\b/.test(lower)) {
      category = 'control';
      action = lower.match(/\b(stop|cancel|pause|resume|repeat|undo)\b/)?.[0] || 'control';
      confidence = 0.8;
    }
    // System keywords
    else if (/\b(settings|help|logout|exit|quit)\b/.test(lower)) {
      category = 'system';
      action = lower.match(/\b(settings|help|logout|exit|quit)\b/)?.[0] || 'system';
      confidence = 0.7;
    }

    return {
      transcript,
      category,
      action,
      entities: this.extractEntities(transcript),
      confidence,
      timestamp: Date.now(),
    };
  }

  /**
   * Extract entities from transcript
   */
  private extractEntities(transcript: string): Record<string, string | number> {
    const entities: Record<string, string | number> = {};

    // Extract numbers
    const numbers = transcript.match(/\d+/g);
    if (numbers) {
      entities.count = parseInt(numbers[0], 10);
    }

    // Extract quoted strings
    const quoted = transcript.match(/"([^"]+)"/);
    if (quoted) {
      entities.name = quoted[1];
    }

    // Extract common targets
    const targetMatch = transcript.match(/\b(dashboard|settings|profile|home|logs?|pods?|deployments?|services?)\b/i);
    if (targetMatch) {
      entities.target = targetMatch[1].toLowerCase();
    }

    return entities;
  }

  /**
   * Clean up resources
   */
  async dispose(): Promise<void> {
    this.generator = null;
  }
}

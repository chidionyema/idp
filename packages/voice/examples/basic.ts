/**
 * Basic FleetView Voice SDK Example
 *
 * Run with: npx ts-node examples/basic.ts
 */

import { VoiceClient, Intent, ModelProgress } from '../src';

async function main() {
  console.log('FleetView Voice SDK - Basic Example\n');

  // Create voice client
  const client = new VoiceClient({
    debug: true,

    // Called when an intent is recognized
    onIntent: (intent: Intent) => {
      console.log('\n--- Intent Recognized ---');
      console.log(`Transcript: "${intent.transcript}"`);
      console.log(`Category:   ${intent.category}`);
      console.log(`Action:     ${intent.action}`);
      console.log(`Confidence: ${(intent.confidence * 100).toFixed(1)}%`);
      console.log(`Entities:   ${JSON.stringify(intent.entities)}`);
      console.log('------------------------\n');

      // Handle different intent categories
      switch (intent.category) {
        case 'navigation':
          handleNavigation(intent);
          break;
        case 'action':
          handleAction(intent);
          break;
        case 'query':
          handleQuery(intent);
          break;
        case 'control':
          handleControl(intent, client);
          break;
        case 'system':
          handleSystem(intent, client);
          break;
      }
    },

    // Called when speaking state changes
    onSpeaking: (speaking: boolean) => {
      if (speaking) {
        console.log('🎤 Listening...');
      } else {
        console.log('🔇 Processing...');
      }
    },

    // Called for model download progress
    onModelProgress: (progress: ModelProgress) => {
      const pct = (progress.progress * 100).toFixed(1);
      const mb = (progress.loaded / 1024 / 1024).toFixed(1);
      console.log(`📦 Loading ${progress.model}: ${pct}% (${mb} MB)`);
    },

    // Called on errors
    onError: (error: Error) => {
      console.error('❌ Error:', error.message);
    },
  });

  try {
    // Start the voice client
    console.log('Starting voice client...');
    await client.start();

    // Speak a greeting
    await client.speak('Voice control ready. What would you like to do?');

    console.log('\n🎙️  Say something! Try:');
    console.log('   - "Go to dashboard"');
    console.log('   - "Show me the logs"');
    console.log('   - "Deploy the application"');
    console.log('   - "Stop listening"');
    console.log('\nPress Ctrl+C to exit.\n');

    // Keep running until interrupted
    await new Promise(() => {});

  } catch (error) {
    console.error('Failed to start:', error);
    process.exit(1);
  }
}

// Intent handlers

function handleNavigation(intent: Intent) {
  const target = intent.entities.target || 'unknown';
  console.log(`➡️  Navigating to: ${target}`);
}

function handleAction(intent: Intent) {
  console.log(`⚡ Executing action: ${intent.action}`);
}

function handleQuery(intent: Intent) {
  console.log(`❓ Query: ${intent.transcript}`);
}

async function handleControl(intent: Intent, client: VoiceClient) {
  if (intent.action === 'stop' || intent.action === 'cancel') {
    console.log('🛑 Stopping voice client...');
    await client.stop();
    process.exit(0);
  }
}

async function handleSystem(intent: Intent, client: VoiceClient) {
  if (intent.action === 'exit' || intent.action === 'quit') {
    await client.speak('Goodbye!');
    await client.stop();
    process.exit(0);
  }
}

// Run
main().catch(console.error);

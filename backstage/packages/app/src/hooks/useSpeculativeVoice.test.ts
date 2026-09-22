/**
 * Tests for useSpeculativeVoice hook.
 *
 * These tests verify the hook's behavior without loading actual ML models,
 * which would be too slow for unit tests. Integration tests should cover
 * the full pipeline.
 */
import { renderHook } from '@testing-library/react';
import { useSpeculativeVoice, type VoiceIntent } from './useSpeculativeVoice';

// Mock the dynamic imports
jest.mock('@huggingface/transformers', () => ({
  pipeline: jest.fn(),
  env: {
    allowLocalModels: false,
    useBrowserCache: true,
  },
}));

jest.mock('kokoro-js', () => ({
  KokoroTTS: {
    from_pretrained: jest.fn(),
  },
}));

// Mock window objects
const mockOrt = {
  env: {
    wasm: {
      wasmPaths: '',
    },
  },
};

const mockVad = {
  MicVAD: {
    new: jest.fn().mockResolvedValue({
      start: jest.fn().mockResolvedValue(undefined),
      destroy: jest.fn(),
    }),
  },
};

describe('useSpeculativeVoice', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (window as any).ort = mockOrt;
    (window as any).vad = mockVad;
  });

  afterEach(() => {
    delete (window as any).ort;
    delete (window as any).vad;
  });

  it('initializes in unloaded state', () => {
    const { result } = renderHook(() => useSpeculativeVoice());

    expect(result.current.state).toBe('unloaded');
    expect(result.current.ready).toBe(false);
    expect(result.current.transcript).toBe('');
    expect(result.current.intent).toBeNull();
  });

  it('exposes all required methods', () => {
    const { result } = renderHook(() => useSpeculativeVoice());

    expect(typeof result.current.load).toBe('function');
    expect(typeof result.current.start).toBe('function');
    expect(typeof result.current.stop).toBe('function');
    expect(typeof result.current.speak).toBe('function');
    expect(typeof result.current.silence).toBe('function');
  });

  it('tracks model progress during load', () => {
    const { result } = renderHook(() => useSpeculativeVoice());

    // Progress should be empty initially
    expect(Object.keys(result.current.modelProgress).length).toBe(0);
  });

  it('maintains intent history', () => {
    const { result } = renderHook(() => useSpeculativeVoice());

    expect(result.current.intentHistory).toEqual([]);
  });

  it('returns metrics as null initially', () => {
    const { result } = renderHook(() => useSpeculativeVoice());

    expect(result.current.metrics).toBeNull();
  });
});

describe('VoiceIntent schema', () => {
  it('has the correct shape for a deploy intent', () => {
    const intent: VoiceIntent = {
      action: 'deploy',
      target: 'frontend',
      env: 'prod',
      confidence: 0.95,
      partial: false,
    };

    expect(intent.action).toBe('deploy');
    expect(intent.target).toBe('frontend');
    expect(intent.env).toBe('prod');
    expect(intent.confidence).toBeGreaterThanOrEqual(0);
    expect(intent.confidence).toBeLessThanOrEqual(1);
    expect(intent.partial).toBe(false);
  });

  it('allows optional fields to be omitted', () => {
    const intent: VoiceIntent = {
      action: 'status',
      confidence: 0.8,
      partial: true,
    };

    expect(intent.action).toBe('status');
    expect(intent.target).toBeUndefined();
    expect(intent.env).toBeUndefined();
  });
});

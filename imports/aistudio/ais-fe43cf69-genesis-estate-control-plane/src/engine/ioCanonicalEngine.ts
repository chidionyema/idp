// Re-export the single canonical @meridian-estate/io-engine (PACK-15) implementation
// so UI components, Express server routes, unit tests, and bin/io never fork.
export * from '../../packages/io-engine/index.ts';

// The home refresh heartbeat, in one place. Every hook that polls reads this, so the
// founder's pages breathe together instead of each polling on its own clock.
// Leaf module: importing it must not drag the catalogue or Kubernetes plugins into a
// test's module graph (the micRetry suite mocks only the frontend-plugin-api surface).
export const REFRESH_MS = 60_000;

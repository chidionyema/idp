interface BackstageAnalytics {
  track(event: string, properties?: Record<string, unknown>): void;
}

interface Window {
  __BACKSTAGE_ANALYTICS__?: BackstageAnalytics;
}

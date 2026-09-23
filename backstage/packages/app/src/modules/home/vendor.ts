// CP3 (docs/specs/backstage-as-a-product.md): the vendor surfaces the estate does not own the UI
// of -- Traces (Langfuse), Telemetry (SigNoz), Dashboards (Superset) -- shipped as a card whose
// only fact was a link to the vendor's own login. This module is the pure half of the fix: it
// maps ONE live read of a vendor's own health endpoint into one plain sentence, so a card says
// whether the thing is up without framing the vendor (LAW 21, spec Non-goals).
//
// No host and no key live here (LAW 46): the hook (useVendor.ts) reads through the backend's
// proxy, which names the target in app-config, and this file only turns an answer into words.
// Pure, so the words are graded by a fixture and never by a live vendor.

/** One vendor's in-portal door: the proxy path in app-config, and the name a person reads. */
export type Vendor = {
  /** The proxy endpoint key (app-config proxy.endpoints.<key>). */
  path: string;
  /** Plain English, as the card's own title names it. */
  label: string;
};

/** The three doors CP3 adds. Kept here, not typed in a page, so a test can hold the set. */
export const VENDORS = {
  langfuse: { path: '/langfuse/api/public/health', label: 'Traces' },
  signoz: { path: '/signoz/api/v1/health', label: 'Telemetry' },
  superset: { path: '/superset/health', label: 'Dashboards' },
} as const;

/** Which vendor a founder-surface entity is, from its own metadata name; undefined for the rest.
 * The catalogue names these `founder-traces`, `founder-telemetry`, `founder-dashboards`, so the
 * mapping is one place and a new vendor is one row, not a branch in a component. */
export const vendorOf = (name: string): Vendor | undefined => {
  switch (name) {
    case 'founder-traces':
      return VENDORS.langfuse;
    case 'founder-telemetry':
      return VENDORS.signoz;
    case 'founder-dashboards':
      return VENDORS.superset;
    default:
      return undefined;
  }
};

/** The read, as the hook hands it to the card. `status` is the vendor's HTTP answer when it
 * answered at all; `error` is the wire failure when it did not. */
export type VendorRead =
  | { state: 'loading' }
  | { state: 'answered'; status: number }
  | { state: 'unread'; error: string };

/**
 * One plain sentence (plus a verdict word) for one VendorRead. The rule is the estate's: a
 * vendor that did not answer is never drawn green, and a 200 is "up" only because the vendor's
 * OWN health endpoint said so -- this component does not know the product works, only that the
 * door answered. A non-2xx is "answers, but not healthy" and is not green either.
 */
export const vendorSentence = (
  label: string,
  read: VendorRead,
): { verdict: 'up' | 'degraded' | 'down' | 'reading'; sentence: string } => {
  if (read.state === 'loading') {
    return { verdict: 'reading', sentence: `Reading ${label}…` };
  }
  if (read.state === 'unread') {
    return { verdict: 'down', sentence: `${label} did not answer.` };
  }
  if (read.status >= 200 && read.status < 300) {
    return { verdict: 'up', sentence: `${label} is up.` };
  }
  return {
    verdict: 'degraded',
    sentence: `${label} answered, but not healthy.`,
  };
};

// CP6 (docs/specs/backstage-as-a-product.md): four founder surfaces held no live fact at all --
// they carried only a GitHub link or a vendor login. Each is backed by a real running process,
// so each gets ONE read of its own health endpoint through the backend's proxy, turned into one
// plain sentence: the same move CP3 made for the vendor surfaces and CP4 for the platform layers.
//
// No host and no key live here (LAW 46): the hook (useDoorHealth.ts) reads through the proxy,
// which names the target in app-config, and this file only turns an answer into words. Pure, so
// the words are graded by a fixture and never by a live service.

/** One founder surface's in-portal door: the proxy path in app-config, the name a person reads,
 * and the endpoint that speaks for the process (kept here in the comment so the target is
 * traceable to its manifest, never typed as a URL). */
export type DoorHealth = {
  /** The proxy endpoint key (app-config proxy.endpoints.<key>). */
  path: string;
  /** Plain English, as the card's own title names it. */
  label: string;
  /** Which live thing answers: the process's own health endpoint, named from its manifest. */
  source: string;
};

/** The four doors CP6 adds. Kept here, not typed in a page, so a test can hold the set.
 *  - otto-door: otto-golden Service :8080, GET /healthz (platform/otto-golden/config.yaml).
 *  - mcp-gateway: platform/mcp agentgateway http :3000, GET /healthz (agentgateway-deploy.yaml).
 *  - otto: hermes-agent-gateway Service :9900, GET /.well-known/agent-card.json (gateway.yaml).
 *  - cursor: no in-cluster Service (a vendor harness), so its card is the vendor pattern: the
 *    read is the catalogue fact, and its door names the console rather than a process port. */
export const DOOR_HEALTH = {
  'founder-otto-door': {
    path: '/otto-door/healthz',
    label: 'The Otto door',
    source: 'otto-golden :8080 /healthz',
  },
  'founder-mcp-gateway': {
    path: '/mcp-gateway/healthz',
    label: 'The MCP gateway',
    source: 'mcp agentgateway :3000 /healthz',
  },
  'founder-otto': {
    path: '/otto/agent-card',
    label: 'Otto',
    source: 'hermes-agent-gateway :9900 /.well-known/agent-card.json',
  },
} as const;

/** Which surface a founder-surface entity is, from its own metadata name; undefined for the rest.
 *  `founder-cursor` is deliberately absent: it has no in-cluster health endpoint, so it renders
 *  the vendor fact (its console), never a fabricated process read. */
export const doorHealthOf = (name: string): DoorHealth | undefined => {
  const door = (DOOR_HEALTH as Record<string, DoorHealth>)[name];
  return door;
};

/** The read, as the hook hands it to the card. `status` is the endpoint's HTTP answer when it
 * answered at all; `error` is the wire failure when it did not. */
export type DoorRead =
  | { state: 'loading' }
  | { state: 'answered'; status: number }
  | { state: 'unread'; error: string };

/**
 * One plain sentence (plus a verdict word) for one DoorRead. The estate's rule applied to a
 * door: a process that did not answer is never drawn green, and a 2xx is "up" only because the
 * process's OWN health endpoint said so -- this component does not know the product works, only
 * that the door answered. A non-2xx "answers, but not healthy" is not green either.
 */
export const doorSentence = (
  label: string,
  read: DoorRead,
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

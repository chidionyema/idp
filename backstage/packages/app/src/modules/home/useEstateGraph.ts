// The estate graph, read through the estate's one MCP server (ADR 0006).
//
// Every other hook on this page calls the Kubernetes API: useClusterHealth, useOpenReds,
// useInventory. Those are PROBES -- they answer "what does the cluster say right now". This
// one calls the graph, which answers a different question: "what has the estate recorded
// about itself", including the half a probe cannot reach. A branch carrying 94,093 files
// that exist on no commit of main is not a cluster object and no kubectl call will find it.
//
// The tool is `get_estate_state` on the existing estate MCP server
// (mcp/plugins/estate_twin.py). There is no second server and no new endpoint.
import { useEffect, useState } from 'react';
import { EstateGraph, Loaded } from './estateGraph';
import { REFRESH_MS } from './useEstate';

/** The estate MCP tool that answers from the graph rather than from a fresh probe. */
export const ESTATE_STATE_TOOL = 'get_estate_state';

/** The route the estate MCP server is reached through, as every other tool call is. */
export const ESTATE_STATE_PATH = '/api/proxy/mcp/estate';

export const useEstateGraph = (): Loaded => {
  const [loaded, setLoaded] = useState<Loaded>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    const read = async () => {
      try {
        const r = await fetch(ESTATE_STATE_PATH, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            jsonrpc: '2.0',
            id: 1,
            method: 'tools/call',
            params: { name: ESTATE_STATE_TOOL, arguments: {} },
          }),
        });
        if (!r.ok) {
          throw new Error(`${ESTATE_STATE_PATH} answered ${r.status}`);
        }
        const body = await r.json();
        // An MCP tool result arrives as content[0].text carrying JSON. A shape that does not
        // parse is an error, never an empty graph -- an empty graph reads as "nothing wrong".
        const text = body?.result?.content?.[0]?.text ?? body?.result;
        const graph: EstateGraph = typeof text === 'string' ? JSON.parse(text) : text;
        if (!graph || !Array.isArray(graph.domains)) {
          throw new Error(`${ESTATE_STATE_TOOL} returned no domains`);
        }
        if (!cancelled) setLoaded({ state: 'ready', graph });
      } catch (e) {
        if (!cancelled) {
          setLoaded({ state: 'error', error: e instanceof Error ? e.message : String(e) });
        }
      }
    };
    read();
    const t = setInterval(read, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);

  return loaded;
};

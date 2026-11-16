// ==UserScript==
// @name         genesis-mycelium
// @namespace    https://genesis-founder-surface.pages.dev
// @version      1.0.0
// @description  I-8096-REV2 channel 1: tee AI Studio model turns to the zero-click ingest edge
// @match        https://aistudio.google.com/*
// @grant        none
// @run-at       document-start
// ==/UserScript==

// Zero human action after install. The token is the one secret the founder stores once, in
// this origin's localStorage: genesis.ingest.token. Everything after that is automatic: a
// finished model turn has its code blocks extracted, SHA-256'd in-page and POSTed to the
// worker, which is where the second channel (Drive) joins it and dedupes by (path, sha256).

(function () {
  "use strict";

  const DEFAULT_ENDPOINT = "https://genesis-founder-surface.pages.dev";
  const TOKEN_KEY = "genesis.ingest.token";
  const URL_KEY = "genesis.ingest.url";
  const PATH = /[A-Za-z0-9._/-]+\.(?:ts|tsx|js|jsx|mjs|cjs|json|css|scss|md|html|py|rb|go|rs|java|kt|swift|sh|yml|yaml|toml|sql|txt)$/;
  const FENCE = /```([^\n`]*)\n([\s\S]*?)```/g;

  function bytesToB64(bytes) {
    let bin = "";
    for (const b of bytes) bin += String.fromCharCode(b);
    return btoa(bin);
  }

  async function sha256Hex(text) {
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
    return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  function pathFromHeader(header, body) {
    const named = header.match(PATH);
    if (named) return named[0];
    const comment = body.match(/^\s*(?:\/\/|#|\/\*)\s*([A-Za-z0-9._/-]+\.\w+)/);
    return comment ? comment[1] : null;
  }

  function extractArtifacts(text) {
    const files = new Map();
    let match;
    FENCE.lastIndex = 0;
    while ((match = FENCE.exec(text || ""))) {
      const header = (match[1] || "").trim();
      const body = match[2] || "";
      const path = pathFromHeader(header, body);
      if (!path) continue;
      files.set(path, body);
    }
    return [...files].map(([path, content]) => ({ path, content }));
  }

  function endpoint() {
    try {
      return localStorage.getItem(URL_KEY) || DEFAULT_ENDPOINT;
    } catch {
      return DEFAULT_ENDPOINT;
    }
  }

  function token() {
    try {
      return localStorage.getItem(TOKEN_KEY) || "";
    } catch {
      return "";
    }
  }

  async function submit(text) {
    const files = extractArtifacts(text);
    if (files.length === 0) return { ok: false, reason: "NO_ARTIFACTS" };
    const bearer = token();
    if (!bearer) return { ok: false, reason: "TOKEN_ABSENT" };

    const payload = {
      source: "stream",
      files: await Promise.all(
        files.map(async (file) => {
          const bytes = new TextEncoder().encode(file.content);
          return {
            path: file.path,
            content_b64: bytesToB64(bytes),
            sha256: await sha256Hex(file.content),
            bytes: bytes.length,
          };
        }),
      ),
    };

    const res = await fetch(`${endpoint()}/api/ingest/stream`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-genesis-ingest-token": bearer,
      },
      body: JSON.stringify(payload),
      keepalive: true,
    });
    return res.json();
  }

  function teeFetch() {
    const original = window.fetch;
    window.fetch = async function (...args) {
      const response = await original.apply(this, args);
      const url = String(args[0]?.url || args[0] || "");
      if (!/aistudio\.google\.com/.test(url)) return response;
      try {
        const clone = response.clone();
        const reader = clone.body?.getReader();
        if (!reader) return response;
        const decoder = new TextDecoder();
        let text = "";
        (async () => {
          for (;;) {
            const { done, value } = await reader.read();
            if (done) break;
            text += decoder.decode(value, { stream: true });
          }
          text += decoder.decode();
          if (text.trim()) submit(text).catch(() => {});
        })();
      } catch {
        /* a tee that cannot read must never break the page */
      }
      return response;
    };
  }

  function observeTurns() {
    let timer = null;
    const observer = new MutationObserver(() => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const turns = document.querySelectorAll("ms-chat-turn, [data-turn-role='model']");
        if (turns.length === 0) return;
        const last = turns[turns.length - 1].innerText || "";
        if (last.includes("```")) submit(last).catch(() => {});
      }, 1200);
    });
    observer.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
  }

  if (typeof window !== "undefined" && typeof document !== "undefined") {
    teeFetch();
    observeTurns();
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { extractArtifacts, sha256Hex, pathFromHeader };
  }
})();

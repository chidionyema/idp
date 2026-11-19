// ==UserScript==
// @name         Genesis Estate One-Brain Web Sidecar & Zero-Credit Lifeboat Bridge
// @namespace    https://genesis-estate.ai/one-brain
// @version      6.0.0
// @description  Connects DeepSeek Web, Claude Web, ChatGPT Web, Kimi Web, Grok, Meta Muse, and Z.ai into the Genesis One-Brain Federation (GEN-NET-006) for real-time Council voting and £0-API-Credit Lifeboat Relay.
// @match        https://chat.deepseek.com/*
// @match        https://claude.ai/*
// @match        https://chatgpt.com/*
// @match        https://kimi.moonshot.cn/*
// @match        https://grok.com/*
// @match        https://www.meta.ai/*
// @grant        none
// ==/UserScript==

(function () {
  'use strict';

  const BRAIN_HUB_URL =
    window.localStorage.getItem('GENESIS_BRAIN_HUB_URL') ||
    'https://ais-pre-6t2ghnwqn4d2uzq7jeutd2-534240513427.europe-west3.run.app';

  const host = window.location.hostname;
  const surfaceId = `surf-web-${host.replace(/[^a-z0-9]+/gi, '-')}`;

  async function sendWebSurfaceHeartbeat() {
    try {
      const res = await fetch(`${BRAIN_HUB_URL}/api/brain/heartbeat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          surfaceId,
          surfaceName: `Web Lifeboat (${host})`,
          modelBackbone: `${host} Zero-Credit Web Session`,
          category: 'web_zero_credit_lifeboat',
          transport: 'BROWSER_USERSCRIPT_SIDECAR',
          creditMode: 'ZERO_API_CREDIT_FREE_WEB',
          currentActivity: `Attached to ${host} via Userscript Sidecar (£0 API credit lifeboat ready)`,
        }),
      });
      return await res.json();
    } catch (err) {
      console.debug('[GEN-NET-006] One-Brain heartbeat deferred:', err.message);
      return null;
    }
  }

  // Poll every 15s to keep Web Surface registered in the One-Brain Federation
  setInterval(sendWebSurfaceHeartbeat, 15000);
  sendWebSurfaceHeartbeat();
})();

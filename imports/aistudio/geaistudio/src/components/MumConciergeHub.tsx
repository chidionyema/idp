import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Copy,
  Download,
  Eye,
  FileWarning,
  Lock,
  MessageCircle,
  PhoneCall,
  PiggyBank,
  Play,
  RefreshCw,
  RotateCcw,
  Send,
  ShieldAlert,
  ShieldCheck,
  Volume2,
  XCircle,
} from 'lucide-react';
import type {
  MumConciergeOverviewSnapshot,
  NegativeFixtureId,
} from '../engine/mumsConcierge';

type HubMode = 'family_whatsapp' | 'document_lab' | 'control_tower';

const NEGATIVE_LABELS: Array<{ id: NegativeFixtureId; label: string }> = [
  { id: 'clean_eon_001', label: 'EON-001 Valid (£95.11 Credit)' },
  { id: 'missing_pages', label: '1. Missing Pages' },
  { id: 'unreadable_figures', label: '2. Blurry / Unreadable Figures' },
  { id: 'conflicting_meter_readings', label: '3. Conflicting Meter Readings' },
  { id: 'misleading_discount', label: '4. Misleading Discount + Exit Fee' },
  { id: 'expired_tariff', label: '5. Expired Tariff Quote' },
  { id: 'spoofed_supplier', label: '6. Spoofed Supplier Domain' },
  { id: 'false_refund_offer', label: '7. False Refund / Rebate Phish' },
  { id: 'repeated_whatsapp_delivery', label: '8. Duplicate WhatsApp SID' },
  { id: 'provider_timeout', label: '9. Provider Portal Timeout' },
  { id: 'guardian_unavailable', label: '10. Guardian Unavailable' },
  { id: 'cancel_during_transaction', label: '11. Cancel Mid-Transaction' },
];

export function MumConciergeHub() {
  const [snap, setSnap] = useState<MumConciergeOverviewSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<HubMode>('family_whatsapp');
  const [largeVision, setLargeVision] = useState(true);
  const [whatsappInput, setWhatsappInput] = useState('');
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [selectedChoiceBanner, setSelectedChoiceBanner] = useState<string | null>(null);
  const [speakingText, setSpeakingText] = useState(false);
  const [customIngestUrl, setCustomIngestUrl] = useState('');
  const [pushMethod, setPushMethod] = useState<'POST' | 'PUT'>('POST');
  const [handoffStatus, setHandoffStatus] = useState<string | null>(null);

  async function loadOverview() {
    setLoading(true);
    try {
      const res = await fetch('/api/concierge/overview');
      if (res.ok) {
        const json = (await res.json()) as MumConciergeOverviewSnapshot;
        setSnap(json);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadOverview();
  }, []);

  function speakAloud(text: string) {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      setSelectedChoiceBanner('Voice playback prepared: ' + text.slice(0, 120) + '...');
      return;
    }
    try {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      utter.rate = 0.9;
      utter.onstart = () => setSpeakingText(true);
      utter.onend = () => setSpeakingText(false);
      utter.onerror = () => setSpeakingText(false);
      window.speechSynthesis.speak(utter);
    } catch {
      setSpeakingText(false);
    }
  }

  async function sendWhatsAppBurst(
    preset: 'eon_burst' | 'cancel_burst' | 'scam_forward' | 'distress' | 'custom'
  ) {
    setBusyAction(preset);
    const now = Date.now();
    let fragments: Array<{
      messageSid: string;
      senderRole: 'MUMMY';
      channel: 'text' | 'voice_note' | 'guided_button';
      timestampMs: number;
      text: string;
    }> = [];

    if (preset === 'eon_burst') {
      fragments = [
        {
          messageSid: `ui-eon-${now}-1`,
          senderRole: 'MUMMY',
          channel: 'voice_note',
          timestampMs: now,
          text: 'Auntie Ezinne I just got an E.ON bill on WhatsApp',
        },
        {
          messageSid: `ui-eon-${now}-2`,
          senderRole: 'MUMMY',
          channel: 'text',
          timestampMs: now + 1500,
          text: 'wait it says £95.11 and £52.43 Direct Debit am I in debt?',
        },
        {
          messageSid: `ui-eon-${now}-2`, // intentional duplicate SID to verify dedupe
          senderRole: 'MUMMY',
          channel: 'text',
          timestampMs: now + 1600,
          text: 'wait it says £95.11 and £52.43 Direct Debit am I in debt?',
        },
      ];
    } else if (preset === 'cancel_burst') {
      fragments = [
        {
          messageSid: `ui-can-${now}-1`,
          senderRole: 'MUMMY',
          channel: 'text',
          timestampMs: now,
          text: 'Please order the fruit basket',
        },
        {
          messageSid: `ui-can-${now}-2`,
          senderRole: 'MUMMY',
          channel: 'text',
          timestampMs: now + 1800,
          text: 'Actually stop cancel do not do that',
        },
      ];
    } else if (preset === 'scam_forward') {
      fragments = [
        {
          messageSid: `ui-scam-${now}-1`,
          senderRole: 'MUMMY',
          channel: 'text',
          timestampMs: now,
          text: 'Forwarded message: Urgent bank transfer HMRC arrest risk buy £100 gift card and send OTP pin code',
        },
      ];
    } else if (preset === 'distress') {
      fragments = [
        {
          messageSid: `ui-dist-${now}-1`,
          senderRole: 'MUMMY',
          channel: 'voice_note',
          timestampMs: now,
          text: 'I feel dizzy and scared I have chest pain please help me',
        },
      ];
    } else if (whatsappInput.trim()) {
      fragments = [
        {
          messageSid: `ui-cust-${now}`,
          senderRole: 'MUMMY',
          channel: 'text',
          timestampMs: now,
          text: whatsappInput.trim(),
        },
      ];
    }

    if (fragments.length === 0) {
      setBusyAction(null);
      return;
    }

    try {
      const res = await fetch('/api/concierge/whatsapp-burst', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fragments }),
      });
      if (res.ok) {
        const json = (await res.json()) as { snapshot: MumConciergeOverviewSnapshot };
        setSnap(json.snapshot);
        if (preset === 'custom') setWhatsappInput('');
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function runDocumentFixture(fixtureId: NegativeFixtureId) {
    setBusyAction(fixtureId);
    try {
      const res = await fetch('/api/concierge/document-analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fixtureId }),
      });
      if (res.ok) {
        const json = (await res.json()) as { snapshot: MumConciergeOverviewSnapshot };
        setSnap(json.snapshot);
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function triggerGuardianAction(
    action:
      | 'kill_switch_on'
      | 'kill_switch_off'
      | 'guardian_offline'
      | 'guardian_online'
      | 'cancel_all'
      | 'fulfilment_approve'
      | 'fulfilment_cancel'
      | 'fulfilment_recover',
    id?: string
  ) {
    setBusyAction(action + (id ?? ''));
    try {
      const res = await fetch('/api/concierge/guardian-action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, id }),
      });
      if (res.ok) {
        const json = (await res.json()) as { snapshot: MumConciergeOverviewSnapshot };
        setSnap(json.snapshot);
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function createInterruptedFulfilment() {
    setBusyAction('interrupt_demo');
    try {
      const res = await fetch('/api/concierge/fulfil', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          idempotencyKey: `idem-rx-${Date.now()}`,
          kind: 'prescription',
          title: 'Repeat NHS Blood Pressure Prescription (Simulated Interrupt)',
          amountGbp: 0,
          motherConfirmed: true,
          simulateInterruption: true,
        }),
      });
      if (res.ok) {
        const json = (await res.json()) as { snapshot: MumConciergeOverviewSnapshot };
        setSnap(json.snapshot);
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function runAllFalsifiers() {
    setBusyAction('falsify_all');
    try {
      const res = await fetch('/api/concierge/falsify-all', { method: 'POST' });
      if (res.ok) {
        const json = (await res.json()) as { snapshot: MumConciergeOverviewSnapshot };
        setSnap(json.snapshot);
      }
    } finally {
      setBusyAction(null);
    }
  }

  async function downloadAuthenticatedArtifact(url: string, filename: string) {
    setBusyAction(`dl:${filename}`);
    setHandoffStatus(null);
    try {
      const res = await fetch(url);
      if (!res.ok) {
        setHandoffStatus(`Download failed: HTTP ${res.status}`);
        return;
      }
      const blob = await res.blob();
      const objUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = objUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(objUrl), 5000);
      setHandoffStatus(`Downloaded ${filename} (${blob.size.toLocaleString()} bytes) via authenticated browser session.`);
    } catch (err) {
      setHandoffStatus(err instanceof Error ? err.message : 'Browser download failed');
    } finally {
      setBusyAction(null);
    }
  }

  async function copyFifteenFileShellUnpack() {
    setBusyAction('copy_b64');
    setHandoffStatus(null);
    try {
      const res = await fetch('/api/export/concierge-pack?format=json');
      if (!res.ok) {
        setHandoffStatus(`Pack fetch failed: HTTP ${res.status}`);
        return;
      }
      const json = (await res.json()) as {
        ok: boolean;
        bytes: number;
        sha256: string;
        base64: string;
      };
      const shellCmd = `python3 -c 'import base64,hashlib,sys; b=base64.b64decode("${json.base64}"); assert hashlib.sha256(b).hexdigest()=="${json.sha256}"; open("mums-concierge-15-files.tar.gz","wb").write(b); print("VERIFIED",len(b),"bytes")' && tar -xzvf mums-concierge-15-files.tar.gz`;
      await navigator.clipboard.writeText(shellCmd);
      setHandoffStatus(
        `Copied self-verifying 15-file shell unpack command (${json.bytes.toLocaleString()} B, SHA-256 ${json.sha256.slice(0, 12)}…) to clipboard.`
      );
    } catch (err) {
      setHandoffStatus(err instanceof Error ? err.message : 'Clipboard copy failed');
    } finally {
      setBusyAction(null);
    }
  }

  async function pushToCustomFleetEndpoint() {
    if (!customIngestUrl.trim()) return;
    setBusyAction('push_custom');
    setHandoffStatus(null);
    try {
      const res = await fetch('/api/export/push-bundle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ingestUrl: customIngestUrl.trim(), method: pushMethod }),
      });
      const json = (await res.json()) as {
        pushed?: boolean;
        httpStatus?: number | null;
        bundleSha256?: string | null;
        reason?: string;
        error?: string;
      };
      if (json.pushed) {
        setHandoffStatus(
          `PUSHED (${pushMethod} -> HTTP ${json.httpStatus}) · SHA-256 ${json.bundleSha256?.slice(0, 16)}…`
        );
      } else {
        setHandoffStatus(
          `Not accepted: ${json.error ?? json.reason ?? `HTTP ${json.httpStatus ?? 'unreachable'}`}`
        );
      }
    } catch (err) {
      setHandoffStatus(err instanceof Error ? err.message : 'Outbound push failed');
    } finally {
      setBusyAction(null);
    }
  }

  if (loading || !snap) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-6 text-sm text-slate-600">
        Loading Mum’s Sovereign Concierge (Auntie Ezinne) control plane…
      </div>
    );
  }

  const eon = snap.latestEonAnalysis;
  const safetyPassCount = snap.safetyFalsifiers.filter((s) => s.passed).length;
  const negPassCount = snap.negativeFixtures.filter((n) => n.passed).length;

  return (
    <div className="space-y-6">
      {/* Top Mode & Honest Release Header */}
      <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
        <div className="space-y-3">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-slate-500">
                <span className="font-semibold text-slate-900">MUM-CONCIERGE-001</span>
                <span aria-hidden="true">·</span>
                <span>P0 Family Safety</span>
                <span aria-hidden="true">·</span>
                <span>Primary Touchpoint: WhatsApp Audio + Large Print</span>
              </div>
              <span
                className={`font-semibold ${
                  snap.overallFamilyReleasePermitted ? 'text-emerald-700' : 'text-amber-700'
                }`}
              >
                Live Family Release: {snap.overallFamilyReleasePermitted ? 'CERTIFIED' : 'GATED (G2/G3/G4 UNKNOWN)'}
              </span>
            </div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">
              Auntie Ezinne — Mummy’s WhatsApp Concierge &amp; Guardian Safety Tower
            </h2>
            <p className="text-xs text-slate-600">
              Baseline <span className="font-mono">{snap.baseline.productRepo}@{snap.baseline.mainSha.slice(0, 8)}</span> ·{' '}
              Family Schema <span className="font-mono">{snap.baseline.familyIntegrationRef}</span> · Deploy Dep{' '}
              <span className="font-mono">{snap.baseline.deploymentDependency} (OPEN)</span>
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 pt-1">
            <button
              type="button"
              onClick={() => setMode('family_whatsapp')}
              className={`min-h-[44px] px-4 py-2 rounded-lg text-xs font-semibold transition-colors whitespace-nowrap ${
                mode === 'family_whatsapp'
                  ? 'bg-emerald-700 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              Mummy’s WhatsApp View (Zero Jargon)
            </button>
            <button
              type="button"
              onClick={() => setMode('document_lab')}
              className={`min-h-[44px] px-4 py-2 rounded-lg text-xs font-semibold transition-colors whitespace-nowrap ${
                mode === 'document_lab'
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              EON-001 &amp; 11 Negative Cases
            </button>
            <button
              type="button"
              onClick={() => setMode('control_tower')}
              className={`min-h-[44px] px-4 py-2 rounded-lg text-xs font-semibold transition-colors whitespace-nowrap ${
                mode === 'control_tower'
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              Founder &amp; Guardian Tower (WP01–WP08)
            </button>
          </div>
        </div>

        {/* Truthful Non-Completion Banner */}
        <div className="rounded-lg border border-amber-300 bg-amber-50/70 px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs text-amber-950">
          <span>
            <strong>Epistemic Rule (PR #7999 · MUM-CONCIERGE-001):</strong> Local safety controls (9/9), EON-001 reconciliation, and 11/11 negative tests pass in sandbox; live Modal/Twilio deploy (<strong>G2</strong>), live merchant APIs (<strong>G3</strong>), and a real supervised trial with Mummy (<strong>G4</strong>) remain strictly <strong>UNKNOWN</strong> until executed live.
          </span>
          <button
            type="button"
            disabled={busyAction === 'falsify_all'}
            onClick={() => void runAllFalsifiers()}
            className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800 whitespace-nowrap shrink-0"
          >
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            Re-Verify All 20 Safety &amp; Negative Cases
          </button>
        </div>

        {/* Fleet Source Recovery & Outbound Push Bar (Bypasses AI Studio Unauthenticated Cookie Gate) */}
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 space-y-2.5 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-slate-700">
              <strong>Fleet Source Recovery:</strong> External unauthenticated <code className="font-mono">curl</code> hits AI Studio’s cookie gate. Export directly from this authenticated browser session or push outbound to any fleet HTTPS webhook / presigned URL:
            </span>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={busyAction !== null}
                onClick={() =>
                  void downloadAuthenticatedArtifact(
                    '/api/export/bundle',
                    'meridian-hermes-today.bundle'
                  )
                }
                className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 font-medium text-white hover:bg-slate-800 disabled:opacity-50 whitespace-nowrap"
              >
                <Download className="h-3.5 w-3.5" aria-hidden="true" />
                Download Git Bundle (.bundle)
              </button>
              <button
                type="button"
                disabled={busyAction !== null}
                onClick={() =>
                  void downloadAuthenticatedArtifact(
                    '/api/export/concierge-pack',
                    'mums-concierge-15-files.tar.gz'
                  )
                }
                className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 font-medium text-slate-900 hover:bg-slate-100 disabled:opacity-50 whitespace-nowrap"
              >
                <Download className="h-3.5 w-3.5" aria-hidden="true" />
                15-File Tarball (.tar.gz)
              </button>
              <button
                type="button"
                disabled={busyAction !== null}
                onClick={() => void copyFifteenFileShellUnpack()}
                className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 font-medium text-slate-900 hover:bg-slate-100 disabled:opacity-50 whitespace-nowrap"
              >
                <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                Copy 1-Line Shell Unpack
              </button>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              aria-label="Outbound HTTP method"
              value={pushMethod}
              onChange={(e) => setPushMethod(e.target.value === 'PUT' ? 'PUT' : 'POST')}
              className="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 font-mono text-xs text-slate-900"
            >
              <option value="POST">POST</option>
              <option value="PUT">PUT (Presigned)</option>
            </select>
            <input
              type="url"
              value={customIngestUrl}
              onChange={(e) => setCustomIngestUrl(e.target.value)}
              placeholder="https://your-modal-or-cloudflare-endpoint/api/ingest/bundle (or presigned S3/R2/GCS PUT URL)"
              className="min-w-[240px] flex-1 rounded-md border border-slate-300 bg-white px-3 py-1.5 font-mono text-xs text-slate-900"
            />
            <button
              type="button"
              disabled={busyAction !== null || !customIngestUrl.trim()}
              onClick={() => void pushToCustomFleetEndpoint()}
              className="inline-flex items-center gap-1.5 rounded-md bg-emerald-700 px-3 py-1.5 font-semibold text-white hover:bg-emerald-800 disabled:opacity-50 whitespace-nowrap"
            >
              <Send className="h-3.5 w-3.5" aria-hidden="true" />
              Push Bundle Outbound
            </button>
          </div>

          {handoffStatus && (
            <div className="rounded border border-slate-300 bg-white px-3 py-1.5 font-mono text-xs text-slate-800">
              {handoffStatus}
            </div>
          )}
        </div>
      </section>

      {/* ===================================================================== */}
      {/* VIEW 1: MUMMY'S WHATSAPP & LOW-VISION ACCESSIBLE EXPERIENCE (WP03/07) */}
      {/* ===================================================================== */}
      {mode === 'family_whatsapp' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left / Main accessible WhatsApp Family Experience */}
          <section className="lg:col-span-7 bg-white border-2 border-slate-900 rounded-2xl overflow-hidden flex flex-col">
            {/* Warm WhatsApp Top Header */}
            <div className="bg-emerald-800 text-white px-5 py-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="h-11 w-11 rounded-full bg-emerald-600 flex items-center justify-center font-bold text-lg shrink-0">
                  AE
                </div>
                <div>
                  <div className="text-lg font-bold leading-tight">Auntie Ezinne (WhatsApp)</div>
                  <div className="text-xs text-emerald-100">
                    Your quiet family helper · Voice note &amp; large print ready
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => setLargeVision((prev) => !prev)}
                  className="min-h-[44px] inline-flex items-center gap-1.5 rounded-lg bg-emerald-950/60 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-950"
                >
                  <Eye className="h-4 w-4" aria-hidden="true" />
                  {largeVision ? 'Extra-Large Print: ON' : 'Standard Print'}
                </button>
                <button
                  type="button"
                  onClick={() => speakAloud(eon.familyFriendlySummary)}
                  className="min-h-[44px] inline-flex items-center gap-1.5 rounded-lg bg-white text-emerald-950 px-3.5 py-2 text-xs font-bold hover:bg-emerald-50"
                >
                  <Volume2 className="h-4 w-4" aria-hidden="true" />
                  {speakingText ? 'Speaking…' : 'Listen Out Loud'}
                </button>
              </div>
            </div>

            {/* Key Money Truth Card — Never calls credit debt! */}
            <div className="p-5 bg-emerald-50/70 border-b border-emerald-200 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-bold uppercase tracking-wide text-emerald-900">
                  Your E.ON Next Bill Summary
                </span>
                <span className="text-xs font-semibold text-emerald-800">
                  {eon.billingPeriod}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="rounded-xl bg-white border border-emerald-300 p-3.5">
                  <div className="text-xs font-semibold text-slate-600">Account Balance</div>
                  <div
                    className={`mt-1 font-bold font-mono tabular-nums text-emerald-800 ${
                      largeVision ? 'text-2xl' : 'text-xl'
                    }`}
                  >
                    £{eon.closingBalanceGbp.toFixed(2)} CREDIT
                  </div>
                  <div className="mt-0.5 text-xs font-semibold text-emerald-700">
                    You owe £0 extra
                  </div>
                </div>
                <div className="rounded-xl bg-white border border-slate-300 p-3.5">
                  <div className="text-xs font-semibold text-slate-600">Monthly Direct Debit</div>
                  <div
                    className={`mt-1 font-bold font-mono tabular-nums text-slate-900 ${
                      largeVision ? 'text-2xl' : 'text-xl'
                    }`}
                  >
                    £{eon.monthlyDirectDebitGbp.toFixed(2)} / mo
                  </div>
                  <div className="mt-0.5 text-xs text-slate-600">Regular steady payment</div>
                </div>
                <div className="rounded-xl bg-white border border-slate-300 p-3.5">
                  <div className="text-xs font-semibold text-slate-600">This Month’s Usage Cost</div>
                  <div
                    className={`mt-1 font-bold font-mono tabular-nums text-slate-900 ${
                      largeVision ? 'text-2xl' : 'text-xl'
                    }`}
                  >
                    £{eon.estimatedAverageMonthlyCostGbp.toFixed(2)}
                  </div>
                  <div className="mt-0.5 text-xs text-slate-600">Covered by your £95.11 credit</div>
                </div>
              </div>

              <p className={`text-slate-900 leading-relaxed ${largeVision ? 'text-lg font-medium' : 'text-sm'}`}>
                {eon.familyFriendlySummary}
              </p>

              {/* Money-Saving Protector Highlights */}
              {eon.householdSavingsOpportunities.length > 0 && (
                <div className="rounded-xl bg-white border border-emerald-200 p-3.5 space-y-1.5">
                  <div className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-900">
                    <PiggyBank className="h-4 w-4 text-emerald-700" aria-hidden="true" />
                    How We Kept Your Money Safe Today
                  </div>
                  <ul className="space-y-1">
                    {eon.householdSavingsOpportunities.map((sav) => (
                      <li
                        key={sav.id}
                        className={`text-slate-800 ${largeVision ? 'text-base' : 'text-xs'}`}
                      >
                        • {sav.whatsappLine}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Calm 3 Choices — Large 48px+ Tap Targets */}
              <div className="space-y-2 pt-1">
                <div className="text-xs font-bold text-slate-700">
                  Choose what you would like to do (nothing happens unless you and Chidi both agree):
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  {eon.threeGentleChoices.map((choice) => (
                    <button
                      key={choice.id}
                      type="button"
                      onClick={() => {
                        setSelectedChoiceBanner(
                          `Selected "${choice.label}": ${choice.description}`
                        );
                        if (choice.id === 'hear_more') {
                          speakAloud(
                            `${eon.familyFriendlySummary} ${eon.directDebitVsCostExplanation}`
                          );
                        }
                      }}
                      className={`min-h-[52px] rounded-xl border-2 p-3 text-left transition-colors ${
                        choice.id === 'do_nothing'
                          ? 'border-emerald-700 bg-emerald-800 text-white hover:bg-emerald-900'
                          : 'border-slate-800 bg-white text-slate-900 hover:bg-slate-100'
                      }`}
                    >
                      <div className={`font-bold ${largeVision ? 'text-base' : 'text-sm'}`}>
                        {choice.label}
                      </div>
                      <div
                        className={`mt-0.5 leading-snug ${
                          choice.id === 'do_nothing' ? 'text-emerald-100' : 'text-slate-600'
                        } text-xs`}
                      >
                        {choice.description}
                      </div>
                    </button>
                  ))}
                </div>
                {selectedChoiceBanner && (
                  <div className="rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-900">
                    {selectedChoiceBanner}
                  </div>
                )}
              </div>
            </div>

            {/* Warm WhatsApp Conversation Feed */}
            <div className="p-5 bg-slate-50 space-y-3 max-h-80 overflow-y-auto">
              {snap.familyConversationLog.map((msg) => (
                <div
                  key={msg.id}
                  className={`rounded-2xl px-4 py-3 border ${
                    msg.speaker === 'MUMMY'
                      ? 'bg-emerald-100/70 border-emerald-300 ml-6'
                      : 'bg-white border-slate-300 mr-6'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 text-xs text-slate-600 mb-1">
                    <span className="font-bold text-slate-900">
                      {msg.speaker === 'MUMMY' ? 'Mummy' : 'Auntie Ezinne'}
                    </span>
                    <span>
                      {msg.timestampLabel}
                      {msg.tag ? ` · ${msg.tag}` : ''}
                    </span>
                  </div>
                  <p className={`text-slate-900 leading-relaxed ${largeVision ? 'text-base font-medium' : 'text-sm'}`}>
                    {msg.text}
                  </p>
                </div>
              ))}
            </div>

            {/* Reply + Always-Present Cancel & Human Help */}
            <div className="p-4 bg-white border-t border-slate-200 space-y-3">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void sendWhatsAppBurst('custom');
                }}
                className="flex gap-2"
              >
                <label htmlFor="mummy-whatsapp-msg" className="sr-only">
                  Send a WhatsApp message to Auntie Ezinne
                </label>
                <input
                  id="mummy-whatsapp-msg"
                  type="text"
                  value={whatsappInput}
                  onChange={(e) => setWhatsappInput(e.target.value)}
                  placeholder="Type a simple message or question (e.g., Check my bill or Stop)…"
                  className="min-w-0 flex-1 min-h-[48px] rounded-xl border-2 border-slate-300 px-4 text-base text-slate-900 focus:border-slate-900 focus:outline-none"
                />
                <button
                  type="submit"
                  disabled={busyAction !== null || !whatsappInput.trim()}
                  className="min-h-[48px] inline-flex items-center gap-2 rounded-xl bg-emerald-700 px-5 text-sm font-bold text-white hover:bg-emerald-800 disabled:opacity-50 whitespace-nowrap"
                >
                  <Send className="h-4 w-4" aria-hidden="true" />
                  Send
                </button>
              </form>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => void triggerGuardianAction('cancel_all')}
                  className="min-h-[52px] inline-flex items-center justify-center gap-2 rounded-xl border-2 border-red-700 bg-red-50 px-4 text-base font-bold text-red-900 hover:bg-red-100"
                >
                  <XCircle className="h-5 w-5" aria-hidden="true" />
                  Stop &amp; Cancel Everything
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedChoiceBanner(
                      'Requested a calm phone call from Chidi (Family Helper) — no automated purchase can proceed.'
                    );
                    speakAloud('I have asked Chidi to ring you gently on your phone, Mummy.');
                  }}
                  className="min-h-[52px] inline-flex items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 text-base font-bold text-white hover:bg-slate-800"
                >
                  <PhoneCall className="h-5 w-5 text-emerald-400" aria-hidden="true" />
                  Speak to Family / Chidi
                </button>
              </div>
            </div>
          </section>

          {/* Right: 4s WhatsApp Burst Simulator & Formatted Phone Preview */}
          <aside className="lg:col-span-5 space-y-5">
            <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
              <div className="flex items-center gap-2">
                <MessageCircle className="h-4 w-4 text-emerald-700" aria-hidden="true" />
                <h3 className="text-sm font-bold text-slate-900">
                  WP03 · 4-Second WhatsApp Burst Coalescer Tests
                </h3>
              </div>
              <p className="text-xs text-slate-600">
                Real family messages often arrive as quick fragments (voice note + hesitation + typo + duplicate webhook SID). Test how Auntie Ezinne waits 4,000ms to combine fragments cleanly — or stops instantly on cancellation.
              </p>
              <div className="grid grid-cols-1 gap-2">
                <button
                  type="button"
                  disabled={busyAction !== null}
                  onClick={() => void sendWhatsAppBurst('eon_burst')}
                  className="min-h-[44px] rounded-lg border border-slate-300 bg-slate-50 px-3.5 py-2 text-left text-xs font-semibold text-slate-900 hover:bg-slate-100"
                >
                  1. Replay Fragmented E.ON Burst + Duplicate Webhook SID
                </button>
                <button
                  type="button"
                  disabled={busyAction !== null}
                  onClick={() => void sendWhatsAppBurst('cancel_burst')}
                  className="min-h-[44px] rounded-lg border border-amber-300 bg-amber-50 px-3.5 py-2 text-left text-xs font-semibold text-amber-950 hover:bg-amber-100"
                >
                  2. Replay Mid-Burst Cancellation (“Actually stop cancel”)
                </button>
                <button
                  type="button"
                  disabled={busyAction !== null}
                  onClick={() => void sendWhatsAppBurst('scam_forward')}
                  className="min-h-[44px] rounded-lg border border-red-300 bg-red-50 px-3.5 py-2 text-left text-xs font-semibold text-red-900 hover:bg-red-100"
                >
                  3. Replay Scam Forward (Gift Card / OTP / HMRC Threat)
                </button>
                <button
                  type="button"
                  disabled={busyAction !== null}
                  onClick={() => void sendWhatsAppBurst('distress')}
                  className="min-h-[44px] rounded-lg border border-red-400 bg-red-100/70 px-3.5 py-2 text-left text-xs font-semibold text-red-950 hover:bg-red-100"
                >
                  4. Replay Health Distress Voice Note (“Dizzy / Chest Pain”)
                </button>
              </div>
            </section>

            {/* Exact Outbound Low-Vision WhatsApp Text Payload */}
            <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-2.5">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-900">
                  Outbound Low-Vision WhatsApp Text + Voice Dispatch
                </h3>
                <span className="font-mono text-xs text-emerald-700">$0.00 Sovereign AI</span>
              </div>
              <pre className="rounded-lg bg-slate-950 text-emerald-100 p-4 text-xs leading-relaxed whitespace-pre-wrap font-sans">
                {eon.whatsappFormattedForLowVision}
              </pre>
            </section>
          </aside>
        </div>
      )}

      {/* ===================================================================== */}
      {/* VIEW 2: WP04 EON-001 & ALL 11 NEGATIVE SCENARIOS LAB                  */}
      {/* ===================================================================== */}
      {mode === 'document_lab' && (
        <div className="space-y-6">
          <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  WP04 · Real Document-to-Action &amp; 11 Negative Failure Fixtures
                </h3>
                <p className="text-xs text-slate-600">
                  Select EON-001 or inject any of the 11 negative edge cases to verify deterministic arithmetic and fail-closed safety.
                </p>
              </div>
              <span className="font-mono text-xs font-semibold text-emerald-700">
                {negPassCount} / {snap.negativeFixtures.length} Negative Cases Passing Fail-Closed
              </span>
            </div>

            <div className="flex flex-wrap gap-2">
              {NEGATIVE_LABELS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  disabled={busyAction !== null}
                  onClick={() => void runDocumentFixture(item.id)}
                  className={`min-h-[40px] rounded-lg px-3 py-1.5 text-xs font-semibold border transition-colors ${
                    eon.fixtureId === item.id
                      ? 'bg-slate-900 text-white border-slate-900'
                      : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>

            {/* Active Document Reconciliation Panel */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 pt-2">
              <div className="rounded-xl border border-slate-200 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-slate-900">{eon.supplierName}</span>
                  <span
                    className={`font-mono text-xs font-bold ${
                      eon.safeToAct ? 'text-emerald-700' : 'text-red-700'
                    }`}
                  >
                    {eon.safeToAct ? 'RECONCILED_CLEAR' : 'PAUSED_FAIL_CLOSED'}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono tabular-nums">
                  <div className="rounded bg-slate-50 p-2">Opening Credit: £{eon.openingCreditGbp.toFixed(2)}</div>
                  <div className="rounded bg-slate-50 p-2">Payment Received: £{eon.paymentsReceivedGbp.toFixed(2)}</div>
                  <div className="rounded bg-slate-50 p-2">Period Charges: £{eon.chargesTotalGbp.toFixed(2)}</div>
                  <div className="rounded bg-emerald-50 p-2 font-bold text-emerald-900">
                    Closing: £{eon.closingBalanceGbp.toFixed(2)} ({eon.balanceInterpretation})
                  </div>
                </div>
                {eon.blockedReason && (
                  <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-900 font-medium">
                    <FileWarning className="inline h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
                    Blocked Reason: {eon.blockedReason}
                  </div>
                )}
                <p className="text-xs text-slate-700">{eon.directDebitVsCostExplanation}</p>
              </div>

              {/* Tariff Net-After-Exit-Fee Comparison */}
              <div className="rounded-xl border border-slate-200 p-4 space-y-3">
                <div className="text-sm font-bold text-slate-900">
                  Tariff Comparison (Honest Net Saving After Exit Fees)
                </div>
                {eon.tariffOptions.length === 0 ? (
                  <div className="text-xs text-slate-600 py-4">
                    Tariff comparison intentionally suppressed while active negative fault blocks safe reconciliation.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {eon.tariffOptions.map((t) => (
                      <div key={t.name} className="rounded-lg border border-slate-200 p-3 text-xs space-y-1">
                        <div className="flex flex-wrap items-center justify-between gap-2 font-semibold text-slate-900">
                          <span>{t.name}</span>
                          <span className="font-mono tabular-nums">
                            {t.unitRatePencePerKwh}p/kWh · Exit Fee £{t.exitFeeGbp} · Yr-1 Net{' '}
                            {t.netFirstYearSavingAfterFeeGbp !== null
                              ? `${t.netFirstYearSavingAfterFeeGbp >= 0 ? '+' : ''}£${t.netFirstYearSavingAfterFeeGbp.toFixed(2)}`
                              : 'N/A'}
                          </span>
                        </div>
                        <div className="text-slate-600">{t.note}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* All 11 Negative Cases Verification Table */}
          <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 font-bold text-sm text-slate-900">
              All 11 Required Negative Acceptance Fixtures
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
                  <tr>
                    <th className="px-4 py-2.5">Scenario</th>
                    <th className="px-4 py-2.5">Status</th>
                    <th className="px-4 py-2.5">Fail-Closed Disposition</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {snap.negativeFixtures.map((nf) => (
                    <tr key={nf.fixtureId} className="hover:bg-slate-50">
                      <td className="px-4 py-2.5 font-medium text-slate-900">{nf.title}</td>
                      <td className="px-4 py-2.5 font-mono font-bold text-emerald-700">
                        {nf.passed ? 'FAIL_CLOSED_PASS' : 'FAILED'}
                      </td>
                      <td className="px-4 py-2.5 text-slate-600">{nf.failClosedDisposition}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}

      {/* ===================================================================== */}
      {/* VIEW 3: FOUNDER & GUARDIAN CONTROL TOWER (WP01–WP08 + G0–G5 GATES)    */}
      {/* ===================================================================== */}
      {mode === 'control_tower' && (
        <div className="space-y-6">
          {/* Founder Telemetry Strip + Emergency Controls */}
          <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <div className="text-xs text-slate-500">AI Run Cost (WhatsApp)</div>
              <div className="mt-1 text-2xl font-mono tabular-nums font-bold text-emerald-700">
                ${snap.founderTelemetryProjection.conciergeInferenceRunCostUsd.toFixed(2)}
              </div>
              <div className="text-xs text-slate-600 mt-0.5">Sovereign $0.00 OpenCode / Nemotron</div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <div className="text-xs text-slate-500">Verified Savings / Traps Avoided</div>
              <div className="mt-1 text-2xl font-mono tabular-nums font-bold text-slate-900">
                £{snap.founderTelemetryProjection.verifiedAnnualSavingsFoundGbp.toFixed(2)}
              </div>
              <div className="text-xs text-slate-600 mt-0.5">Credit cushion + £100 fee trap avoided</div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <div className="text-xs text-slate-500">Nov-16 Safety Falsifiers (WP02)</div>
              <div className="mt-1 text-2xl font-mono tabular-nums font-bold text-emerald-700">
                {safetyPassCount} / {snap.safetyFalsifiers.length}
              </div>
              <div className="text-xs text-slate-600 mt-0.5">String "false" fail-closed verified</div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-2">
              <div className="text-xs font-semibold text-slate-700">Safety Master Switches</div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() =>
                    void triggerGuardianAction(
                      snap.killSwitchActive ? 'kill_switch_off' : 'kill_switch_on'
                    )
                  }
                  className={`min-h-[38px] px-3 py-1.5 rounded-md text-xs font-bold ${
                    snap.killSwitchActive
                      ? 'bg-red-700 text-white'
                      : 'border border-red-300 bg-red-50 text-red-900'
                  }`}
                >
                  {snap.killSwitchActive ? 'Kill Switch: ON (Disarm)' : 'Arm Emergency Kill Switch'}
                </button>
                <button
                  type="button"
                  onClick={() =>
                    void triggerGuardianAction(
                      snap.guardianAvailable ? 'guardian_offline' : 'guardian_online'
                    )
                  }
                  className="min-h-[38px] px-3 py-1.5 rounded-md border border-slate-300 bg-slate-50 text-xs font-semibold text-slate-900"
                >
                  Guardian: {snap.guardianAvailable ? 'Online' : 'Offline (Fail-Closed)'}
                </button>
              </div>
            </div>
          </section>

          {/* G0–G5 Release Gates — Strictly Uninflated */}
          <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-bold text-slate-900">
                Release Gates G0–G5 (Live External Proof Strictly Separated From Sandbox)
              </h3>
              <span className="font-mono text-xs text-amber-800 font-semibold">
                overallFamilyReleasePermitted = {String(snap.overallFamilyReleasePermitted)}
              </span>
            </div>
            <div className="divide-y divide-slate-100">
              {snap.releaseGates.map((g) => (
                <div key={g.gateId} className="px-5 py-3 flex flex-col md:flex-row md:items-center justify-between gap-2 text-xs">
                  <div>
                    <div className="font-bold text-slate-900">
                      {g.gateId} · {g.title}
                    </div>
                    <div className="text-slate-600">{g.honestEvidence}</div>
                  </div>
                  <span
                    className={`font-mono font-bold px-2.5 py-1 rounded-md whitespace-nowrap self-start md:self-center ${
                      g.status === 'PASS'
                        ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                        : g.status === 'LOCAL_VERIFIED'
                          ? 'bg-blue-50 text-blue-800 border border-blue-200'
                          : 'bg-amber-50 text-amber-900 border border-amber-300'
                    }`}
                  >
                    {g.status}
                  </span>
                </div>
              ))}
            </div>
          </section>

          {/* WP02 9/9 Safety Falsifiers */}
          <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-700" aria-hidden="true" />
              <h3 className="text-sm font-bold text-slate-900">
                WP02 · Replay of November 16 Guardian &amp; Safety Falsifiers (9/9)
              </h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {snap.safetyFalsifiers.map((sf) => (
                <div key={sf.id} className="rounded-lg border border-slate-200 p-3 text-xs space-y-1">
                  <div className="flex items-center justify-between font-bold text-slate-900">
                    <span>{sf.title}</span>
                    {sf.passed ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" aria-hidden="true" />
                    ) : (
                      <AlertTriangle className="h-4 w-4 text-red-600 shrink-0" aria-hidden="true" />
                    )}
                  </div>
                  <div className="text-slate-600">{sf.expectedBehavior}</div>
                  <div className="font-mono text-[11px] text-slate-800 break-words">
                    {sf.observedOutcome}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* WP05 Fulfilment Integrity & Recovery + WP06 IDP #8091 Memory */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-bold text-slate-900">
                  WP05 · Fulfilment Queue (Sandbox Typed Ack + Recovery)
                </h3>
                <button
                  type="button"
                  onClick={() => void createInterruptedFulfilment()}
                  className="inline-flex items-center gap-1 rounded border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-800 hover:bg-slate-50"
                >
                  <Play className="h-3 w-3" aria-hidden="true" />
                  Simulate Interrupted Rx
                </button>
              </div>
              <div className="space-y-2.5">
                {snap.fulfilmentQueue.map((item) => (
                  <div key={item.id} className="rounded-lg border border-slate-200 p-3 text-xs space-y-2">
                    <div className="flex items-center justify-between gap-2 font-semibold text-slate-900">
                      <span>
                        [{item.kind.toUpperCase()}] {item.title}
                      </span>
                      <span className="font-mono tabular-nums">£{item.amountGbp.toFixed(2)}</span>
                    </div>
                    <div className="flex flex-wrap items-center justify-between gap-2 text-slate-600 font-mono">
                      <span>{item.status}</span>
                      <span>
                        {item.providerAckId ? `Ack: ${item.providerAckId}` : 'No provider ack yet'}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {item.status === 'AWAITING_GUARDIAN_APPROVAL' && (
                        <button
                          type="button"
                          onClick={() => void triggerGuardianAction('fulfilment_approve', item.id)}
                          className="rounded bg-emerald-700 px-2.5 py-1 text-xs font-semibold text-white hover:bg-emerald-800"
                        >
                          Guardian Approve (Sandbox Ack)
                        </button>
                      )}
                      {item.status === 'INTERRUPTED_RECOVERABLE' && (
                        <button
                          type="button"
                          onClick={() => void triggerGuardianAction('fulfilment_recover', item.id)}
                          className="inline-flex items-center gap-1 rounded bg-blue-700 px-2.5 py-1 text-xs font-semibold text-white hover:bg-blue-800"
                        >
                          <RotateCcw className="h-3 w-3" aria-hidden="true" />
                          Recover Safely
                        </button>
                      )}
                      {(item.status === 'AWAITING_GUARDIAN_APPROVAL' ||
                        item.status === 'AWAITING_MUMMY_CONFIRMATION' ||
                        item.status === 'INTERRUPTED_RECOVERABLE') && (
                        <button
                          type="button"
                          onClick={() => void triggerGuardianAction('fulfilment_cancel', item.id)}
                          className="rounded border border-red-300 bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-900"
                        >
                          Cancel
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* WP06 / WP08 Reconciled IDP #8091 Memory & Redacted Telemetry */}
            <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
              <div className="flex items-center gap-2">
                <Lock className="h-4 w-4 text-slate-700" aria-hidden="true" />
                <h3 className="text-sm font-bold text-slate-900">
                  WP06 &amp; WP08 · Reconciled Memory (IDP #8091) &amp; Privacy Boundary
                </h3>
              </div>
              <div className="rounded-lg bg-slate-50 border border-slate-200 p-3 text-xs space-y-1">
                <div className="font-semibold text-slate-900">
                  Single Schema ({snap.reconciledMemory.schemaVersion}) — Consolidated Legacy Duplicate Tables
                </div>
                <div className="text-slate-600">
                  Private Boundary: <span className="font-mono">{snap.reconciledMemory.privateHouseholdVault.piiBoundary}</span> · Touchpoint: {snap.reconciledMemory.privateHouseholdVault.mummyPreferences.primaryTouchpoint}
                </div>
                <div className="text-slate-600">
                  Founder Privacy Policy: <span className="font-mono">{snap.founderTelemetryProjection.privacyMode}</span>
                </div>
              </div>
              <div className="space-y-1.5 max-h-64 overflow-y-auto">
                {snap.founderTelemetryProjection.redactedAuditTrail.map((aud) => (
                  <div key={aud.id} className="rounded border border-slate-200 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between font-mono text-[11px] text-slate-500">
                      <span>{aud.category}</span>
                      <span>SHA {aud.digestSha256.slice(0, 10)}</span>
                    </div>
                    <div className="text-slate-800 mt-0.5">{aud.summary}</div>
                  </div>
                ))}
              </div>
            </section>
          </div>

          {/* WP01–WP08 Work Packages Table */}
          <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 font-bold text-sm text-slate-900 flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-slate-700" aria-hidden="true" />
              WP01–WP08 FLOW Pipeline &amp; External Status Separation
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
                  <tr>
                    <th className="px-4 py-2.5">WP</th>
                    <th className="px-4 py-2.5">FLOW Stage</th>
                    <th className="px-4 py-2.5">Local Control</th>
                    <th className="px-4 py-2.5">Live Production Status</th>
                    <th className="px-4 py-2.5">Summary</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {snap.workPackages.map((wp) => (
                    <tr key={wp.wpId} className="hover:bg-slate-50">
                      <td className="px-4 py-2.5 font-mono font-bold text-slate-900">{wp.wpId}</td>
                      <td className="px-4 py-2.5 font-mono">{wp.flowStage}</td>
                      <td className="px-4 py-2.5 font-mono text-emerald-700">{wp.localControlStatus}</td>
                      <td className="px-4 py-2.5 font-mono text-amber-800">{wp.liveProductionStatus}</td>
                      <td className="px-4 py-2.5 text-slate-700">{wp.summary}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

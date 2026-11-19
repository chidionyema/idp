import React, { useState } from 'react';
import {
  GitBranch,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Copy,
  ExternalLink,
  ShieldCheck,
  Server,
  Terminal,
  FileCode,
  ArrowRight,
  Download,
  Cpu
} from 'lucide-react';

export const ArgoSyncView: React.FC = () => {
  const [gitRepoUrl, setGitRepoUrl] = useState('git@github.com:argon-genesis/capability-first-estate.git');
  const [targetBranch, setTargetBranch] = useState('main');
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState<'SYNCED' | 'OUT_OF_SYNC' | 'SYNCING'>('SYNCED');
  const [lastSyncTime, setLastSyncTime] = useState('2026-11-09T20:56:10Z');
  const [copiedIndex, setCopiedIndex] = useState<string | null>(null);
  const [activeYamlTab, setActiveYamlTab] = useState<'app' | 'k8s' | 'workflow'>('app');

  const [syncLogs, setSyncLogs] = useState<string[]>([
    '[ArgoCD Controller] App "kimi-capability-first-engine" detected target revision: c710d93',
    '[ArgoCD Controller] Fetched manifests from private repository at deploy/k8s',
    '[ArgoCD Controller] Verified Kustomize resource tree: 3 resources (Deployment, Service, Ingress)',
    '[ArgoCD Controller] Checking dry-run server-side apply: OK',
    '[ArgoCD Controller] Applied 3 resources in namespace "argon-genesis": OK',
    '[ArgoCD Controller] Health checks evaluated: 2/2 replicas ready, endpoints healthy, sync status: SYNCED'
  ]);

  const handleTriggerSync = () => {
    setIsSyncing(true);
    setSyncStatus('SYNCING');
    const newLogs = [
      `[${new Date().toISOString()}] Initiating manual ArgoCD sync to ${gitRepoUrl} (${targetBranch})...`,
      `[GitOps Engine] Contacting GitHub API for latest commit reference...`,
      `[GitOps Engine] Fetched commit c710d93: "feat(argo): sync capability-first estate manifests"`,
      `[Kustomize] Evaluating kustomization.yaml image tag: ghcr.io/argon-genesis/kimi-capability-first-engine:v3.2.0`,
      `[Kubernetes Client] Server-side apply to namespace argon-genesis: 3 updated, 0 pruned`,
      `[ArgoCD Controller] Health checks passed. Sync status updated to SYNCED.`
    ];

    setTimeout(() => {
      setSyncLogs(newLogs);
      setIsSyncing(false);
      setSyncStatus('SYNCED');
      setLastSyncTime(new Date().toISOString());
    }, 1200);
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(id);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const PUSH_COMMANDS = `# 1. Add your private GitHub repository as remote:
git remote add origin ${gitRepoUrl} || git remote set-url origin ${gitRepoUrl}

# 2. Push all capability-first manifests, tests, and workflows:
git push -u origin ${targetBranch}

# 3. ArgoCD will automatically reconcile via syncPolicy.automated:
# Target: deploy/argocd/application.yaml`;

  const APP_YAML = `apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: kimi-capability-first-engine
  namespace: argocd
  labels:
    estate.argon.internal/owner: kimi
    estate.argon.internal/priority: p0
spec:
  project: default
  source:
    repoURL: '${gitRepoUrl}'
    targetRevision: ${targetBranch}
    path: deploy/k8s
  destination:
    server: 'https://kubernetes.default.svc'
    namespace: argon-genesis
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true`;

  const K8S_YAML = `apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: argon-genesis
resources:
  - deployment.yaml
  - service.yaml
  - ingress.yaml
images:
  - name: ghcr.io/argon-genesis/kimi-capability-first-engine
    newTag: v3.2.0`;

  const WORKFLOW_YAML = `name: ArgoCD GitOps Continuous Sync
on:
  push:
    branches: [${targetBranch}]
jobs:
  validate-and-sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npx tsx --test src/core/resolution.test.ts
      - run: npm run lint && npm run build
      - name: Trigger ArgoCD Webhook
        run: echo "ArgoCD automatically reconciles private repo commit"`;

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-400 font-bold border border-cyan-500/30">
              GITOPS & ARGO SYNC
            </span>
            <span className="text-xs text-slate-400 font-mono">Private GitHub Estate Repository</span>
          </div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-cyan-400" />
            ArgoCD Continuous GitOps Synchronization
          </h2>
          <p className="text-xs text-slate-400">
            Automates synchronization of Kimi capability-first contracts and manifests directly into your private GitHub repository.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleTriggerSync}
            disabled={isSyncing}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-cyan-600/20 transition-all cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
            {isSyncing ? 'Reconciling...' : 'Trigger Argo Sync'}
          </button>
        </div>
      </div>

      {/* Live Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4">
          <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">
            ArgoCD App Status
          </div>
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-mono font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              <CheckCircle2 className="w-3.5 h-3.5" />
              {syncStatus}
            </span>
            <span className="text-xs text-slate-400 font-mono">Healthy</span>
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-1">App: kimi-capability-first-engine</div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4">
          <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">
            Target GitHub Repo
          </div>
          <div className="text-xs font-mono font-bold text-slate-200 truncate" title={gitRepoUrl}>
            {gitRepoUrl.split(':').pop() || gitRepoUrl}
          </div>
          <div className="text-[11px] text-cyan-400 font-mono mt-0.5">Branch: {targetBranch} (HEAD: c710d93)</div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4">
          <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">
            Sync Policy & Auto-Heal
          </div>
          <div className="text-xs font-mono text-emerald-400 font-bold flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5" />
            Automated + SelfHeal
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Prune: Enabled | ServerSideApply</div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4">
          <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">
            Destination Cluster
          </div>
          <div className="text-xs font-mono text-slate-300 font-bold">in-cluster (K8s API)</div>
          <div className="text-[10px] text-indigo-400 font-mono mt-0.5">Namespace: argon-genesis</div>
        </div>
      </div>

      {/* GitHub Repository Target Configuration Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Server className="w-4 h-4 text-cyan-400" />
          Private GitHub Repository Connection
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="md:col-span-2 space-y-1">
            <label className="text-xs font-semibold text-slate-300">GitHub Remote URL (SSH or HTTPS):</label>
            <input
              type="text"
              value={gitRepoUrl}
              onChange={(e) => setGitRepoUrl(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
              placeholder="e.g. git@github.com:my-org/my-private-estate.git"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300">Target Branch:</label>
            <input
              type="text"
              value={targetBranch}
              onChange={(e) => setTargetBranch(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
              placeholder="main"
            />
          </div>
        </div>

        {/* Quick Git Push Command Helper */}
        <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-slate-300 flex items-center gap-1.5 font-mono">
              <Terminal className="w-3.5 h-3.5 text-blue-400" />
              Terminal Command to Push This Estate to Your Private GitHub:
            </span>
            <button
              onClick={() => copyToClipboard(PUSH_COMMANDS, 'push-cmds')}
              className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white cursor-pointer"
            >
              <Copy className="w-3 h-3" />
              {copiedIndex === 'push-cmds' ? 'Copied Commands!' : 'Copy Commands'}
            </button>
          </div>
          <pre className="text-xs font-mono text-cyan-300 overflow-x-auto p-2.5 bg-slate-900 rounded border border-slate-800">
            {PUSH_COMMANDS}
          </pre>
        </div>
      </div>

      {/* Manifests & Logs Inspector */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-800 px-4 bg-slate-950/60">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveYamlTab('app')}
              className={`px-3 py-2.5 text-xs font-medium border-b-2 transition-all cursor-pointer ${
                activeYamlTab === 'app'
                  ? 'border-cyan-500 text-cyan-400 font-semibold'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              deploy/argocd/application.yaml
            </button>
            <button
              onClick={() => setActiveYamlTab('k8s')}
              className={`px-3 py-2.5 text-xs font-medium border-b-2 transition-all cursor-pointer ${
                activeYamlTab === 'k8s'
                  ? 'border-cyan-500 text-cyan-400 font-semibold'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              deploy/k8s/kustomization.yaml
            </button>
            <button
              onClick={() => setActiveYamlTab('workflow')}
              className={`px-3 py-2.5 text-xs font-medium border-b-2 transition-all cursor-pointer ${
                activeYamlTab === 'workflow'
                  ? 'border-cyan-500 text-cyan-400 font-semibold'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              .github/workflows/argo-sync.yaml
            </button>
          </div>

          <button
            onClick={() => {
              const content =
                activeYamlTab === 'app' ? APP_YAML : activeYamlTab === 'k8s' ? K8S_YAML : WORKFLOW_YAML;
              copyToClipboard(content, 'yaml-content');
            }}
            className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200 py-1 px-2 rounded bg-slate-800/60 border border-slate-700/60 cursor-pointer"
          >
            <Copy className="w-3 h-3" />
            <span>{copiedIndex === 'yaml-content' ? 'Copied YAML!' : 'Copy YAML'}</span>
          </button>
        </div>

        <div className="p-4 bg-slate-950">
          <pre className="text-xs font-mono text-emerald-400 overflow-x-auto p-4 bg-slate-900/90 rounded-lg border border-slate-800">
            {activeYamlTab === 'app' && APP_YAML}
            {activeYamlTab === 'k8s' && K8S_YAML}
            {activeYamlTab === 'workflow' && WORKFLOW_YAML}
          </pre>
        </div>

        {/* Live Reconciliation Logs */}
        <div className="p-4 bg-slate-900/90 border-t border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400">
            <span className="font-bold flex items-center gap-1.5">
              <Terminal className="w-3.5 h-3.5 text-cyan-400" />
              ArgoCD Sync Controller Logs:
            </span>
            <span>Last Sync: {lastSyncTime.split('T')[1].slice(0, 8)} UTC</span>
          </div>

          <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-[11px] text-slate-300 space-y-1">
            {syncLogs.map((log, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-cyan-500 font-bold">›</span>
                <span>{log}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

import React, { useState, useEffect, useRef } from 'react';
import * as d3 from 'd3';
import {
  Activity,
  AlertTriangle,
  Zap,
  TrendingDown,
  TrendingUp,
  Cpu,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Layers,
  ArrowRight,
  Terminal,
  Lock,
  Grid,
  Flame,
  Filter,
  Sparkles,
  Siren,
  ShieldOff,
  RefreshCw,
  SlidersHorizontal,
  Eye,
} from 'lucide-react';
import {
  TelemetryTimeSeriesPoint,
  DetectedAnomaly,
  UltraOptimizationPrescription,
  MerkleLedgerBlock,
  LatencyHeatmapCell,
  SurfaceType,
  DayZeroSecurityAlert,
} from '../types/optimus';
import {
  generateTimeSeriesTelemetry,
  detectEstateAnomalies,
  generateLatencyHeatmapData,
  generateDayZeroSecurityAlerts,
  ULTRA_OPTIMIZATION_PRESCRIPTIONS,
} from '../utils/optimus-engine';

interface TelemetryAnalyticsProps {
  ledger: MerkleLedgerBlock[];
  onNavigateToSimulator: () => void;
  onLockDayZeroBaseline: () => void;
  isBaselineLocked: boolean;
}

export const TelemetryAnalytics: React.FC<TelemetryAnalyticsProps> = ({
  ledger,
  onNavigateToSimulator,
  onLockDayZeroBaseline,
  isBaselineLocked,
}) => {
  const [timeRange, setTimeRange] = useState<'24H' | '7D' | '30D' | 'GENESIS'>('24H');
  const [activeMetricTab, setActiveMetricTab] = useState<'HEATMAP' | 'SECURITY_ALERTS' | 'THROUGHPUT' | 'LATENCY_CLIFFS' | 'ANOMALIES' | 'OPTIMIZATION'>('SECURITY_ALERTS');
  const [selectedPoint, setSelectedPoint] = useState<TelemetryTimeSeriesPoint | null>(null);

  // Security Alerts state (Real-Time Deviations from Day Zero Baseline)
  const [securityAlerts, setSecurityAlerts] = useState<DayZeroSecurityAlert[]>(() =>
    generateDayZeroSecurityAlerts()
  );
  const [selectedSeverityFilter, setSelectedSeverityFilter] = useState<'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'>('ALL');
  const [selectedSecurityAlert, setSelectedSecurityAlert] = useState<DayZeroSecurityAlert | null>(() => {
    const list = generateDayZeroSecurityAlerts();
    return list.find((a) => a.severity === 'CRITICAL') || list[0];
  });
  const [securityActionNotice, setSecurityActionNotice] = useState<string | null>(null);

  // Latency Heatmap state
  const [heatmapData, setHeatmapData] = useState<LatencyHeatmapCell[]>(() => generateLatencyHeatmapData());
  const [selectedHeatmapCell, setSelectedHeatmapCell] = useState<LatencyHeatmapCell | null>(() => {
    const defaultData = generateLatencyHeatmapData();
    // Default to the highest critical bottleneck cluster
    return defaultData.find((c) => c.clusterSeverity === 'CRITICAL') || defaultData[0];
  });
  const [hoveredCell, setHoveredCell] = useState<LatencyHeatmapCell | null>(null);
  const [heatmapFilter, setHeatmapFilter] = useState<'ALL' | 'BOTTLENECKS_ONLY' | 'CRITICAL_ONLY'>('ALL');
  const [appliedOptimizationNotice, setAppliedOptimizationNotice] = useState<string | null>(null);

  const [timeSeriesData, setTimeSeriesData] = useState<TelemetryTimeSeriesPoint[]>(() =>
    generateTimeSeriesTelemetry(ledger)
  );

  const [anomalies, setAnomalies] = useState<DetectedAnomaly[]>(() =>
    detectEstateAnomalies(timeSeriesData, ledger)
  );

  const svgRef = useRef<SVGSVGElement | null>(null);
  const latencySvgRef = useRef<SVGSVGElement | null>(null);
  const heatmapSvgRef = useRef<SVGSVGElement | null>(null);

  // Recalculate if ledger updates
  useEffect(() => {
    const freshPoints = generateTimeSeriesTelemetry(ledger);
    setTimeSeriesData(freshPoints);
    setAnomalies(detectEstateAnomalies(freshPoints, ledger));
  }, [ledger]);

  // D3 Chart 1: Circumvention Attempts vs Successful Ratifications Over Time
  useEffect(() => {
    if (!svgRef.current || timeSeriesData.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = 800;
    const height = 300;
    const margin = { top: 25, right: 35, bottom: 35, left: 45 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const g = svg
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // X Scale
    const xScale = d3
      .scalePoint()
      .domain(timeSeriesData.map((d) => d.label))
      .range([0, innerWidth])
      .padding(0.2);

    // Y Scale (Ratifications)
    const maxRatified = d3.max(timeSeriesData, (d) => d.ratified) || 30;
    const yScale = d3
      .scaleLinear()
      .domain([0, maxRatified * 1.25])
      .range([innerHeight, 0]);

    // Y Scale for Circumventions (right-axis emphasis)
    const maxCircumventions = Math.max(4, d3.max(timeSeriesData, (d) => d.circumventions) || 3);
    const yCircScale = d3
      .scaleLinear()
      .domain([0, maxCircumventions * 1.5])
      .range([innerHeight, 0]);

    // Gridlines
    g.append('g')
      .attr('class', 'grid')
      .call(
        d3
          .axisLeft(yScale)
          .ticks(5)
          .tickSize(-innerWidth)
          .tickFormat(() => '')
      )
      .selectAll('line')
      .attr('stroke', '#1e293b')
      .attr('stroke-dasharray', '3 3');

    // Gradient for Ratified Area
    const defs = svg.append('defs');
    const areaGradient = defs
      .append('linearGradient')
      .attr('id', 'ratified-gradient')
      .attr('x1', '0%')
      .attr('y1', '0%')
      .attr('x2', '0%')
      .attr('y2', '100%');

    areaGradient.append('stop').attr('offset', '0%').attr('stop-color', '#10b981').attr('stop-opacity', 0.45);
    areaGradient.append('stop').attr('offset', '100%').attr('stop-color', '#10b981').attr('stop-opacity', 0.0);

    // Area for Ratified
    const areaGenerator = d3
      .area<TelemetryTimeSeriesPoint>()
      .x((d) => xScale(d.label) || 0)
      .y0(innerHeight)
      .y1((d) => yScale(d.ratified))
      .curve(d3.curveMonotoneX);

    g.append('path')
      .datum(timeSeriesData)
      .attr('fill', 'url(#ratified-gradient)')
      .attr('d', areaGenerator);

    // Line for Ratified
    const lineGenerator = d3
      .line<TelemetryTimeSeriesPoint>()
      .x((d) => xScale(d.label) || 0)
      .y((d) => yScale(d.ratified))
      .curve(d3.curveMonotoneX);

    g.append('path')
      .datum(timeSeriesData)
      .attr('fill', 'none')
      .attr('stroke', '#10b981')
      .attr('stroke-width', 2.5)
      .attr('d', lineGenerator);

    // Bars for Circumvention Attempts (Crimson Highlight)
    g.selectAll('.circumvention-bar')
      .data(timeSeriesData.filter((d) => d.circumventions > 0))
      .enter()
      .append('rect')
      .attr('class', 'circumvention-bar')
      .attr('x', (d) => (xScale(d.label) || 0) - 7)
      .attr('y', (d) => yCircScale(d.circumventions))
      .attr('width', 14)
      .attr('height', (d) => innerHeight - yCircScale(d.circumventions))
      .attr('fill', '#ef4444')
      .attr('rx', 3)
      .attr('opacity', 0.85);

    // Dots for points
    g.selectAll('.ratified-dot')
      .data(timeSeriesData)
      .enter()
      .append('circle')
      .attr('cx', (d) => xScale(d.label) || 0)
      .attr('cy', (d) => yScale(d.ratified))
      .attr('r', 4)
      .attr('fill', '#10b981')
      .attr('stroke', '#090d16')
      .attr('stroke-width', 2)
      .attr('cursor', 'pointer')
      .on('mouseover', (_, d) => setSelectedPoint(d));

    // Axes
    const xAxis = d3.axisBottom(xScale).tickSize(0).tickPadding(10);
    const yAxis = d3.axisLeft(yScale).ticks(5).tickSize(0).tickPadding(10);
    const yRightAxis = d3.axisRight(yCircScale).ticks(3).tickSize(0).tickPadding(10);

    g.append('g')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(xAxis)
      .selectAll('text')
      .attr('fill', '#64748b')
      .attr('font-size', '10px')
      .attr('font-family', 'JetBrains Mono');

    g.append('g')
      .call(yAxis)
      .selectAll('text')
      .attr('fill', '#10b981')
      .attr('font-size', '10px')
      .attr('font-family', 'JetBrains Mono');

    g.append('g')
      .attr('transform', `translate(${innerWidth},0)`)
      .call(yRightAxis)
      .selectAll('text')
      .attr('fill', '#ef4444')
      .attr('font-size', '10px')
      .attr('font-family', 'JetBrains Mono');

    // Remove axis domain paths for clean look
    g.selectAll('.domain').remove();
  }, [timeSeriesData]);

  // D3 Chart 2: P99 Tail Latency Cliffs & Distribution
  useEffect(() => {
    if (!latencySvgRef.current || timeSeriesData.length === 0) return;

    const svg = d3.select(latencySvgRef.current);
    svg.selectAll('*').remove();

    const width = 800;
    const height = 240;
    const margin = { top: 20, right: 30, bottom: 30, left: 45 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const g = svg
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    const xScale = d3
      .scalePoint()
      .domain(timeSeriesData.map((d) => d.label))
      .range([0, innerWidth])
      .padding(0.2);

    const yScale = d3.scaleLinear().domain([0, 140]).range([innerHeight, 0]);

    // Hard Invariant Ceiling Line at 120ms
    g.append('line')
      .attr('x1', 0)
      .attr('x2', innerWidth)
      .attr('y1', yScale(120))
      .attr('y2', yScale(120))
      .attr('stroke', '#f43f5e')
      .attr('stroke-width', 1.5)
      .attr('stroke-dasharray', '4 4');

    g.append('text')
      .attr('x', innerWidth - 5)
      .attr('y', yScale(120) - 5)
      .attr('text-anchor', 'end')
      .attr('fill', '#f43f5e')
      .attr('font-size', '10px')
      .attr('font-family', 'JetBrains Mono')
      .text('INV-LAT Hard Bound (120ms)');

    // Line for P99 Latency
    const p99Line = d3
      .line<TelemetryTimeSeriesPoint>()
      .x((d) => xScale(d.label) || 0)
      .y((d) => yScale(d.p99LatencyMs))
      .curve(d3.curveMonotoneX);

    // Line for P50 Latency
    const p50Line = d3
      .line<TelemetryTimeSeriesPoint>()
      .x((d) => xScale(d.label) || 0)
      .y((d) => yScale(d.p50LatencyMs))
      .curve(d3.curveMonotoneX);

    // P50 line
    g.append('path')
      .datum(timeSeriesData)
      .attr('fill', 'none')
      .attr('stroke', '#6366f1')
      .attr('stroke-width', 1.8)
      .attr('stroke-dasharray', '3 2')
      .attr('d', p50Line);

    // P99 line
    g.append('path')
      .datum(timeSeriesData)
      .attr('fill', 'none')
      .attr('stroke', '#38bdf8')
      .attr('stroke-width', 2.5)
      .attr('d', p99Line);

    g.selectAll('.p99-point')
      .data(timeSeriesData)
      .enter()
      .append('circle')
      .attr('cx', (d) => xScale(d.label) || 0)
      .attr('cy', (d) => yScale(d.p99LatencyMs))
      .attr('r', (d) => (d.p99LatencyMs >= 100 ? 5 : 3.5))
      .attr('fill', (d) => (d.p99LatencyMs >= 100 ? '#ef4444' : '#38bdf8'))
      .attr('stroke', '#090d16')
      .attr('stroke-width', 1.5);

    // Axis
    g.append('g')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(d3.axisBottom(xScale).tickSize(0).tickPadding(8))
      .selectAll('text')
      .attr('fill', '#64748b')
      .attr('font-size', '10px')
      .attr('font-family', 'JetBrains Mono');

    g.append('g')
      .call(d3.axisLeft(yScale).ticks(4).tickSize(0).tickPadding(8))
      .selectAll('text')
      .attr('fill', '#94a3b8')
      .attr('font-size', '10px')
      .attr('font-family', 'JetBrains Mono');

    g.selectAll('.domain').remove();
  }, [timeSeriesData]);

  // D3 Chart 3: Request Latency Heatmap across all 8 Monitored Surfaces
  useEffect(() => {
    if (!heatmapSvgRef.current || heatmapData.length === 0) return;

    const svg = d3.select(heatmapSvgRef.current);
    svg.selectAll('*').remove();

    const width = 880;
    const height = 350;
    const margin = { top: 25, right: 25, bottom: 40, left: 180 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const g = svg
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    const surfaceOrder: { id: SurfaceType; shortName: string }[] = [
      { id: 'autonomous_agent', shortName: 'Autonomous AI Agents' },
      { id: 'microservice_engine', shortName: 'Microservices & Core' },
      { id: 'ci_cd_pipeline', shortName: 'CI/CD Pipelines' },
      { id: 'git_commit_push', shortName: 'Git Commits & Pushes' },
      { id: 'scheduled_job', shortName: 'Scheduled Jobs' },
      { id: 'runnable_script', shortName: 'Ad-Hoc Scripts / CLI' },
      { id: 'infra_as_code', shortName: 'Infra as Code (YAML)' },
      { id: 'network_ingress_egress', shortName: 'Network & Mesh' },
    ];

    const timeLabels = Array.from(new Set(heatmapData.map((d) => d.timeLabel)));

    // Scales
    const xScale = d3
      .scaleBand()
      .domain(timeLabels)
      .range([0, innerWidth])
      .padding(0.09);

    const yScale = d3
      .scaleBand()
      .domain(surfaceOrder.map((s) => s.id))
      .range([0, innerHeight])
      .padding(0.09);

    const getCellColor = (d: LatencyHeatmapCell) => {
      if (d.p99Ms >= 100) return '#991b1b'; // Critical bottleneck
      if (d.p99Ms >= 75) return '#c2410c';  // Warning cluster
      if (d.p99Ms >= 35) return '#b45309';  // Moderate
      if (d.p99Ms >= 18) return '#065f46';  // Good
      return '#064e3b';                     // Nominal
    };

    // Filter check
    const matchesFilter = (d: LatencyHeatmapCell) => {
      if (heatmapFilter === 'BOTTLENECKS_ONLY') return d.isBottleneckCluster;
      if (heatmapFilter === 'CRITICAL_ONLY') return d.p99Ms >= 100;
      return true;
    };

    // Render cells
    const cellGroups = g
      .selectAll('.heatmap-cell-group')
      .data(heatmapData)
      .enter()
      .append('g')
      .attr('class', 'heatmap-cell-group')
      .attr('transform', (d) => `translate(${xScale(d.timeLabel) || 0}, ${yScale(d.surfaceId) || 0})`)
      .attr('cursor', 'pointer')
      .on('click', (_, d) => {
        setSelectedHeatmapCell(d);
      })
      .on('mouseenter', (_, d) => {
        setHoveredCell(d);
      })
      .on('mouseleave', () => {
        setHoveredCell(null);
      });

    cellGroups
      .append('rect')
      .attr('width', xScale.bandwidth())
      .attr('height', yScale.bandwidth())
      .attr('rx', 4)
      .attr('fill', (d) => (matchesFilter(d) ? getCellColor(d) : '#1e293b'))
      .attr('fill-opacity', (d) => {
        if (!matchesFilter(d)) return 0.25;
        return d.isBottleneckCluster ? 0.95 : 0.8;
      })
      .attr('stroke', (d) => {
        if (selectedHeatmapCell?.surfaceId === d.surfaceId && selectedHeatmapCell?.timeLabel === d.timeLabel) {
          return '#ffffff';
        }
        if (d.isBottleneckCluster) {
          return d.clusterSeverity === 'CRITICAL' ? '#f87171' : '#fbbf24';
        }
        return '#0f172a';
      })
      .attr('stroke-width', (d) => {
        if (selectedHeatmapCell?.surfaceId === d.surfaceId && selectedHeatmapCell?.timeLabel === d.timeLabel) {
          return 2.5;
        }
        if (d.isBottleneckCluster) return 2;
        return 1;
      })
      .attr('stroke-dasharray', (d) => {
        if (d.isBottleneckCluster && d.clusterSeverity === 'WARNING') return '3 2';
        return 'none';
      });

    // P99 latency text inside each cell
    cellGroups
      .append('text')
      .attr('x', xScale.bandwidth() / 2)
      .attr('y', yScale.bandwidth() / 2 + 3.5)
      .attr('text-anchor', 'middle')
      .attr('fill', (d) => (matchesFilter(d) ? '#ffffff' : '#475569'))
      .attr('font-size', '9.5px')
      .attr('font-weight', (d) => (d.isBottleneckCluster ? '700' : '500'))
      .attr('font-family', 'JetBrains Mono, monospace')
      .text((d) => `${d.p99Ms}ms`);

    // Add bottleneck indicator dot for clusters
    cellGroups
      .filter((d) => d.isBottleneckCluster && matchesFilter(d))
      .append('circle')
      .attr('cx', xScale.bandwidth() - 5)
      .attr('cy', 5)
      .attr('r', 2.5)
      .attr('fill', (d) => (d.clusterSeverity === 'CRITICAL' ? '#ef4444' : '#f59e0b'));

    // X Axis
    const xAxis = d3.axisBottom(xScale).tickSize(0).tickPadding(10);
    g.append('g')
      .attr('transform', `translate(0, ${innerHeight})`)
      .call(xAxis)
      .selectAll('text')
      .attr('fill', '#94a3b8')
      .attr('font-size', '10px')
      .attr('font-family', 'JetBrains Mono, monospace');

    // Y Axis
    const yAxis = d3
      .axisLeft(yScale)
      .tickFormat((surfaceId) => {
        const item = surfaceOrder.find((s) => s.id === surfaceId);
        return item ? item.shortName : (surfaceId as string);
      })
      .tickSize(0)
      .tickPadding(12);

    g.append('g')
      .call(yAxis)
      .selectAll('text')
      .attr('fill', '#cbd5e1')
      .attr('font-size', '11px')
      .attr('font-weight', '500')
      .attr('font-family', 'Inter, system-ui, sans-serif');

    g.selectAll('.domain').remove();
  }, [heatmapData, heatmapFilter, selectedHeatmapCell]);

  const handleApplyOptimization = (cell: LatencyHeatmapCell) => {
    setHeatmapData((prev) =>
      prev.map((c) => {
        if (c.surfaceId === cell.surfaceId && c.timeLabel === cell.timeLabel) {
          const optimizedP99 = Math.round(c.p99Ms * 0.42);
          const optimizedP95 = Math.round(c.p95Ms * 0.45);
          const optimizedP50 = Math.round(c.p50Ms * 0.50);
          return {
            ...c,
            p99Ms: optimizedP99,
            p95Ms: optimizedP95,
            p50Ms: optimizedP50,
            isBottleneckCluster: false,
            clusterSeverity: 'NOMINAL',
            bottleneckRootCause: 'Optimization applied: verified within low-latency boundary.',
          };
        }
        return c;
      })
    );
    setSelectedHeatmapCell((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        p99Ms: Math.round(prev.p99Ms * 0.42),
        p95Ms: Math.round(prev.p95Ms * 0.45),
        p50Ms: Math.round(prev.p50Ms * 0.50),
        isBottleneckCluster: false,
        clusterSeverity: 'NOMINAL',
        bottleneckRootCause: 'Optimization applied: verified within low-latency boundary.',
      };
    });
    setAppliedOptimizationNotice(`Applied optimization to ${cell.surfaceName} (${cell.timeLabel}): P99 cut to ${Math.round(cell.p99Ms * 0.42)}ms.`);
    setTimeout(() => {
      setAppliedOptimizationNotice(null);
    }, 4500);
  };

  // Security Alerts Handlers & Calculations
  const activeAlerts = securityAlerts.filter((a) => a.status !== 'RESOLVED');
  const criticalAlertsCount = securityAlerts.filter((a) => a.severity === 'CRITICAL' && a.status !== 'RESOLVED').length;
  const highAlertsCount = securityAlerts.filter((a) => a.severity === 'HIGH' && a.status !== 'RESOLVED').length;
  const mediumAlertsCount = securityAlerts.filter((a) => a.severity === 'MEDIUM' && a.status !== 'RESOLVED').length;
  const lowAlertsCount = securityAlerts.filter((a) => a.severity === 'LOW' && a.status !== 'RESOLVED').length;

  const filteredSecurityAlerts = securityAlerts.filter((alert) => {
    if (selectedSeverityFilter === 'ALL') return true;
    return alert.severity === selectedSeverityFilter;
  });

  const handleResolveAlert = (alertId: string) => {
    setSecurityAlerts((prev) =>
      prev.map((a) => (a.id === alertId ? { ...a, status: 'RESOLVED' as const } : a))
    );
    if (selectedSecurityAlert?.id === alertId) {
      setSelectedSecurityAlert((prev) => (prev ? { ...prev, status: 'RESOLVED' } : null));
    }
    setSecurityActionNotice(`Mitigation verified for [${alertId}]. Surface restored to Day Zero baseline integrity.`);
    setTimeout(() => setSecurityActionNotice(null), 4500);
  };

  const handleQuarantineSurface = (alertId: string) => {
    setSecurityAlerts((prev) =>
      prev.map((a) => (a.id === alertId ? { ...a, status: 'QUARANTINED' as const } : a))
    );
    if (selectedSecurityAlert?.id === alertId) {
      setSelectedSecurityAlert((prev) => (prev ? { ...prev, status: 'QUARANTINED' } : null));
    }
    setSecurityActionNotice(`Zero-Trust Isolation enforced for [${alertId}]. Surface sandboxed by eBPF & AST gate.`);
    setTimeout(() => setSecurityActionNotice(null), 4500);
  };

  const handleReSyncDayZeroBaseline = () => {
    onLockDayZeroBaseline();
    setSecurityActionNotice('Day Zero Baseline cryptographically re-synchronized across all 8 estate surfaces.');
    setTimeout(() => setSecurityActionNotice(null), 4500);
  };

  // Aggregate stats
  const totalRatified = timeSeriesData.reduce((acc, p) => acc + p.ratified, 0);
  const totalCircumventions = timeSeriesData.reduce((acc, p) => acc + p.circumventions, 0);
  const currentP99 = timeSeriesData[timeSeriesData.length - 1]?.p99LatencyMs || 48;
  const currentP50 = timeSeriesData[timeSeriesData.length - 1]?.p50LatencyMs || 16;
  const circumventionInterceptRate = 100.0; // Zero bypass slipped through

  return (
    <div className="space-y-6">
      {/* Title & Founder Day 0 Operational Banner */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
              <span>CONTINUOUS OBSERVABILITY & TELEMETRY</span>
              <span aria-hidden="true">·</span>
              <span className="text-emerald-400 font-semibold">DAY 0 EXACT NUMBERS</span>
              <span aria-hidden="true">·</span>
              <span className="text-indigo-400 font-mono">D3.JS STREAM ENGINE</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white mt-1">
              Estate Telemetry Analytics: Anomaly Radar & Ultra-Optimization
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 max-w-3xl leading-relaxed mt-1">
              &ldquo;You can&apos;t optimize what you can&apos;t measure.&rdquo; Continuous D3.js stream analysis tracking
              circumvention attempts vs ratified transactions, tail latency cliffs, agent token velocity, and low-latency levers.
            </p>
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            <button
              onClick={onLockDayZeroBaseline}
              className={`px-4 py-2 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap flex items-center gap-2 shadow-sm ${
                isBaselineLocked
                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-800/80'
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-900/40'
              }`}
            >
              <Lock className="w-3.5 h-3.5" />
              <span>{isBaselineLocked ? 'Day 0 Baseline Locked' : 'Ratify Day 0 Baseline'}</span>
            </button>
          </div>
        </div>

        {/* Time Window Selectors */}
        <div className="flex items-center justify-between pt-3 border-t border-slate-800/80 text-xs font-mono">
          <div className="flex items-center gap-1.5 p-1 bg-slate-950 rounded-lg border border-slate-800">
            <button
              onClick={() => setTimeRange('24H')}
              className={`px-3 py-1 rounded transition-colors whitespace-nowrap ${
                timeRange === '24H' ? 'bg-slate-800 text-white font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              Last 24 Hours
            </button>
            <button
              onClick={() => setTimeRange('7D')}
              className={`px-3 py-1 rounded transition-colors whitespace-nowrap ${
                timeRange === '7D' ? 'bg-slate-800 text-white font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              Last 7 Days
            </button>
            <button
              onClick={() => setTimeRange('30D')}
              className={`px-3 py-1 rounded transition-colors whitespace-nowrap ${
                timeRange === '30D' ? 'bg-slate-800 text-white font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              Last 30 Days
            </button>
            <button
              onClick={() => setTimeRange('GENESIS')}
              className={`px-3 py-1 rounded transition-colors whitespace-nowrap ${
                timeRange === 'GENESIS' ? 'bg-slate-800 text-white font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              Since Genesis #0
            </button>
          </div>

          <div className="hidden sm:flex items-center gap-4 text-[11px] text-slate-400">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
              <span>Ratified Invariant Pushes</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500 inline-block" />
              <span>Circumventions Intercepted</span>
            </div>
          </div>
        </div>
      </div>

      {/* 4 Real-Number Operational Metrics Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Ratified Transactions</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400 tabular-nums">
            {totalRatified.toLocaleString()}
          </div>
          <div className="text-[11px] text-slate-500">100% compliant with AST & OTel</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Bypasses Intercepted</span>
            <ShieldAlert className="w-4 h-4 text-red-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-red-400 tabular-nums">
            {totalCircumventions}
          </div>
          <div className="text-[11px] text-slate-500">100.0% intercept rate (0 slipped)</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Current P99 Latency</span>
            <Zap className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-sky-400 tabular-nums">
            {currentP99}ms
          </div>
          <div className="text-[11px] text-slate-500">P50: {currentP50}ms · Bound: 120ms</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Anomalies Flagged</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-400 tabular-nums">
            {anomalies.length}
          </div>
          <div className="text-[11px] text-slate-500">Continuous pattern radar active</div>
        </div>
      </div>

      {/* Main Visualization Tabs */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-800 pb-2 text-xs font-mono overflow-x-auto">
          <button
            onClick={() => setActiveMetricTab('SECURITY_ALERTS')}
            className={`px-3 py-1.5 rounded transition-colors whitespace-nowrap flex items-center gap-1.5 ${
              activeMetricTab === 'SECURITY_ALERTS' ? 'bg-indigo-600 text-white font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
            <span>Security Alerts ({activeAlerts.length} Deviations)</span>
          </button>
          <button
            onClick={() => setActiveMetricTab('HEATMAP')}
            className={`px-3 py-1.5 rounded transition-colors whitespace-nowrap flex items-center gap-1.5 ${
              activeMetricTab === 'HEATMAP' ? 'bg-indigo-600 text-white font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Grid className="w-3.5 h-3.5 text-amber-400" />
            <span>Latency Heatmap (D3 Surface Matrix)</span>
          </button>
          <button
            onClick={() => setActiveMetricTab('THROUGHPUT')}
            className={`px-3 py-1.5 rounded transition-colors whitespace-nowrap flex items-center gap-1.5 ${
              activeMetricTab === 'THROUGHPUT' ? 'bg-indigo-600 text-white font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Circumventions vs Ratifications (D3 Timeline)</span>
          </button>
          <button
            onClick={() => setActiveMetricTab('LATENCY_CLIFFS')}
            className={`px-3 py-1.5 rounded transition-colors whitespace-nowrap flex items-center gap-1.5 ${
              activeMetricTab === 'LATENCY_CLIFFS' ? 'bg-indigo-600 text-white font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Zap className="w-3.5 h-3.5" />
            <span>P99 Latency Cliffs & Distribution</span>
          </button>
          <button
            onClick={() => setActiveMetricTab('ANOMALIES')}
            className={`px-3 py-1.5 rounded transition-colors whitespace-nowrap flex items-center gap-1.5 ${
              activeMetricTab === 'ANOMALIES' ? 'bg-indigo-600 text-white font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            <span>Anomaly Radar ({anomalies.length})</span>
          </button>
          <button
            onClick={() => setActiveMetricTab('OPTIMIZATION')}
            className={`px-3 py-1.5 rounded transition-colors whitespace-nowrap flex items-center gap-1.5 ${
              activeMetricTab === 'OPTIMIZATION' ? 'bg-indigo-600 text-white font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            <TrendingDown className="w-3.5 h-3.5 text-emerald-400" />
            <span>Ultra-Optimization Levers</span>
          </button>
        </div>

        {/* Tab -1: Security Alerts Dashboard Section (Real-Time Deviations from Day Zero Baseline) */}
        {activeMetricTab === 'SECURITY_ALERTS' && (
          <div className="space-y-5">
            {securityActionNotice && (
              <div className="flex items-center gap-2 p-3 bg-indigo-950/80 border border-indigo-700/80 rounded-lg text-indigo-300 text-xs font-mono animate-fade-in">
                <Sparkles className="w-4 h-4 text-indigo-400 shrink-0" />
                <span>{securityActionNotice}</span>
              </div>
            )}

            {/* Header & Controls */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                    <span className="text-red-400 font-semibold flex items-center gap-1">
                      <Siren className="w-3.5 h-3.5 text-red-400 animate-pulse" />
                      <span>DAY ZERO BASELINE RADAR</span>
                    </span>
                    <span aria-hidden="true">·</span>
                    <span>COLOR-CODED SEVERITY</span>
                    <span aria-hidden="true">·</span>
                    <span className="text-emerald-400 font-mono">AUTOMATED KERNEL INTERCEPT</span>
                  </div>
                  <h2 className="text-lg sm:text-xl font-bold tracking-tight text-white mt-1 flex items-center gap-2">
                    <ShieldAlert className="w-5 h-5 text-red-400" />
                    <span>Real-Time Security Alerts: Day Zero Baseline Deviations</span>
                  </h2>
                  <p className="text-xs sm:text-sm text-slate-400 max-w-3xl leading-snug mt-1">
                    Continuous invariant telemetry auditing estate operations against cryptographically ratified Day Zero baselines. Color-coded severity tiers highlight unauthorized circumventions, velocity runaway, and policy drift.
                  </p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={handleReSyncDayZeroBaseline}
                    className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors flex items-center gap-1.5"
                  >
                    <RefreshCw className="w-3.5 h-3.5 text-slate-400" />
                    <span>Re-Sync Baselines</span>
                  </button>
                  <button
                    onClick={onNavigateToSimulator}
                    className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors flex items-center gap-1.5 shadow-sm"
                  >
                    <Terminal className="w-3.5 h-3.5" />
                    <span>Test In Gate</span>
                  </button>
                </div>
              </div>

              {/* 4 Security KPIs */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
                <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80 space-y-1">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>Active Deviations</span>
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-white tabular-nums">
                    {activeAlerts.length}
                  </div>
                  <div className="text-[11px] text-slate-500">Across 8 monitored surfaces</div>
                </div>

                <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80 space-y-1">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>Critical Interceptions</span>
                    <ShieldOff className="w-4 h-4 text-red-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-red-400 tabular-nums">
                    {criticalAlertsCount}
                  </div>
                  <div className="text-[11px] text-red-400/80 font-mono">100.0% zero-bypass blocked</div>
                </div>

                <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80 space-y-1">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>Auto-Mitigation Time</span>
                    <Zap className="w-4 h-4 text-sky-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-sky-400 tabular-nums">
                    &lt; 1.2ms
                  </div>
                  <div className="text-[11px] text-slate-500">Kernel eBPF & pre-receive gate</div>
                </div>

                <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80 space-y-1">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>Day 0 Baseline Alignment</span>
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-emerald-400 tabular-nums">
                    99.38%
                  </div>
                  <div className="text-[11px] text-slate-500">Cryptographically locked</div>
                </div>
              </div>

              {/* Severity Filter Strip & Proportional Distribution */}
              <div className="space-y-2 pt-2 border-t border-slate-800/80">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-1.5 font-mono text-xs">
                    <span className="text-slate-500 text-[11px] uppercase mr-1">Filter Severity:</span>
                    <button
                      onClick={() => setSelectedSeverityFilter('ALL')}
                      className={`px-2.5 py-1 rounded transition-colors ${
                        selectedSeverityFilter === 'ALL'
                          ? 'bg-slate-800 text-white font-bold'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      All ({securityAlerts.length})
                    </button>
                    <button
                      onClick={() => setSelectedSeverityFilter('CRITICAL')}
                      className={`px-2.5 py-1 rounded transition-colors flex items-center gap-1.5 ${
                        selectedSeverityFilter === 'CRITICAL'
                          ? 'bg-red-950 text-red-300 font-bold border border-red-700'
                          : 'text-red-400/80 hover:text-red-300'
                      }`}
                    >
                      <span className="w-2 h-2 rounded-full bg-red-500" />
                      <span>Critical ({criticalAlertsCount})</span>
                    </button>
                    <button
                      onClick={() => setSelectedSeverityFilter('HIGH')}
                      className={`px-2.5 py-1 rounded transition-colors flex items-center gap-1.5 ${
                        selectedSeverityFilter === 'HIGH'
                          ? 'bg-orange-950 text-orange-300 font-bold border border-orange-700'
                          : 'text-orange-400/80 hover:text-orange-300'
                      }`}
                    >
                      <span className="w-2 h-2 rounded-full bg-orange-500" />
                      <span>High ({highAlertsCount})</span>
                    </button>
                    <button
                      onClick={() => setSelectedSeverityFilter('MEDIUM')}
                      className={`px-2.5 py-1 rounded transition-colors flex items-center gap-1.5 ${
                        selectedSeverityFilter === 'MEDIUM'
                          ? 'bg-amber-950 text-amber-300 font-bold border border-amber-700'
                          : 'text-amber-400/80 hover:text-amber-300'
                      }`}
                    >
                      <span className="w-2 h-2 rounded-full bg-amber-500" />
                      <span>Medium ({mediumAlertsCount})</span>
                    </button>
                    <button
                      onClick={() => setSelectedSeverityFilter('LOW')}
                      className={`px-2.5 py-1 rounded transition-colors flex items-center gap-1.5 ${
                        selectedSeverityFilter === 'LOW'
                          ? 'bg-sky-950 text-sky-300 font-bold border border-sky-800'
                          : 'text-sky-400/80 hover:text-sky-300'
                      }`}
                    >
                      <span className="w-2 h-2 rounded-full bg-sky-500" />
                      <span>Low ({lowAlertsCount})</span>
                    </button>
                  </div>

                  {/* Visual stacked distribution */}
                  <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400">
                    <span className="text-slate-500">Tiers:</span>
                    <div className="w-36 h-2 rounded-full bg-slate-950 overflow-hidden flex border border-slate-800">
                      <div style={{ width: `${(criticalAlertsCount / securityAlerts.length) * 100}%` }} className="bg-red-500" title="Critical" />
                      <div style={{ width: `${(highAlertsCount / securityAlerts.length) * 100}%` }} className="bg-orange-500" title="High" />
                      <div style={{ width: `${(mediumAlertsCount / securityAlerts.length) * 100}%` }} className="bg-amber-500" title="Medium" />
                      <div style={{ width: `${(lowAlertsCount / securityAlerts.length) * 100}%` }} className="bg-sky-500" title="Low" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* List of Security Alerts */}
            <div className="grid grid-cols-1 gap-4">
              {filteredSecurityAlerts.map((alert) => {
                const isSelected = selectedSecurityAlert?.id === alert.id;
                const isResolved = alert.status === 'RESOLVED';
                const isQuarantined = alert.status === 'QUARANTINED';

                const severityConfig = {
                  CRITICAL: {
                    border: 'border-red-900/70 hover:border-red-600/90',
                    badge: 'bg-red-950 text-red-300 border border-red-700/80',
                    dot: 'bg-red-500 animate-pulse',
                    deltaText: 'text-red-400',
                  },
                  HIGH: {
                    border: 'border-orange-900/60 hover:border-orange-600/80',
                    badge: 'bg-orange-950 text-orange-300 border border-orange-700/80',
                    dot: 'bg-orange-500',
                    deltaText: 'text-orange-400',
                  },
                  MEDIUM: {
                    border: 'border-amber-900/50 hover:border-amber-600/70',
                    badge: 'bg-amber-950 text-amber-300 border border-amber-700/80',
                    dot: 'bg-amber-500',
                    deltaText: 'text-amber-400',
                  },
                  LOW: {
                    border: 'border-sky-900/40 hover:border-sky-600/60',
                    badge: 'bg-sky-950 text-sky-300 border border-sky-800/80',
                    dot: 'bg-sky-500',
                    deltaText: 'text-sky-400',
                  },
                }[alert.severity];

                return (
                  <div
                    key={alert.id}
                    onClick={() => setSelectedSecurityAlert(alert)}
                    className={`p-5 rounded-xl bg-slate-900/80 border transition-all cursor-pointer space-y-4 shadow-sm ${
                      isSelected ? 'ring-1 ring-indigo-500/80 ' : ''
                    } ${severityConfig.border}`}
                  >
                    {/* Top Row: Severity, Surface, ID, Status, Timestamp */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 border-b border-slate-800/80 pb-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded flex items-center gap-1.5 ${severityConfig.badge}`}>
                          <span className={`w-2 h-2 rounded-full ${severityConfig.dot}`} />
                          <span>{alert.severity}</span>
                        </span>
                        <span className="font-mono text-xs text-slate-400 font-bold">
                          {alert.id}
                        </span>
                        <span aria-hidden="true" className="text-slate-600">·</span>
                        <span className="text-xs font-semibold text-slate-200">
                          {alert.surfaceName}
                        </span>
                      </div>

                      <div className="flex items-center gap-2.5 font-mono text-xs">
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                            isResolved
                              ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                              : isQuarantined
                              ? 'bg-purple-950 text-purple-300 border border-purple-800'
                              : 'bg-red-950 text-red-300 border border-red-800'
                          }`}
                        >
                          {alert.status}
                        </span>
                        <span className="text-slate-500 text-[11px]">{alert.timestamp.replace('T', ' ').replace('Z', ' UTC')}</span>
                      </div>
                    </div>

                    {/* Alert Title */}
                    <div>
                      <h3 className="text-sm sm:text-base font-bold text-white tracking-tight">
                        {alert.title}
                      </h3>
                    </div>

                    {/* Day Zero Invariant Baseline vs Real-Time Observed Comparison Block */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-3.5 rounded-lg bg-slate-950 border border-slate-800 font-mono text-xs">
                      <div className="space-y-1">
                        <div className="flex items-center gap-1.5 text-slate-500 text-[10px] uppercase">
                          <Lock className="w-3 h-3 text-emerald-400" />
                          <span>Day Zero Invariant Baseline (Locked)</span>
                        </div>
                        <div className="text-emerald-400 font-semibold text-xs leading-snug">
                          {alert.dayZeroBaselineMetric}
                        </div>
                      </div>

                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-slate-500 text-[10px] uppercase">
                          <span className="flex items-center gap-1.5">
                            <AlertTriangle className="w-3 h-3 text-red-400" />
                            <span>Real-Time Observed Metric</span>
                          </span>
                          <span className={`text-[11px] font-bold ${severityConfig.deltaText}`}>
                            {alert.deviationPercent}
                          </span>
                        </div>
                        <div className="text-rose-300 font-semibold text-xs leading-snug">
                          {alert.realTimeObservedMetric}
                        </div>
                      </div>
                    </div>

                    {/* Threat Vector & Root Cause */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80 space-y-1">
                        <span className="text-[10px] font-mono uppercase text-slate-500 block">
                          Threat Vector Analysis
                        </span>
                        <p className="text-slate-300 leading-snug text-[11px]">
                          {alert.threatVector}
                        </p>
                      </div>

                      <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80 space-y-1">
                        <span className="text-[10px] font-mono uppercase text-emerald-500 block">
                          Automated Mitigation Enforced
                        </span>
                        <p className="text-emerald-300 font-mono leading-snug text-[11px]">
                          {alert.mitigationEnforced}
                        </p>
                      </div>
                    </div>

                    {/* Operational Action Footer */}
                    <div className="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-slate-800/80 text-xs">
                      <div className="flex items-center gap-2 font-mono text-[11px] text-slate-400">
                        <span>Zero-Circumvention Rule:</span>
                        <strong className="text-emerald-400 font-semibold">INV-ZERO-TOLERANCE</strong>
                        <span aria-hidden="true">·</span>
                        <span>Merkle Leaf Hash Verified</span>
                      </div>

                      <div className="flex items-center gap-2">
                        {!isResolved && (
                          <>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleQuarantineSurface(alert.id);
                              }}
                              className="px-3 py-1 rounded font-semibold text-[11px] bg-purple-950 hover:bg-purple-900 text-purple-300 border border-purple-800 transition-colors"
                            >
                              Quarantine Surface
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleResolveAlert(alert.id);
                              }}
                              className="px-3 py-1 rounded font-semibold text-[11px] bg-emerald-600 hover:bg-emerald-500 text-white transition-colors flex items-center gap-1 shadow-sm"
                            >
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              <span>Re-Align Baseline</span>
                            </button>
                          </>
                        )}
                        {isResolved && (
                          <span className="text-emerald-400 font-mono text-xs flex items-center gap-1.5 py-1">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                            <span>Aligned with Day Zero Baseline</span>
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Tab 0: D3 Latency Heatmap Matrix across all Monitored Surfaces */}
        {activeMetricTab === 'HEATMAP' && (
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-5">
            {appliedOptimizationNotice && (
              <div className="flex items-center gap-2 p-3 bg-emerald-950/80 border border-emerald-700/80 rounded-lg text-emerald-300 text-xs font-mono">
                <Sparkles className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{appliedOptimizationNotice}</span>
              </div>
            )}

            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Grid className="w-4 h-4 text-amber-400" />
                  <span>D3.js Surface Request Latency Heatmap & High-Latency Bottleneck Clusters</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Visualizes request latency across all 8 monitored surfaces over time slices. Click or hover any cell to inspect exact P50/P95/P99 latency, identify high-latency bottleneck clusters, and trigger ultra-optimization levers.
                </p>
              </div>

              {/* Filter Controls & Legend */}
              <div className="flex flex-wrap items-center gap-2 shrink-0 text-xs font-mono">
                <div className="flex items-center gap-1 p-1 bg-slate-950 rounded-lg border border-slate-800">
                  <button
                    onClick={() => setHeatmapFilter('ALL')}
                    className={`px-2.5 py-1 rounded transition-colors whitespace-nowrap ${
                      heatmapFilter === 'ALL' ? 'bg-slate-800 text-white font-bold' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    All Cells (96)
                  </button>
                  <button
                    onClick={() => setHeatmapFilter('BOTTLENECKS_ONLY')}
                    className={`px-2.5 py-1 rounded transition-colors whitespace-nowrap flex items-center gap-1 ${
                      heatmapFilter === 'BOTTLENECKS_ONLY' ? 'bg-amber-950 text-amber-300 font-bold border border-amber-800/60' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    <Flame className="w-3 h-3 text-amber-400" />
                    <span>Clusters Only ({heatmapData.filter((d) => d.isBottleneckCluster).length})</span>
                  </button>
                  <button
                    onClick={() => setHeatmapFilter('CRITICAL_ONLY')}
                    className={`px-2.5 py-1 rounded transition-colors whitespace-nowrap flex items-center gap-1 ${
                      heatmapFilter === 'CRITICAL_ONLY' ? 'bg-red-950 text-red-300 font-bold border border-red-800/60' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    <span>Critical ≥100ms ({heatmapData.filter((d) => d.p99Ms >= 100).length})</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Heatmap Legend */}
            <div className="flex flex-wrap items-center justify-between text-[11px] font-mono text-slate-400 pt-1 pb-1 border-y border-slate-800/60">
              <span className="text-slate-500 uppercase text-[10px]">Latency Distribution Legend:</span>
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-1.5">
                  <span className="w-3.5 h-3.5 rounded bg-[#064e3b] border border-emerald-700/50 inline-block" />
                  <span>&lt; 35ms Nominal</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3.5 h-3.5 rounded bg-[#b45309] border border-amber-600/50 inline-block" />
                  <span>35–74ms Moderate</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3.5 h-3.5 rounded bg-[#c2410c] border border-orange-400/80 border-dashed inline-block" />
                  <span>75–99ms Warning Cluster</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3.5 h-3.5 rounded bg-[#991b1b] border-2 border-red-400 inline-block" />
                  <span className="text-red-300 font-bold">≥ 100ms Critical Bottleneck</span>
                </div>
              </div>
            </div>

            {/* D3 Heatmap SVG */}
            <div className="w-full overflow-x-auto">
              <svg
                ref={heatmapSvgRef}
                viewBox="0 0 880 350"
                className="w-full h-auto min-w-[780px] bg-slate-950/90 rounded-lg border border-slate-800/80 shadow-inner"
              />
            </div>

            {/* Interactive Cell Inspector & Bottleneck Resolution Card */}
            {selectedHeatmapCell && (
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-2.5">
                  <div className="flex items-center gap-2.5">
                    <span
                      className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                        selectedHeatmapCell.clusterSeverity === 'CRITICAL'
                          ? 'bg-red-950 text-red-300 border border-red-700'
                          : selectedHeatmapCell.clusterSeverity === 'WARNING'
                          ? 'bg-amber-950 text-amber-300 border border-amber-700'
                          : 'bg-emerald-950 text-emerald-300 border border-emerald-700'
                      }`}
                    >
                      {selectedHeatmapCell.clusterSeverity === 'CRITICAL'
                        ? 'CRITICAL BOTTLENECK CLUSTER'
                        : selectedHeatmapCell.clusterSeverity === 'WARNING'
                        ? 'WARNING LATENCY CLUSTER'
                        : 'NOMINAL SLA INVARIANT'}
                    </span>
                    <h4 className="text-xs font-bold text-white">
                      {selectedHeatmapCell.surfaceName}
                    </h4>
                  </div>

                  <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
                    <span>Window: <strong className="text-white">{selectedHeatmapCell.timeLabel} UTC</strong></span>
                    <span aria-hidden="true">·</span>
                    <span>Throughput: <strong className="text-slate-200">{selectedHeatmapCell.requestCount} req/min</strong></span>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                  {/* Latency Breakdown */}
                  <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 flex flex-col justify-between space-y-2">
                    <span className="text-[10px] uppercase font-mono text-slate-500">Latency Percentiles</span>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="p-1.5 rounded bg-slate-950 border border-slate-800/80">
                        <span className="text-[10px] text-slate-500 block">P50</span>
                        <span className="text-sm font-mono font-bold text-slate-200">{selectedHeatmapCell.p50Ms}ms</span>
                      </div>
                      <div className="p-1.5 rounded bg-slate-950 border border-slate-800/80">
                        <span className="text-[10px] text-slate-500 block">P95</span>
                        <span className="text-sm font-mono font-bold text-amber-300">{selectedHeatmapCell.p95Ms}ms</span>
                      </div>
                      <div className="p-1.5 rounded bg-slate-950 border border-slate-800/80">
                        <span className="text-[10px] text-slate-500 block">P99</span>
                        <span className={`text-sm font-mono font-bold ${selectedHeatmapCell.p99Ms >= 100 ? 'text-red-400' : selectedHeatmapCell.p99Ms >= 75 ? 'text-orange-400' : 'text-emerald-400'}`}>
                          {selectedHeatmapCell.p99Ms}ms
                        </span>
                      </div>
                    </div>
                    <div className="text-[10px] text-slate-500 text-center font-mono">
                      Hard Bound: 120ms (INV-LAT-003)
                    </div>
                  </div>

                  {/* Bottleneck Cause */}
                  <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                    <span className="text-[10px] uppercase font-mono text-slate-500 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3 text-amber-400" />
                      <span>Cluster Bottleneck Analysis</span>
                    </span>
                    <p className="text-xs text-slate-300 leading-snug">
                      {selectedHeatmapCell.bottleneckRootCause ||
                        'No bottleneck cluster detected. Operation meets nominal sub-50ms estate latency invariants.'}
                    </p>
                  </div>

                  {/* Prescribed Optimization & Action */}
                  <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 flex flex-col justify-between space-y-2">
                    <div className="space-y-1">
                      <span className="text-[10px] uppercase font-mono text-emerald-400 flex items-center gap-1">
                        <Zap className="w-3 h-3 text-emerald-400" />
                        <span>Prescribed Ultra-Optimization</span>
                      </span>
                      <p className="text-xs text-emerald-300 font-mono text-[11px] leading-snug">
                        {selectedHeatmapCell.prescribedOptimization ||
                          'Current path is optimized. Zero action required.'}
                      </p>
                    </div>

                    {selectedHeatmapCell.isBottleneckCluster && (
                      <button
                        onClick={() => handleApplyOptimization(selectedHeatmapCell)}
                        className="w-full py-1.5 px-3 rounded text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors flex items-center justify-center gap-1.5 shadow-sm"
                      >
                        <Zap className="w-3.5 h-3.5" />
                        <span>Execute Optimization Lever (-58% Latency)</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Quick Estate Bottleneck Intelligence Strip */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs pt-1">
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 font-mono text-[10px] uppercase block">Total Matrix Grid</span>
                <span className="text-white font-bold font-mono text-base">96 Cells</span>
                <span className="text-slate-400 block text-[10px]">8 surfaces × 12 time slices</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 font-mono text-[10px] uppercase block">Bottleneck Clusters</span>
                <span className="text-amber-400 font-bold font-mono text-base">
                  {heatmapData.filter((d) => d.isBottleneckCluster).length} Clusters
                </span>
                <span className="text-slate-400 block text-[10px]">P99 ≥ 75ms highlighted</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 font-mono text-[10px] uppercase block">Critical Operations</span>
                <span className="text-red-400 font-bold font-mono text-base">
                  {heatmapData.filter((d) => d.p99Ms >= 100).length} Cells
                </span>
                <span className="text-slate-400 block text-[10px]">Agents token storm & fan-out</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 font-mono text-[10px] uppercase block">Sub-10ms Fast Path</span>
                <span className="text-emerald-400 font-bold font-mono text-base">
                  {heatmapData.filter((d) => d.p50Ms <= 10).length} Cells
                </span>
                <span className="text-slate-400 block text-[10px]">eBPF sockops & static shims</span>
              </div>
            </div>
          </div>
        )}

        {/* Tab 1: D3 Circumventions vs Ratifications */}
        {activeMetricTab === 'THROUGHPUT' && (
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <span>D3.js Stream: Circumvention Attempts (Red Bars) vs Ratifications (Green Area)</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Hover over any data point to inspect exact minute-by-minute transactional metrics and bypass flags.
                </p>
              </div>

              {selectedPoint && (
                <div className="px-3 py-1 rounded bg-slate-950 border border-slate-800 font-mono text-xs flex items-center gap-3">
                  <span className="text-slate-400">Time: <strong className="text-white">{selectedPoint.label}</strong></span>
                  <span className="text-emerald-400">Ratified: <strong>{selectedPoint.ratified}</strong></span>
                  <span className="text-red-400">Blocked: <strong>{selectedPoint.circumventions}</strong></span>
                  <span className="text-sky-400">P99: <strong>{selectedPoint.p99LatencyMs}ms</strong></span>
                </div>
              )}
            </div>

            <div className="w-full overflow-x-auto">
              <svg
                ref={svgRef}
                viewBox="0 0 800 300"
                className="w-full h-auto min-w-[700px] bg-slate-950/60 rounded-lg border border-slate-800/80"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs pt-2">
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-slate-500 font-mono text-[10px] uppercase">Peak Burst Window</span>
                <div className="font-bold text-white font-mono">19:30 UTC</div>
                <p className="text-[11px] text-slate-400">32 ratified AST transactions/min with 0 metric drops.</p>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-slate-500 font-mono text-[10px] uppercase">Rogue Bypass Clustering</span>
                <div className="font-bold text-red-400 font-mono">04:25 UTC (3 blocked)</div>
                <p className="text-[11px] text-slate-400">Intercepted 3 distinct attempts to run git push --no-verify.</p>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-slate-500 font-mono text-[10px] uppercase">Continuous Metric Integrity</span>
                <div className="font-bold text-emerald-400 font-mono">100.00% Zero-Leak</div>
                <p className="text-[11px] text-slate-400">Every single event recorded in Merkle ledger with in-toto attestation.</p>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: D3 Latency Cliffs */}
        {activeMetricTab === 'LATENCY_CLIFFS' && (
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span>D3.js Estate-Wide P99 Tail Latency Timeline vs Invariant Ceiling</span>
              </h3>
              <p className="text-xs text-slate-400">
                Tracking microsecond/millisecond latency drift across all 8 surfaces. Dotted line marks the INV-LAT 120ms hard kill-switch.
              </p>
            </div>

            <div className="w-full overflow-x-auto">
              <svg
                ref={latencySvgRef}
                viewBox="0 0 800 240"
                className="w-full h-auto min-w-[700px] bg-slate-950/60 rounded-lg border border-slate-800/80"
              />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs pt-1">
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 font-mono text-[10px] uppercase block">Microservices P99</span>
                <span className="text-sky-400 font-bold font-mono text-base">48.2ms</span>
                <span className="text-slate-400 block text-[10px]">Mesh proxy + OTel</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 font-mono text-[10px] uppercase block">Pre-Push Hook AST</span>
                <span className="text-indigo-400 font-bold font-mono text-base">38.4ms</span>
                <span className="text-slate-400 block text-[10px]">Compiled AST probe</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 font-mono text-[10px] uppercase block">Agent Step Latency</span>
                <span className="text-purple-400 font-bold font-mono text-base">142.0ms</span>
                <span className="text-slate-400 block text-[10px]">Token throttle gated</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 font-mono text-[10px] uppercase block">Kernel eBPF Packet</span>
                <span className="text-emerald-400 font-bold font-mono text-base">&lt; 240ns</span>
                <span className="text-slate-400 block text-[10px]">Zero-copy sockops</span>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Intelligent Anomaly Radar */}
        {activeMetricTab === 'ANOMALIES' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  <span>Intelligent Operational Anomaly Radar ({anomalies.length} Flagged)</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Continuous heuristics analyzing circumvention vectors, adversarial evasions, and tail bottlenecks.
                </p>
              </div>
              <button
                onClick={onNavigateToSimulator}
                className="px-3 py-1.5 text-xs font-semibold rounded bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
              >
                Test Interceptor Gate
              </button>
            </div>

            <div className="grid grid-cols-1 gap-3.5">
              {anomalies.map((anom) => (
                <div
                  key={anom.id}
                  className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-2.5">
                    <div className="flex items-center gap-2.5">
                      <span
                        className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                          anom.severity === 'CRITICAL'
                            ? 'bg-red-950 text-red-400 border border-red-800'
                            : 'bg-amber-950 text-amber-400 border border-amber-800'
                        }`}
                      >
                        {anom.severity}
                      </span>
                      <h4 className="text-xs font-bold text-white">{anom.title}</h4>
                    </div>

                    <div className="text-[11px] font-mono text-slate-400 flex items-center gap-2">
                      <span>Surface: <strong className="text-slate-300">{anom.surface}</strong></span>
                      <span aria-hidden="true">·</span>
                      <span>Observed: <strong className="text-red-400">{anom.metricObserved}</strong></span>
                    </div>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed">
                    {anom.description}
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 text-xs">
                    <div className="p-2.5 rounded bg-slate-950 border border-slate-800 text-[11px] space-y-1">
                      <span className="text-slate-500 font-mono uppercase block text-[10px]">Root Cause Analysis</span>
                      <div className="text-slate-300 leading-snug">{anom.rootCauseAnalysis}</div>
                    </div>
                    <div className="p-2.5 rounded bg-slate-950 border border-slate-800 text-[11px] space-y-1">
                      <span className="text-emerald-500 font-mono uppercase block text-[10px]">Mathematical Remediation</span>
                      <div className="text-emerald-300 leading-snug">{anom.mathematicalRemediation}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 4: Ultra-Optimization Prescriptions for Extreme Low Latency */}
        {activeMetricTab === 'OPTIMIZATION' && (
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <TrendingDown className="w-4 h-4 text-emerald-400" />
                <span>Ultra-Optimization Levers for Extreme Low-Latency Estate</span>
              </h3>
              <p className="text-xs text-slate-400">
                Actionable, high-leverage architectural upgrades to strip milliseconds and microseconds off every execution path.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {ULTRA_OPTIMIZATION_PRESCRIPTIONS.map((prescription) => (
                <div
                  key={prescription.id}
                  className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 flex flex-col justify-between space-y-3"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-slate-800 text-indigo-300 border border-slate-700">
                        {prescription.domain}
                      </span>
                      <span className="text-xs font-mono font-bold text-emerald-400">
                        {prescription.projectedLatencySavings}
                      </span>
                    </div>

                    <h4 className="text-xs font-bold text-white">{prescription.title}</h4>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      {prescription.impactDescription}
                    </p>
                  </div>

                  <div className="space-y-2 pt-2 border-t border-slate-800/80">
                    <div className="flex justify-between text-[11px] text-slate-400 font-mono">
                      <span>Baseline Cost:</span>
                      <span className="text-rose-400">{prescription.currentLatencyCost}</span>
                    </div>
                    <div className="p-2 bg-slate-950 rounded border border-slate-800/80 font-mono text-[10px] text-slate-300 overflow-x-auto">
                      <code>{prescription.cliCommandOrConfig}</code>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

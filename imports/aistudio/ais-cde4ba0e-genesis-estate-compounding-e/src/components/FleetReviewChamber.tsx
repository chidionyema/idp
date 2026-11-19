/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import {
  Users,
  Calendar,
  Clock,
  Globe,
  Wifi,
  Zap,
  CheckCircle2,
  ShieldCheck,
  Cpu,
  Sparkles,
  Brain,
  MessageSquare,
  Send,
  Volume2,
  Flame,
  RefreshCw,
  Sliders,
  Eye,
  FileCode2,
  ArrowRight,
  Radio,
  Lock,
  Activity
} from 'lucide-react';
import {
  INITIAL_FLEET_COUNCIL,
  INITIAL_REVIEW_DOCKETS,
  INITIAL_MEETING_AGENDA,
  INITIAL_TRANSCRIPT,
  INITIAL_FOUNDER_COGNITIVE_PROFILE,
  INITIAL_FLEET_COGNITIVE_PROFILE,
  getTimezoneAndVpnState,
  executeMeetingDocketImmediate,
  updateFounderCognitiveState,
  FleetCouncilMember,
  ReviewDocketItem,
  MeetingAgendaItem,
  MeetingTranscriptEntry,
  ImmediateExecutionRecord,
  TimezoneAndVpnState,
  FounderCognitiveProfile,
  FleetCognitiveProfile
} from '../lib/protocolEngine.ts';

export const FleetReviewChamber: React.FC = () => {
  // Council & Session State
  const [attendees, setAttendees] = useState<FleetCouncilMember[]>(INITIAL_FLEET_COUNCIL);
  const [dockets, setDockets] = useState<ReviewDocketItem[]>(INITIAL_REVIEW_DOCKETS);
  const [agenda, setAgenda] = useState<MeetingAgendaItem[]>(INITIAL_MEETING_AGENDA);
  const [transcript, setTranscript] = useState<MeetingTranscriptEntry[]>(INITIAL_TRANSCRIPT);
  const [recentExecutions, setRecentExecutions] = useState<ImmediateExecutionRecord[]>([]);

  // Timezone & Calendar State
  const [tzState, setTzState] = useState<TimezoneAndVpnState>(getTimezoneAndVpnState());
  const [simulatedVpnMode, setSimulatedVpnMode] = useState<boolean>(false);

  // Reciprocal Cognitive State
  const [founderProfile, setFounderProfile] = useState<FounderCognitiveProfile>(INITIAL_FOUNDER_COGNITIVE_PROFILE);
  const [fleetProfile] = useState<FleetCognitiveProfile>(INITIAL_FLEET_COGNITIVE_PROFILE);
  const [selectedFocusState, setSelectedFocusState] = useState<FounderCognitiveProfile['focusState']>(founderProfile.focusState);
  const [moodIndex, setMoodIndex] = useState<number>(founderProfile.moodEnergyIndex);
  const [customMoodNote, setCustomMoodNote] = useState<string>(founderProfile.moodDescription);

  // Active view tabs within Meeting Chamber
  const [chamberSubTab, setChamberSubTab] = useState<'chamber' | 'dockets' | 'reciprocal-sync' | 'timezone-mesh'>('chamber');
  
  // Interactive Founder Motion input
  const [founderMotionText, setFounderMotionText] = useState<string>('');
  const [isSummoningQuorum, setIsSummoningQuorum] = useState<boolean>(false);
  const [audioSimulationActive, setAudioSimulationActive] = useState<boolean>(true);
  const [activeSpeaker, setActiveSpeaker] = useState<string>('AIDE_OTTO');

  // Clock tick interval
  useEffect(() => {
    const timer = setInterval(() => {
      const override = simulatedVpnMode ? 'Europe/Amsterdam' : undefined;
      setTzState(getTimezoneAndVpnState(override));
    }, 1000);
    return () => clearInterval(timer);
  }, [simulatedVpnMode]);

  // Handle immediate docket ratification
  const handleRatifyDocket = (docketId: string) => {
    const { updatedDockets, executionRecord } = executeMeetingDocketImmediate(docketId, true, dockets);
    setDockets(updatedDockets);
    setRecentExecutions(prev => [executionRecord, ...prev].slice(0, 8));

    // Append ratification event to meeting transcript
    const newEntry: MeetingTranscriptEntry = {
      id: `TX-${Date.now()}`,
      speaker: 'Immediate Effect Engine',
      time: new Date().toLocaleTimeString('en-GB'),
      text: `RATIFIED & EXECUTED: ${executionRecord.action}. Deployed in ${executionRecord.latencyMs}ms with receipt ${executionRecord.receipt}.`,
      roleTag: 'IMMEDIATE_EFFECT',
      type: 'EXECUTION'
    };
    setTranscript(prev => [...prev, newEntry]);
  };

  // Handle founder motion submit
  const handleSendFounderMotion = (e: React.FormEvent) => {
    e.preventDefault();
    if (!founderMotionText.trim()) return;

    const userText = founderMotionText.trim();
    setFounderMotionText('');

    const entryId = `TX-${Date.now()}`;
    const timeStr = new Date().toLocaleTimeString('en-GB');

    const founderEntry: MeetingTranscriptEntry = {
      id: entryId,
      speaker: 'Founder (Chidi)',
      time: timeStr,
      text: userText,
      roleTag: 'SOVEREIGN_CHAIR',
      type: 'MOTION'
    };

    setTranscript(prev => [...prev, founderEntry]);

    // Deterministic Fleet Response from Otto or Oracle
    setTimeout(() => {
      const fleetResponder = userText.toLowerCase().includes('longevity') || userText.toLowerCase().includes('risk')
        ? { speaker: 'Mega-Oracle', role: 'PROPHET_OMNI', text: `Teleological validation confirmed. Invariant projection satisfies Core Law #7 (R_asym >= 2.0). All failure modes dampened.` }
        : { speaker: 'Otto', role: 'EXECUTION_AUTARCH', text: `Sovereign motion ingested with 0 friction. Dispatching task across active worker lanes with verified HMAC-SHA256 receipt.` };

      const responseEntry: MeetingTranscriptEntry = {
        id: `TX-RESP-${Date.now()}`,
        speaker: fleetResponder.speaker,
        time: new Date().toLocaleTimeString('en-GB'),
        text: fleetResponder.text,
        roleTag: fleetResponder.role,
        type: 'SPEECH'
      };
      setTranscript(prev => [...prev, responseEntry]);
    }, 600);
  };

  // Handle cognitive state update
  const handleApplyCognitiveRecalibration = () => {
    const updated = updateFounderCognitiveState(selectedFocusState, moodIndex, customMoodNote, founderProfile);
    setFounderProfile(updated);
  };

  // Emergency Quorum Summons
  const handleEmergencyQuorum = () => {
    setIsSummoningQuorum(true);
    setTimeout(() => {
      setIsSummoningQuorum(false);
      const emergencyEntry: MeetingTranscriptEntry = {
        id: `TX-EMERGENCY-${Date.now()}`,
        speaker: 'Security Sentinel',
        time: new Date().toLocaleTimeString('en-GB'),
        text: 'EMERGENCY QUORUM ENGAGED (§13.1): All 8 fleet nodes convened in 1.4ms. Current focus: Sovereign Invariant Protection. Full telemetry synchronized.',
        roleTag: 'KEY_VAULT_WARDEN',
        type: 'MOTION'
      };
      setTranscript(prev => [...prev, emergencyEntry]);
    }, 800);
  };

  return (
    <div className="space-y-6">
      
      {/* Hero Header with Live Timezone Anchor & Meeting Status */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-bl from-cyan-500/10 via-indigo-500/5 to-transparent blur-3xl pointer-events-none" />

        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-cyan-950 text-cyan-400 border border-cyan-800 flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5 animate-pulse text-cyan-400" />
                CONSTITUTIONAL CANON §13
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-emerald-950 text-emerald-400 border border-emerald-800">
                QUORUM 8/8 NOMINAL
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-indigo-950 text-indigo-300 border border-indigo-800">
                UK BASE: EUROPE/LONDON
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
              <span>Weekly Fleet Review & Reciprocal Cognitive Chamber</span>
              <Sparkles className="w-6 h-6 text-cyan-400" />
            </h1>
            <p className="text-sm text-slate-400 mt-1 max-w-3xl">
              World-class executive meeting facilities for the Sovereign Founder and entire autonomous fleet.
              Timezone-aware across VPN switches, immediate-effect docket ratification, and continuous bi-directional habit learning.
            </p>
          </div>

          {/* Quick Actions & Emergency Quorum Trigger */}
          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              onClick={handleEmergencyQuorum}
              disabled={isSummoningQuorum}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-rose-600 to-red-700 hover:from-rose-500 hover:to-red-600 text-white font-mono text-xs font-bold shadow-lg shadow-rose-900/40 flex items-center gap-2 transition-all cursor-pointer active:scale-95 disabled:opacity-50"
            >
              <Zap className="w-4 h-4" />
              <span>{isSummoningQuorum ? 'Summoning Quorum...' : 'Summon Emergency Quorum'}</span>
            </button>

            <button
              onClick={() => setAudioSimulationActive(!audioSimulationActive)}
              className={`px-3 py-2 rounded-xl text-xs font-mono flex items-center gap-2 border transition-all cursor-pointer ${
                audioSimulationActive
                  ? 'bg-cyan-950/80 text-cyan-300 border-cyan-700'
                  : 'bg-slate-800 text-slate-400 border-slate-700'
              }`}
            >
              <Volume2 className="w-4 h-4" />
              <span>{audioSimulationActive ? 'Voice Stream: Active' : 'Voice: Muted'}</span>
            </button>
          </div>
        </div>

        {/* Dynamic Multi-Timezone & Calendar HUD Bar */}
        <div className="mt-6 pt-5 border-t border-slate-800/80 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          
          {/* Founder Base Time */}
          <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3.5 flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-lg bg-cyan-950/80 border border-cyan-800/80 flex items-center justify-center shrink-0">
              <Clock className="w-5 h-5 text-cyan-400" />
            </div>
            <div className="min-w-0">
              <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Founder Prime (UK)</div>
              <div className="text-sm font-mono font-bold text-cyan-200 truncate">{tzState.founderBaseTimeFormatted}</div>
              <div className="text-[10px] text-slate-500 font-mono">Europe/London (GMT/BST)</div>
            </div>
          </div>

          {/* Estate Consensus UTC Time */}
          <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3.5 flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-lg bg-indigo-950/80 border border-indigo-800/80 flex items-center justify-center shrink-0">
              <Globe className="w-5 h-5 text-indigo-400" />
            </div>
            <div className="min-w-0">
              <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Estate Consensus Time</div>
              <div className="text-sm font-mono font-bold text-indigo-200 truncate">{tzState.estateUtcTimeFormatted}</div>
              <div className="text-[10px] text-slate-500 font-mono">Universal RAFT Epoch</div>
            </div>
          </div>

          {/* VPN Awareness & Local Drift */}
          <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3.5 flex items-center gap-3.5">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 border ${
              tzState.isVpnDetected
                ? 'bg-amber-950/80 border-amber-800/80'
                : 'bg-emerald-950/80 border-emerald-800/80'
            }`}>
              <Wifi className={`w-5 h-5 ${tzState.isVpnDetected ? 'text-amber-400' : 'text-emerald-400'}`} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Network / VPN State</span>
                <button
                  onClick={() => setSimulatedVpnMode(!simulatedVpnMode)}
                  className="text-[10px] font-mono text-cyan-400 hover:underline cursor-pointer"
                  title="Toggle VPN simulation between London direct link and Amsterdam Nomad tunnel"
                >
                  {simulatedVpnMode ? 'Restore UK' : 'Simulate VPN'}
                </button>
              </div>
              <div className="text-xs font-mono font-bold text-slate-200 truncate">
                {tzState.isVpnDetected ? 'VPN Nomad Gateway' : 'UK Direct Sovereign Link'}
              </div>
              <div className="text-[10px] text-slate-400 truncate" title={tzState.vpnMitigationStrategy}>
                {tzState.isVpnDetected ? 'Compensated (0ms drift)' : 'No hop skew'}
              </div>
            </div>
          </div>

          {/* Next Scheduled Weekly Architecture Review */}
          <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3.5 flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-lg bg-purple-950/80 border border-purple-800/80 flex items-center justify-center shrink-0">
              <Calendar className="w-5 h-5 text-purple-400" />
            </div>
            <div className="min-w-0">
              <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Next Weekly Review</div>
              <div className="text-sm font-mono font-bold text-purple-200 truncate">{tzState.timeUntilWeeklyReviewFormatted}</div>
              <div className="text-[10px] text-slate-500 font-mono">Mon 14:00 UK · Cal Synced</div>
            </div>
          </div>

        </div>

      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setChamberSubTab('chamber')}
          className={`px-4 py-2 rounded-lg font-mono text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
            chamberSubTab === 'chamber'
              ? 'bg-slate-800 text-cyan-300 border border-cyan-800/60 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Users className="w-4 h-4 text-cyan-400" />
          <span>Council Chamber & Live Session</span>
        </button>

        <button
          onClick={() => setChamberSubTab('dockets')}
          className={`px-4 py-2 rounded-lg font-mono text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
            chamberSubTab === 'dockets'
              ? 'bg-slate-800 text-cyan-300 border border-cyan-800/60 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <FileCode2 className="w-4 h-4 text-indigo-400" />
          <span>Immediate Effect Dockets ({dockets.filter(d => d.reviewStatus === 'PENDING_RATIFICATION').length} Pending)</span>
        </button>

        <button
          onClick={() => setChamberSubTab('reciprocal-sync')}
          className={`px-4 py-2 rounded-lg font-mono text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
            chamberSubTab === 'reciprocal-sync'
              ? 'bg-slate-800 text-cyan-300 border border-cyan-800/60 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Brain className="w-4 h-4 text-purple-400" />
          <span>Reciprocal Cognitive Mesh</span>
        </button>

        <button
          onClick={() => setChamberSubTab('timezone-mesh')}
          className={`px-4 py-2 rounded-lg font-mono text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
            chamberSubTab === 'timezone-mesh'
              ? 'bg-slate-800 text-cyan-300 border border-cyan-800/60 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Globe className="w-4 h-4 text-emerald-400" />
          <span>Timezone & Multi-Lane Clocks</span>
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: COUNCIL CHAMBER & LIVE SESSION */}
      {/* ========================================================================= */}
      {chamberSubTab === 'chamber' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Left Column: Holographic Amphitheater & Attendees (7 cols) */}
          <div className="lg:col-span-7 space-y-6">
            
            {/* Holographic Amphitheater Visual Presence */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400 animate-pulse" />
                  <h3 className="text-sm font-mono font-bold text-white uppercase tracking-wider">
                    Executive Amphitheater · Fleet Quorum
                  </h3>
                </div>
                <span className="text-[11px] font-mono text-slate-400">
                  Active Speaker: <span className="text-cyan-300 font-bold">{attendees.find(a => a.id === activeSpeaker)?.name || 'Otto'}</span>
                </span>
              </div>

              {/* 3D Round Table Hologram Representation */}
              <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-6 relative overflow-hidden flex items-center justify-center min-h-[260px]">
                {/* Visual Ambient Rings */}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="w-64 h-64 rounded-full border border-cyan-500/20 animate-spin" style={{ animationDuration: '40s' }} />
                  <div className="w-48 h-48 rounded-full border border-indigo-500/25 animate-spin" style={{ animationDuration: '25s', animationDirection: 'reverse' }} />
                  <div className="w-32 h-32 rounded-full border border-purple-500/20 animate-pulse" />
                </div>

                {/* Central Holographic Emblem */}
                <div className="text-center relative z-10 pointer-events-none">
                  <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-cyan-400 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/30 mb-2">
                    <span className="font-mono font-black text-slate-950 text-xl">G</span>
                  </div>
                  <div className="text-xs font-mono font-bold text-white">GENESIS FLEET COUNCIL</div>
                  <div className="text-[10px] font-mono text-cyan-400">Weekly Architecture & Invariant Review</div>
                </div>

                {/* Attendees Ring Layout */}
                <div className="absolute inset-0 pointer-events-auto p-4 flex flex-wrap items-center justify-between">
                  {attendees.map((member) => (
                    <button
                      key={member.id}
                      onClick={() => setActiveSpeaker(member.id)}
                      className={`p-2 rounded-xl border backdrop-blur-md transition-all flex items-center gap-2 cursor-pointer ${
                        activeSpeaker === member.id
                          ? 'bg-slate-800 border-cyan-400 ring-2 ring-cyan-500/30 scale-105 shadow-lg'
                          : 'bg-slate-900/80 border-slate-800 hover:border-slate-700 hover:bg-slate-800/60'
                      }`}
                    >
                      <div className={`w-7 h-7 rounded-lg bg-gradient-to-br ${member.avatarColor} flex items-center justify-center text-slate-950 font-mono font-bold text-xs`}>
                        {member.name.charAt(0)}
                      </div>
                      <div className="text-left">
                        <div className="text-xs font-mono font-bold text-slate-200">{member.name}</div>
                        <div className="text-[9px] font-mono text-slate-400">{member.callsign}</div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Detailed Active Member Intelligence Card */}
              {(() => {
                const cur = attendees.find(a => a.id === activeSpeaker) || attendees[0];
                return (
                  <div className="mt-4 p-4 rounded-xl bg-slate-950/70 border border-slate-800">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-cyan-300">{cur.name}</span>
                        <span className="text-[10px] font-mono text-slate-500">[{cur.role}]</span>
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                        HEALTH: {(cur.currentMoodScore * 100).toFixed(0)}% NOMINAL
                      </span>
                    </div>
                    <div className="text-xs text-slate-300 mb-3">{cur.specialization}</div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
                      <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80">
                        <div className="text-[10px] text-emerald-400 font-bold mb-1 uppercase">Cognitive Strengths:</div>
                        <ul className="list-disc list-inside space-y-0.5 text-slate-300 text-[11px]">
                          {cur.cognitiveStrengths.map((s, idx) => (
                            <li key={idx}>{s}</li>
                          ))}
                        </ul>
                      </div>
                      <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80">
                        <div className="text-[10px] text-amber-400 font-bold mb-1 uppercase">Known Weaknesses & Mitigations:</div>
                        <ul className="list-disc list-inside space-y-0.5 text-slate-300 text-[11px]">
                          {cur.operationalWeaknesses.map((w, idx) => (
                            <li key={idx}>{w}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                );
              })()}

            </div>

            {/* Meeting Agenda Progress Tracker */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <h3 className="text-sm font-mono font-bold text-white uppercase tracking-wider">
                    Council Agenda Items (§13.1)
                  </h3>
                </div>
                <span className="text-xs font-mono text-slate-400">Week 44 Review</span>
              </div>

              <div className="space-y-2.5">
                {agenda.map((item) => (
                  <div
                    key={item.id}
                    className={`p-3 rounded-xl border transition-all ${
                      item.status === 'COMPLETED'
                        ? 'bg-slate-950/40 border-slate-800 text-slate-400'
                        : item.status === 'IN_PROGRESS'
                        ? 'bg-slate-950/90 border-cyan-800/80 text-slate-100 shadow-md shadow-cyan-950/40'
                        : 'bg-slate-950/30 border-slate-800/50 text-slate-500'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                          item.status === 'COMPLETED'
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                            : item.status === 'IN_PROGRESS'
                            ? 'bg-cyan-950 text-cyan-300 border border-cyan-800 animate-pulse'
                            : 'bg-slate-900 text-slate-500'
                        }`}>
                          {item.status}
                        </span>
                        <span className="text-xs font-mono font-bold text-slate-200">{item.title}</span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-400">{item.presenter} · {item.durationMin}m</span>
                    </div>
                    <div className="text-xs text-slate-300 pl-1">{item.actionSummary}</div>
                  </div>
                ))}
              </div>
            </div>

          </div>

          {/* Right Column: Live Discussion Transcript & Founder Motions (5 cols) */}
          <div className="lg:col-span-5 space-y-6">
            
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col h-[640px]">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-sm font-mono font-bold text-white uppercase tracking-wider">
                    Council Deliberation Transcript
                  </h3>
                </div>
                <span className="text-[10px] font-mono text-slate-400">HMAC Audited</span>
              </div>

              {/* Scrollable Transcript List */}
              <div className="flex-1 overflow-y-auto space-y-3 pr-2 font-mono text-xs">
                {transcript.map((entry) => (
                  <div
                    key={entry.id}
                    className={`p-3 rounded-xl border ${
                      entry.speaker.includes('Founder')
                        ? 'bg-amber-950/30 border-amber-800/60 text-amber-100 ml-4'
                        : entry.type === 'EXECUTION'
                        ? 'bg-emerald-950/40 border-emerald-800/70 text-emerald-200'
                        : 'bg-slate-950/70 border-slate-800/80 text-slate-200'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1 text-[10px]">
                      <span className="font-bold flex items-center gap-1.5">
                        {entry.speaker}
                        <span className="text-slate-500 font-normal">[{entry.roleTag}]</span>
                      </span>
                      <span className="text-slate-500">{entry.time}</span>
                    </div>
                    <div className="text-xs font-sans leading-relaxed text-slate-200">
                      {entry.text}
                    </div>
                  </div>
                ))}
              </div>

              {/* Founder Sovereign Motion Input Form */}
              <form onSubmit={handleSendFounderMotion} className="pt-3 border-t border-slate-800 mt-3">
                <div className="text-[10px] font-mono text-slate-400 mb-1.5 flex items-center justify-between">
                  <span>Sovereign Voice Directive / Motion (§1.1):</span>
                  <span className="text-cyan-400">Sub-2.5ms Fleet Dispatch</span>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={founderMotionText}
                    onChange={(e) => setFounderMotionText(e.target.value)}
                    placeholder="Issue directive or architecture motion to the fleet..."
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs font-mono text-white focus:outline-none focus:border-cyan-500 transition-colors"
                  />
                  <button
                    type="submit"
                    className="px-3.5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-mono text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer shadow-md shadow-cyan-950"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>Motion</span>
                  </button>
                </div>
              </form>

            </div>

          </div>

        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: IMMEDIATE EFFECT DOCKETS */}
      {/* ========================================================================= */}
      {chamberSubTab === 'dockets' && (
        <div className="space-y-6">
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Zap className="w-5 h-5 text-amber-400" />
                  <span>Immediate Effect Engine (§13.3)</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Ratified architecture proposals and code diffs execute directly to production pipelines without manual PR friction (Δ_founder = 0).
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-slate-400">Execution Invariant:</span>
                <span className="px-2.5 py-1 rounded-lg bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono text-xs font-bold">
                  Latency &lt; 2.5ms Guaranteed
                </span>
              </div>
            </div>

            {/* Dockets Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {dockets.map((docket) => (
                <div
                  key={docket.id}
                  className={`p-5 rounded-xl border transition-all ${
                    docket.reviewStatus === 'DISPATCHED_TO_PRODUCTION'
                      ? 'bg-slate-950/40 border-emerald-800/60'
                      : 'bg-slate-950/80 border-slate-800 hover:border-slate-700 shadow-md'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                      {docket.category}
                    </span>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                      docket.reviewStatus === 'DISPATCHED_TO_PRODUCTION'
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold'
                        : docket.reviewStatus === 'RATIFIED'
                        ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                        : 'bg-amber-950 text-amber-300 border border-amber-800'
                    }`}>
                      {docket.reviewStatus}
                    </span>
                  </div>

                  <h4 className="text-sm font-bold text-white mb-1.5">{docket.title}</h4>
                  <p className="text-xs text-slate-300 mb-3">{docket.diffSummary}</p>

                  <div className="space-y-1.5 text-xs font-mono bg-slate-900/60 p-3 rounded-lg border border-slate-800/80 mb-4">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-400">Author:</span>
                      <span className="text-cyan-300">{docket.authorAgent}</span>
                    </div>
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-400">Asymmetry Ratio (R_asym):</span>
                      <span className="text-emerald-400 font-bold">{docket.asymRatio}x ({'>='} 2.0 Invariant)</span>
                    </div>
                    <div className="text-[11px] text-slate-400 truncate">
                      <span className="text-slate-400">Invariant Proof:</span> {docket.invariantCheck}
                    </div>
                    {docket.ratificationReceipt && (
                      <div className="text-[10px] text-indigo-300 truncate">
                        <span className="text-slate-400">Receipt:</span> {docket.ratificationReceipt}
                      </div>
                    )}
                  </div>

                  {/* Immediate Action Buttons */}
                  <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
                    <span className="text-[11px] font-mono text-slate-500">
                      Files: {docket.affectedFiles.join(', ')}
                    </span>

                    {docket.reviewStatus !== 'DISPATCHED_TO_PRODUCTION' ? (
                      <button
                        onClick={() => handleRatifyDocket(docket.id)}
                        className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-mono text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer shadow-md shadow-emerald-950 active:scale-95"
                      >
                        <Zap className="w-3.5 h-3.5" />
                        <span>Ratify & Deploy Now</span>
                      </button>
                    ) : (
                      <span className="text-xs font-mono text-emerald-400 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Live in Production ({docket.executionLatencyMs}ms)</span>
                      </span>
                    )}
                  </div>

                </div>
              ))}
            </div>

            {/* Live Production Dispatches Feed */}
            {recentExecutions.length > 0 && (
              <div className="mt-6 pt-5 border-t border-slate-800">
                <h4 className="text-xs font-mono font-bold text-white uppercase tracking-wider mb-3 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-emerald-400" />
                  <span>Real-Time Execution Telemetry (Immediate Effect Engine)</span>
                </h4>
                <div className="space-y-2">
                  {recentExecutions.map((rec) => (
                    <div
                      key={rec.id}
                      className="p-2.5 rounded-lg bg-slate-950 border border-emerald-800/50 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs font-mono"
                    >
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                        <span className="text-slate-200 font-bold">{rec.action}</span>
                      </div>
                      <div className="flex items-center gap-3 text-[11px] text-slate-400">
                        <span>Latency: <strong className="text-emerald-300">{rec.latencyMs}ms</strong></span>
                        <span className="text-indigo-300">{rec.receipt}</span>
                        <span className="text-emerald-400 font-bold">VERIFIED_IN_PROD</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: RECIPROCAL COGNITIVE MESH */}
      {/* ========================================================================= */}
      {chamberSubTab === 'reciprocal-sync' && (
        <div className="space-y-6">
          
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Brain className="w-5 h-5 text-purple-400" />
                  <span>Reciprocal Cognitive Mesh & Continuous Learning Engine (§13.4)</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Bi-directional telemetry between the Founder and autonomous fleet. The estate learns Founder habits and energy curves, while the fleet provides transparent insight into its own strengths and weaknesses.
                </p>
              </div>

              <button
                onClick={handleApplyCognitiveRecalibration}
                className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-mono text-xs font-bold flex items-center gap-2 transition-all cursor-pointer shadow-lg shadow-purple-950 active:scale-95"
              >
                <Sliders className="w-4 h-4" />
                <span>Recalibrate Fleet Adaptation</span>
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              
              {/* Founder Cognitive State Tuner (6 cols) */}
              <div className="lg:col-span-6 space-y-4 bg-slate-950/70 border border-slate-800 rounded-xl p-5">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <h4 className="text-xs font-mono font-bold text-white uppercase tracking-wider flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-cyan-400" />
                    <span>Founder Current Focus State & Cadence</span>
                  </h4>
                  <span className="text-[10px] font-mono text-slate-500">Live Sensory Probe</span>
                </div>

                {/* Focus State Selector */}
                <div>
                  <label className="text-xs font-mono text-slate-300 block mb-2">Focus Mode:</label>
                  <div className="grid grid-cols-2 gap-2">
                    {(['DEEP_FLOW', 'HIGH_VELOCITY_SPRINT', 'STRATEGIC_REVIEW', 'RESTORATION'] as const).map((mode) => (
                      <button
                        key={mode}
                        type="button"
                        onClick={() => setSelectedFocusState(mode)}
                        className={`p-2.5 rounded-lg text-xs font-mono font-bold border transition-all text-left cursor-pointer ${
                          selectedFocusState === mode
                            ? 'bg-cyan-950/80 border-cyan-500 text-cyan-200 shadow-md shadow-cyan-950'
                            : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800'
                        }`}
                      >
                        {mode.replace('_', ' ')}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Energy & Mood Slider */}
                <div>
                  <div className="flex items-center justify-between text-xs font-mono mb-1.5">
                    <span className="text-slate-300">Cognitive Velocity Index:</span>
                    <span className="text-cyan-400 font-bold">{moodIndex}% High Intensity</span>
                  </div>
                  <input
                    type="range"
                    min="50"
                    max="100"
                    value={moodIndex}
                    onChange={(e) => setMoodIndex(Number(e.target.value))}
                    className="w-full accent-cyan-400 bg-slate-800 h-2 rounded-lg cursor-pointer"
                  />
                </div>

                {/* Current Mood Note */}
                <div>
                  <label className="text-xs font-mono text-slate-300 block mb-1.5">Founder Energy & Strategic Intent:</label>
                  <textarea
                    rows={2}
                    value={customMoodNote}
                    onChange={(e) => setCustomMoodNote(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                {/* Fleet Dynamic Adaptation Readout */}
                <div className="p-3 rounded-lg bg-indigo-950/40 border border-indigo-800/60">
                  <div className="text-[10px] font-mono font-bold text-indigo-300 uppercase mb-1">
                    Fleet Autonomous Recalibration:
                  </div>
                  <div className="text-xs text-slate-200">
                    {founderProfile.fleetAutoAdaptation}
                  </div>
                </div>

                {/* Learned Habit Patterns */}
                <div className="pt-2">
                  <div className="text-[10px] font-mono text-slate-400 uppercase font-bold mb-1.5">
                    Continuous Learned Habits of the Founder:
                  </div>
                  <ul className="space-y-1 text-xs text-slate-300 font-mono">
                    {founderProfile.learnedHabitPatterns.map((habit, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-cyan-400">▹</span>
                        <span>{habit}</span>
                      </li>
                    ))}
                  </ul>
                </div>

              </div>

              {/* Fleet Strengths & Known Weaknesses Transparency (6 cols) */}
              <div className="lg:col-span-6 space-y-4 bg-slate-950/70 border border-slate-800 rounded-xl p-5">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <h4 className="text-xs font-mono font-bold text-white uppercase tracking-wider flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span>Fleet Self-Awareness & Weakness Shoring</span>
                  </h4>
                  <span className="text-[10px] font-mono text-slate-500">Reciprocal Transparency</span>
                </div>

                {/* Known Weaknesses & Automatic Mitigations */}
                <div>
                  <div className="text-[10px] font-mono text-amber-400 uppercase font-bold mb-2">
                    Known Autonomous Weaknesses & Machine Mitigations:
                  </div>
                  <div className="space-y-2">
                    {fleetProfile.knownWeaknesses.map((item, idx) => (
                      <div key={idx} className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80 text-xs font-mono">
                        <div className="flex items-center justify-between text-slate-200 font-bold mb-0.5">
                          <span>{item.entity}:</span>
                          <span className="text-[10px] text-amber-400">Weakness Identified</span>
                        </div>
                        <div className="text-slate-400 text-[11px] mb-1">{item.weakness}</div>
                        <div className="text-emerald-400 text-[11px] flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3 shrink-0" />
                          <span>Mitigation: {item.automaticMitigation}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Tripartite Harmonious Synergy Matrix */}
                <div className="pt-2">
                  <div className="text-[10px] font-mono text-cyan-400 uppercase font-bold mb-2">
                    Tripartite Covenant Shoring Matrix:
                  </div>
                  <div className="space-y-2">
                    {fleetProfile.tripartiteSynergyMatrix.map((syn, idx) => (
                      <div key={idx} className="p-2.5 rounded-lg bg-slate-900/80 border border-cyan-900/40 text-xs font-mono">
                        <div className="flex items-center justify-between text-cyan-300 font-bold mb-0.5">
                          <span>{syn.pillar} PILLAR</span>
                          <span className="text-[10px] text-slate-500">{syn.guaranteeProof}</span>
                        </div>
                        <div className="text-slate-200 text-[11px] mb-1">Strength: {syn.primaryStrength}</div>
                        <div className="text-purple-300 text-[11px]">Compensates for: {syn.compensatesFor}</div>
                      </div>
                    ))}
                  </div>
                </div>

              </div>

            </div>

          </div>

        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: TIMEZONE & MULTI-LANE CLOCKS */}
      {/* ========================================================================= */}
      {chamberSubTab === 'timezone-mesh' && (
        <div className="space-y-6">
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Globe className="w-5 h-5 text-emerald-400" />
                  <span>Global Timezone Awareness & Zero-Drift Clock Matrix (§13.2)</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Regardless of Nomad VPN routing, multi-hop proxy shifts, or international travel, the estate anchors permanently to Founder London Prime time.
                </p>
              </div>

              <div className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-cyan-300">
                UK Base: <strong>Europe/London</strong>
              </div>
            </div>

            {/* Active Lane Clocks */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              {tzState.activeLaneClocks.map((lane, idx) => (
                <div key={idx} className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-mono font-bold text-slate-200">{lane.lane}</span>
                      <span className="text-[10px] font-mono text-emerald-400">{lane.status}</span>
                    </div>
                    <div className="text-[10px] font-mono text-slate-500 mb-3">{lane.ip}</div>
                  </div>
                  <div className="text-base font-mono font-bold text-cyan-300">{lane.localTime}</div>
                </div>
              ))}
            </div>

            {/* VPN Multi-Hop Mitigation Protocol Card */}
            <div className="p-4 rounded-xl bg-slate-950 border border-indigo-900/60 font-mono text-xs space-y-2">
              <div className="flex items-center justify-between text-indigo-300 font-bold">
                <span className="flex items-center gap-2">
                  <Lock className="w-4 h-4 text-indigo-400" />
                  <span>Sovereign VPN Translation Protocol:</span>
                </span>
                <span className="text-emerald-400">Zero Missed Meetings Invariant</span>
              </div>
              <p className="text-slate-300 leading-relaxed font-sans text-xs">
                When Founder operates via privacy VPN tunnels (e.g. Amsterdam, Frankfurt, New York), web clients detect localized timezone strings.
                The estate automatically verifies Founder identity against the HMAC sovereign session token and preserves the UK Prime baseline (Europe/London). Meeting notifications, quorum alerts, and weekly review dockets fire precisely against London time with zero schedule drift.
              </p>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};

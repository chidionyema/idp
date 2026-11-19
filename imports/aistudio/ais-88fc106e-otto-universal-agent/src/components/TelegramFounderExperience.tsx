import React, { useState, useEffect } from 'react';
import { 
  Send, 
  Mic, 
  MicOff, 
  Volume2, 
  VolumeX, 
  CheckCheck, 
  ShieldCheck, 
  Clock, 
  Sparkles, 
  Moon, 
  AlertCircle,
  Play,
  RotateCcw,
  Check,
  ChevronRight
} from 'lucide-react';
import { TelegramMessage } from '../types/otto';

interface TelegramFounderExperienceProps {
  onTriggerCaptcha?: () => void;
}

export const TelegramFounderExperience: React.FC<TelegramFounderExperienceProps> = ({ onTriggerCaptcha }) => {
  const [messages, setMessages] = useState<TelegramMessage[]>([
    {
      id: 'msg-1',
      sender: 'founder',
      type: 'text',
      text: 'What is blocking deployment to production right now?',
      timestamp: '17:04'
    },
    {
      id: 'msg-2',
      sender: 'otto',
      type: 'text',
      text: 'Cloud runner host credential was missing. Recovered via Bitwarden host job in 18s. Production gate is green and ready.',
      timestamp: '17:04',
      proofHash: 'sha256:77bc0918'
    },
    {
      id: 'msg-3',
      sender: 'founder',
      type: 'text',
      text: 'Ship PR-1084 through the airlock.',
      timestamp: '17:05'
    },
    {
      id: 'msg-4',
      sender: 'otto',
      type: 'decision',
      text: 'Governance Gate: PR-1084 Airlock Merge',
      timestamp: '17:05',
      decision: {
        title: 'PR-1084 Airlock Merge Approval',
        facts: [
          'All 42 test suite signatures cryptographically verified by blind verifier.',
          'Zero breaking changes to outbox-state schema.',
          'Peer consensus: DeepSeek + Gemini + Otto Lead signed.'
        ],
        recommendation: 'Merge to propose/argon-airlock and trigger automated staging deployment.',
        options: [
          { id: 'opt-approve', label: 'Approve & Sign Airlock', action: 'approve', variant: 'primary' },
          { id: 'opt-inspect', label: 'Hold for Review', action: 'hold', variant: 'secondary' }
        ]
      }
    }
  ]);

  const [inputText, setInputText] = useState('');
  const [isRecordingVoice, setIsRecordingVoice] = useState(false);
  const [isAudioMuted, setIsAudioMuted] = useState(false);
  const [quietHoursActive, setQuietHoursActive] = useState(false);
  const [interruptionsCount, setInterruptionsCount] = useState(1); // max 3/hour
  const [activeProgressMsgId, setActiveProgressMsgId] = useState<string | null>(null);

  // Play synthetic voice for Otto using browser SpeechSynthesis
  const speakVoice = (text: string) => {
    if (isAudioMuted || typeof window === 'undefined' || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn('Speech synthesis unavailable', e);
    }
  };

  const handleSendMessage = (textToSend?: string, isVoice = false) => {
    const text = textToSend || inputText;
    if (!text.trim()) return;

    const newFounderMsgId = 'msg-' + Date.now();
    const newFounderMsg: TelegramMessage = {
      id: newFounderMsgId,
      sender: 'founder',
      type: isVoice ? 'voice' : 'text',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      audioDuration: isVoice ? '0:04' : undefined
    };

    setMessages(prev => [...prev, newFounderMsg]);
    setInputText('');

    // Rule: Ack within 1 second!
    const progressMsgId = 'msg-progress-' + Date.now();
    setActiveProgressMsgId(progressMsgId);

    setTimeout(() => {
      // Step 1: In-place editing progress message
      const progressMsg: TelegramMessage = {
        id: progressMsgId,
        sender: 'otto',
        type: 'progress',
        text: 'Acknowledged. Executing request...',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        progress: {
          currentStep: 1,
          totalSteps: 3,
          stepName: 'Inspecting estate outbox-state',
          secondsRemaining: 4,
          statusText: 'Acknowledged (410ms) · Step 1 of 3'
        }
      };

      setMessages(prev => [...prev, progressMsg]);

      // Edit progress in-place to Step 2
      setTimeout(() => {
        setMessages(prev =>
          prev.map(m =>
            m.id === progressMsgId
              ? {
                  ...m,
                  progress: {
                    currentStep: 2,
                    totalSteps: 3,
                    stepName: 'Synthesizing verified outcome across peers',
                    secondsRemaining: 2,
                    statusText: 'Peer consensus verified · Step 2 of 3'
                  }
                }
              : m
          )
        );

        // Edit progress in-place to Final Stated Outcome (VIP Rule: max 3 lines, outcome first)
        setTimeout(() => {
          const outcomeText = `Task complete with machine proof. Verified across 5 peers and committed to outbox-state. All systems nominal.`;
          
          setMessages(prev =>
            prev.map(m =>
              m.id === progressMsgId
                ? {
                    id: progressMsgId,
                    sender: 'otto',
                    type: 'text',
                    text: outcomeText,
                    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                    proofHash: 'sha256:' + Math.random().toString(16).substring(2, 10)
                  }
                : m
            )
          );
          setActiveProgressMsgId(null);
          speakVoice(outcomeText);
        }, 1500);
      }, 1200);
    }, 400); // 400ms acknowledgment (< 1s bar!)
  };

  const handleDecisionClick = (msgId: string, optionId: string) => {
    setMessages(prev =>
      prev.map(m => {
        if (m.id === msgId && m.decision) {
          return {
            ...m,
            decision: {
              ...m.decision,
              resolvedOption: optionId
            }
          };
        }
        return m;
      })
    );

    const followUpId = 'msg-decision-result-' + Date.now();
    const resultText = optionId === 'opt-approve'
      ? 'Airlock signature written and merged to propose/argon-airlock. Gate green.'
      : 'Merge held. Post-mortem logged to memory/session-review.';

    setMessages(prev => [
      ...prev,
      {
        id: followUpId,
        sender: 'otto',
        type: 'text',
        text: resultText,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        proofHash: 'sha256:88bc9219'
      }
    ]);
    speakVoice(resultText);
  };

  return (
    <div className="space-y-6">
      {/* Telegram VIP Standards Banner */}
      <div className="rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950 p-6 shadow-2xl">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-500/10 border border-sky-500/20 text-sky-300 text-xs font-mono mb-2">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>SECTION 5: FOUNDER VIP TELEGRAM CONCIERGE STANDARD</span>
            </div>
            <h2 className="text-2xl font-bold text-white font-display">
              Telegram VIP Experience Simulator
            </h2>
            <p className="text-sm text-slate-400 max-w-2xl mt-1">
              The founder talks to Otto like a <span className="text-sky-400 font-semibold">Chief of Staff</span>. Outcome first, three lines at most, <span className="text-rose-400 font-semibold">zero tool names or file paths</span>. Acknowledged within 1 second and edited in place with live progress.
            </p>
          </div>

          {/* Quiet Mode & Budget Controls */}
          <div className="flex flex-wrap items-center gap-3 bg-slate-950/80 p-3 rounded-xl border border-slate-800">
            <div className="text-xs font-mono">
              <span className="text-slate-400">Budget: </span>
              <span className="text-emerald-400 font-bold">{interruptionsCount}/3</span>
              <span className="text-slate-500 text-[10px]"> int/hr</span>
            </div>

            <button
              onClick={() => setQuietHoursActive(!quietHoursActive)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                quietHoursActive
                  ? 'bg-purple-950/40 text-purple-300 border-purple-600'
                  : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-white'
              }`}
            >
              <Moon className="w-3.5 h-3.5" />
              <span>{quietHoursActive ? 'Quiet Mode ON (Only Breaches)' : 'Quiet Mode (22:00-08:00)'}</span>
            </button>

            <button
              onClick={() => setIsAudioMuted(!isAudioMuted)}
              className={`p-2 rounded-lg text-xs border transition-colors ${
                isAudioMuted
                  ? 'bg-rose-950/40 text-rose-300 border-rose-800'
                  : 'bg-slate-900 text-slate-300 border-slate-800 hover:text-white'
              }`}
              title="Toggle Voice Synthesis"
            >
              {isAudioMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Telegram Chat Surface Container */}
      <div className="max-w-3xl mx-auto rounded-2xl border border-slate-800/80 bg-slate-950 shadow-2xl overflow-hidden flex flex-col h-[600px]">
        {/* Telegram Header */}
        <div className="p-3.5 bg-slate-900/90 border-b border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center font-bold text-white shadow-md">
                O
              </div>
              <div className="w-3 h-3 rounded-full bg-emerald-400 border-2 border-slate-950 absolute bottom-0 right-0" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-sm text-white">Otto Core</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-sky-500/20 text-sky-300 font-mono">
                  BOT · VIP CONCIERGE
                </span>
              </div>
              <div className="text-[11px] text-emerald-400">
                online · response latency &lt; 450ms
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">
              1-Tap Card Engine
            </span>
          </div>
        </div>

        {/* Message Stream */}
        <div className="flex-1 p-4 overflow-y-auto space-y-4 bg-slate-950/60">
          {messages.map(msg => {
            const isFounder = msg.sender === 'founder';

            return (
              <div
                key={msg.id}
                className={`flex flex-col ${isFounder ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`max-w-[85%] sm:max-w-[75%] rounded-2xl p-3.5 text-sm transition-all shadow-md ${
                    isFounder
                      ? 'bg-sky-600 text-white rounded-br-none'
                      : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none'
                  }`}
                >
                  {/* Voice note indicator */}
                  {msg.type === 'voice' && (
                    <div className="flex items-center gap-2 mb-1.5 pb-1.5 border-b border-white/20 text-xs font-mono">
                      <Mic className="w-3.5 h-3.5" />
                      <span>Voice memo ({msg.audioDuration})</span>
                    </div>
                  )}

                  {/* Message body text */}
                  <div className="leading-relaxed whitespace-pre-wrap">{msg.text}</div>

                  {/* Progress Indicator (Edited in place) */}
                  {msg.type === 'progress' && msg.progress && (
                    <div className="mt-3 p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 font-mono text-xs space-y-2">
                      <div className="flex items-center justify-between text-cyan-400 font-medium">
                        <span>{msg.progress.statusText}</span>
                        <span>{msg.progress.secondsRemaining}s left</span>
                      </div>
                      <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                        <div
                          className="bg-cyan-400 h-full transition-all duration-500 rounded-full"
                          style={{ width: `${(msg.progress.currentStep / msg.progress.totalSteps) * 100}%` }}
                        />
                      </div>
                      <div className="text-[11px] text-slate-400">{msg.progress.stepName}</div>
                    </div>
                  )}

                  {/* 2-Button Decision Card */}
                  {msg.type === 'decision' && msg.decision && (
                    <div className="mt-3 p-3 rounded-xl bg-slate-950 border border-slate-700/80 space-y-2.5 text-xs">
                      <div className="font-semibold text-white text-sm">
                        {msg.decision.title}
                      </div>

                      <div className="space-y-1 text-slate-300">
                        {msg.decision.facts.map((fact, idx) => (
                          <div key={idx} className="flex items-start gap-1.5 text-[11px]">
                            <span className="text-cyan-400 font-bold">•</span>
                            <span>{fact}</span>
                          </div>
                        ))}
                      </div>

                      <div className="p-2 rounded bg-indigo-950/30 border border-indigo-800/40 text-[11px] text-indigo-300">
                        <span className="font-bold">Otto Recommendation: </span>
                        {msg.decision.recommendation}
                      </div>

                      {/* Action buttons */}
                      <div className="grid grid-cols-2 gap-2 pt-1">
                        {msg.decision.options.map(opt => {
                          const isChosen = msg.decision?.resolvedOption === opt.id;
                          return (
                            <button
                              key={opt.id}
                              onClick={() => handleDecisionClick(msg.id, opt.id)}
                              disabled={!!msg.decision?.resolvedOption}
                              className={`py-2 px-3 rounded-lg font-semibold text-xs transition-all flex items-center justify-center gap-1.5 ${
                                isChosen
                                  ? 'bg-emerald-600 text-white'
                                  : msg.decision?.resolvedOption
                                  ? 'opacity-40 bg-slate-800 text-slate-500'
                                  : opt.variant === 'primary'
                                  ? 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold shadow-md shadow-cyan-500/20'
                                  : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700'
                              }`}
                            >
                              {isChosen && <Check className="w-3.5 h-3.5" />}
                              <span>{opt.label}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Timestamp and proof hash */}
                  <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400">
                    <span className="font-mono">{msg.timestamp}</span>
                    {msg.proofHash && (
                      <span className="text-emerald-400 font-mono flex items-center gap-1">
                        <CheckCheck className="w-3 h-3" />
                        {msg.proofHash}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Preset Prompt Suggestions */}
        <div className="p-2 bg-slate-900/60 border-t border-slate-800/60 flex gap-2 overflow-x-auto no-scrollbar">
          {[
            'Deploy argon-sync PR-419 to staging',
            'Run cross-vendor peer sync test',
            'Trigger Luxury CAPTCHA test flow'
          ].map((prompt, i) => (
            <button
              key={i}
              onClick={() => {
                if (prompt.includes('CAPTCHA')) {
                  if (onTriggerCaptcha) onTriggerCaptcha();
                } else {
                  handleSendMessage(prompt);
                }
              }}
              className="px-2.5 py-1 rounded-full bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-[11px] whitespace-nowrap transition-colors border border-slate-700/60 flex items-center gap-1"
            >
              <span>{prompt}</span>
              <ChevronRight className="w-3 h-3 text-slate-400" />
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-3 bg-slate-900 border-t border-slate-800 flex items-center gap-2">
          <button
            onClick={() => {
              if (!isRecordingVoice) {
                setIsRecordingVoice(true);
                setTimeout(() => {
                  setIsRecordingVoice(false);
                  handleSendMessage('Voice note: Verify peer agent health on bus.', true);
                }, 2000);
              }
            }}
            className={`p-2.5 rounded-full transition-all ${
              isRecordingVoice
                ? 'bg-rose-600 text-white animate-pulse'
                : 'bg-slate-800 text-slate-300 hover:text-white'
            }`}
            title="Record Voice Note"
          >
            <Mic className="w-4 h-4" />
          </button>

          <input
            type="text"
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSendMessage()}
            placeholder={isRecordingVoice ? 'Listening to founder voice...' : 'Message Otto (Outcome first, 3 lines max)...'}
            className="flex-1 bg-slate-950 text-white text-xs rounded-xl px-3.5 py-2.5 border border-slate-800 focus:outline-none focus:border-cyan-500 font-sans"
          />

          <button
            onClick={() => handleSendMessage()}
            disabled={!inputText.trim()}
            className="p-2.5 rounded-full bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold transition-all disabled:opacity-40 disabled:hover:bg-sky-500"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

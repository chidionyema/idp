import React, { useState } from 'react';
import {
  Inbox,
  Send,
  Play,
  RotateCcw,
  CheckCircle2,
  Plus,
  Cpu,
} from 'lucide-react';
import {
  SpecialistAgent,
  ProtocolEvent,
  getNextCanonicalEvent,
} from '../lib/protocolEngine';

interface SpecialistFleetViewProps {
  agents: SpecialistAgent[];
  onStepAgent: (agentId: string, event: ProtocolEvent) => {
    valid: boolean;
    reason: string;
  };
  onEnqueueInboxMessage: (
    agentId: string,
    sender: string,
    eventType: ProtocolEvent,
    payloadSummary: string
  ) => void;
  onProcessInboxItem: (agentId: string, messageId: string) => void;
}

export const SpecialistFleetView: React.FC<SpecialistFleetViewProps> = ({
  agents,
  onStepAgent,
  onEnqueueInboxMessage,
  onProcessInboxItem,
}) => {
  const [selectedAgentId, setSelectedAgentId] = useState<string>(agents[0]?.id || 'SPC-ESTATE-01');
  const [senderInput, setSenderInput] = useState<string>('Estate Registry Event Bus');
  const [eventTypeInput, setEventTypeInput] = useState<ProtocolEvent>('ENQUEUE_INBOX');
  const [payloadInput, setPayloadInput] = useState<string>('');
  const [formError, setFormError] = useState<string>('');
  const [lastTransitionFeedback, setLastTransitionFeedback] = useState<string>('');

  const selectedAgent =
    agents.find((a) => a.id === selectedAgentId) || agents[0];

  const handleDispatchInbox = (e: React.FormEvent) => {
    e.preventDefault();
    if (!payloadInput.trim() || payloadInput.trim().length < 8) {
      setFormError('Please enter an explicit estate instruction payload (at least 8 characters).');
      return;
    }
    if (!senderInput.trim()) {
      setFormError('Sender bus identifier is required.');
      return;
    }
    setFormError('');
    onEnqueueInboxMessage(
      selectedAgent.id,
      senderInput.trim(),
      eventTypeInput,
      payloadInput.trim()
    );
    setPayloadInput('');
    setLastTransitionFeedback(
      `Enqueued ${eventTypeInput} message into ${selectedAgent.id} Private Inbox.`
    );
  };

  const handleStep = (event: ProtocolEvent) => {
    const res = onStepAgent(selectedAgent.id, event);
    setLastTransitionFeedback(res.reason);
  };

  const nextCanonical = getNextCanonicalEvent(selectedAgent.machineState);

  return (
    <div className="space-y-8">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-5 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <div className="text-xs font-medium text-slate-500 dark:text-slate-400">
            Autonomous Estate Fleet · Private Inbox & Outbox Architecture
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 mt-1">
            Headless Specialist Teams & Queue Isolation
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1 max-w-3xl">
            Every specialist team runs inside an isolated Quad-Layer container with zero laptop dependency. Work enters strictly via signed Private Inbox events and exits as verified proof bundles in the Private Outbox.
          </p>
        </div>
      </div>

      {/* Specialist Selector Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {agents.map((agent) => {
          const isSelected = agent.id === selectedAgent.id;
          const pendingInbox = agent.inbox.filter((m) => !m.processed).length;
          return (
            <button
              key={agent.id}
              type="button"
              onClick={() => {
                setSelectedAgentId(agent.id);
                setLastTransitionFeedback('');
                setFormError('');
              }}
              className={`text-left p-4 rounded-lg border transition-colors cursor-pointer ${
                isSelected
                  ? 'bg-slate-900 text-white border-slate-900 dark:bg-slate-100 dark:text-slate-900 dark:border-slate-100'
                  : 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/60'
              }`}
            >
              <div className="flex items-center justify-between text-xs font-mono opacity-80">
                <span>{agent.id}</span>
                <span>{agent.protocolId}</span>
              </div>
              <div className="font-semibold text-sm mt-1.5 truncate">
                {agent.name}
              </div>
              <div className="text-xs opacity-75 mt-2 font-mono tabular-nums">
                State: {agent.machineState}
              </div>
              <div className="text-xs opacity-75 mt-0.5 font-mono tabular-nums">
                Inbox: {pendingInbox} pending · Outbox: {agent.outbox.length}
              </div>
            </button>
          );
        })}
      </div>

      {/* Selected Specialist Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left 5 Cols: Quad-Layer Runtime & State Machine Control */}
        <div className="lg:col-span-5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg p-6 space-y-6">
          <div className="space-y-1 border-b border-slate-200 dark:border-slate-800 pb-4">
            <div className="text-xs font-mono text-slate-500 dark:text-slate-400">
              {selectedAgent.id} · {selectedAgent.squad}
            </div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
              {selectedAgent.name}
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              {selectedAgent.estateDomain}
            </p>
          </div>

          {/* Quad-Layer Configuration Spec */}
          <div className="space-y-3 text-xs">
            <div className="font-semibold text-slate-900 dark:text-slate-100">
              Quad-Layer & Agent Kit Binding
            </div>
            <div className="grid grid-cols-1 gap-2.5">
              <div className="p-3 rounded-md bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                <div className="text-slate-500 dark:text-slate-400">
                  1. Protocol Specification
                </div>
                <div className="font-mono font-medium text-slate-900 dark:text-slate-100 mt-0.5">
                  {selectedAgent.quadLayerConfig.protocolSpec}
                </div>
              </div>
              <div className="p-3 rounded-md bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                <div className="text-slate-500 dark:text-slate-400">
                  2. Event-Driven State Machine
                </div>
                <div className="font-mono font-medium text-slate-900 dark:text-slate-100 mt-0.5">
                  {selectedAgent.quadLayerConfig.stateMachineSpec} · Current: {selectedAgent.machineState}
                </div>
              </div>
              <div className="p-3 rounded-md bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                <div className="text-slate-500 dark:text-slate-400">
                  3. Persistent Estate Memory Store
                </div>
                <div className="font-mono font-medium text-slate-900 dark:text-slate-100 mt-0.5">
                  {selectedAgent.quadLayerConfig.memoryStoreId} ({selectedAgent.memoryKeys} indexed keys)
                </div>
              </div>
              <div className="p-3 rounded-md bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                <div className="text-slate-500 dark:text-slate-400">
                  4. Headless Execution & Laptop Dependency
                </div>
                <div className="font-mono font-medium text-emerald-700 dark:text-emerald-400 mt-0.5">
                  {selectedAgent.quadLayerConfig.agentKitVersion} · {selectedAgent.laptopDependency}
                </div>
              </div>
            </div>
          </div>

          {/* Deterministic State Transition Controls */}
          <div className="space-y-3 pt-2 border-t border-slate-200 dark:border-slate-800">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-900 dark:text-slate-100">
                Step Headless State Machine
              </span>
              <span className="font-mono text-slate-500 dark:text-slate-400">
                State: {selectedAgent.machineState}
              </span>
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => handleStep(nextCanonical)}
                className="px-3.5 py-2 text-xs font-semibold text-white bg-slate-900 dark:bg-slate-100 dark:text-slate-900 rounded-lg hover:bg-slate-800 dark:hover:bg-white transition-colors inline-flex items-center gap-1.5 cursor-pointer"
              >
                <Play className="w-3.5 h-3.5" />
                <span>Advance: {nextCanonical}</span>
              </button>

              <button
                type="button"
                onClick={() => handleStep('RESET_HEADLESS')}
                className="px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors inline-flex items-center gap-1.5 cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset to IDLE</span>
              </button>
            </div>

            {lastTransitionFeedback && (
              <div
                role="status"
                className="p-3 rounded-md bg-slate-100 dark:bg-slate-800 text-xs font-mono text-slate-800 dark:text-slate-200"
              >
                {lastTransitionFeedback}
              </div>
            )}
          </div>
        </div>

        {/* Right 7 Cols: Private Inbox & Private Outbox Queues */}
        <div className="lg:col-span-7 space-y-6">
          {/* Private Inbox Queue + Enqueue Form */}
          <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
                  <Inbox className="w-4 h-4 text-slate-500" />
                  <span>Private Inbox Queue ({selectedAgent.inbox.length})</span>
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Asynchronous event queue consumed headlessly by {selectedAgent.id}
                </p>
              </div>
            </div>

            {/* Inbox Messages Table */}
            <div className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
              {selectedAgent.inbox.map((msg) => (
                <div
                  key={msg.id}
                  className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2 font-mono text-slate-500 dark:text-slate-400">
                      <span className="font-semibold text-slate-900 dark:text-slate-100">
                        {msg.id}
                      </span>
                      <span aria-hidden="true">·</span>
                      <span>{msg.eventType}</span>
                      <span aria-hidden="true">·</span>
                      <span>From: {msg.sender}</span>
                      <span aria-hidden="true">·</span>
                      <span>{msg.timestamp}</span>
                    </div>
                    <div className="text-slate-800 dark:text-slate-200 font-medium">
                      {msg.payloadSummary}
                    </div>
                  </div>

                  <div className="shrink-0">
                    {msg.processed ? (
                      <span className="inline-flex items-center gap-1 text-emerald-700 dark:text-emerald-400 font-medium">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Consumed</span>
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => {
                          onProcessInboxItem(selectedAgent.id, msg.id);
                          setLastTransitionFeedback(
                            `Consumed Inbox event ${msg.id} (${msg.eventType}) and updated state machine.`
                          );
                        }}
                        className="px-3 py-1.5 text-xs font-semibold text-white bg-slate-900 dark:bg-slate-100 dark:text-slate-900 rounded-md hover:bg-slate-800 transition-colors cursor-pointer"
                      >
                        Consume & Execute Event
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Form to Enqueue New Private Inbox Event */}
            <form
              onSubmit={handleDispatchInbox}
              className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-3"
            >
              <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                Dispatch Signed Event to Private Inbox
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label
                    htmlFor="inbox-sender-input"
                    className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1"
                  >
                    Event Sender Bus
                  </label>
                  <input
                    id="inbox-sender-input"
                    type="text"
                    value={senderInput}
                    onChange={(e) => setSenderInput(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                  />
                </div>
                <div>
                  <label
                    htmlFor="inbox-event-select"
                    className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1"
                  >
                    Protocol Event Trigger
                  </label>
                  <select
                    id="inbox-event-select"
                    value={eventTypeInput}
                    onChange={(e) => setEventTypeInput(e.target.value as ProtocolEvent)}
                    className="w-full px-3 py-2 text-xs rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                  >
                    <option value="ENQUEUE_INBOX">ENQUEUE_INBOX</option>
                    <option value="ACQUIRE_CLAIM">ACQUIRE_CLAIM</option>
                    <option value="RUN_AGENT_KIT">RUN_AGENT_KIT</option>
                    <option value="ATTACH_PROOF">ATTACH_PROOF</option>
                    <option value="DISPATCH_OUTBOX">DISPATCH_OUTBOX</option>
                    <option value="RECORD_YIELD">RECORD_YIELD</option>
                  </select>
                </div>
              </div>

              <div>
                <label
                  htmlFor="inbox-payload-input"
                  className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1"
                >
                  Estate Instruction Payload
                </label>
                <div className="flex flex-col sm:flex-row gap-2">
                  <input
                    id="inbox-payload-input"
                    type="text"
                    placeholder="e.g., Audit Q4 roof replacement CapEx recovery caps for Parcel B"
                    value={payloadInput}
                    onChange={(e) => setPayloadInput(e.target.value)}
                    className="flex-1 px-3 py-2 text-xs rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                  />
                  <button
                    type="submit"
                    className="px-4 py-2 text-xs font-semibold text-white bg-slate-900 dark:bg-slate-100 dark:text-slate-900 rounded-md hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0 inline-flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Enqueue to Private Inbox</span>
                  </button>
                </div>
              </div>

              {formError && (
                <p role="alert" className="text-xs text-rose-600 dark:text-rose-400 font-medium">
                  {formError}
                </p>
              )}
            </form>
          </div>

          {/* Private Outbox Queue */}
          <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
                  <Send className="w-4 h-4 text-slate-500" />
                  <span>Private Outbox Queue ({selectedAgent.outbox.length})</span>
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Signed proof bundles and yield snapshots emitted autonomously upon protocol completion
                </p>
              </div>
            </div>

            <div className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
              {selectedAgent.outbox.map((out) => (
                <div key={out.id} className="py-3 space-y-1">
                  <div className="flex flex-wrap items-center justify-between gap-2 font-mono text-slate-500 dark:text-slate-400">
                    <span>
                      <strong className="text-slate-900 dark:text-slate-100">{out.id}</strong> · {out.eventType} → {out.recipient}
                    </span>
                    <span>{out.timestamp}</span>
                  </div>
                  <div className="font-mono text-slate-800 dark:text-slate-200">
                    Proof: {out.proofRef}
                  </div>
                  <div className="text-emerald-700 dark:text-emerald-400 font-medium">
                    {out.yieldSnapshot}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { promptsAPI, PromptConfig, chatAPI, authAPI, sessionAPI, Message, PhaseStatus } from '@/lib/api';

// ---------------------------------------------------------------------------
// Section config — only prompts used in the guided study flow
// ---------------------------------------------------------------------------
interface SectionDef {
  key: keyof PromptConfig;
  label: string;
  description: string;
  type: 'textarea' | 'string-list' | 'string-map' | 'phase-bank';
}

const CONVERSATION_SECTIONS: SectionDef[] = [
  { key: 'phase_question_banks', label: 'Phase Question Banks', description: 'The actual questions asked during each phase (4 per phase, 12 total). The companion weaves these into conversation one at a time, advancing after the participant gives a sufficient answer.', type: 'phase-bank' },
  { key: 'phase_opening_messages', label: 'Phase Opening Messages', description: 'The first message the companion sends at the start of each phase. Use {first_question} where the first question should appear. "fallback" is used if a phase has no questions.', type: 'string-map' },
  { key: 'guided_system_prompt', label: 'Guided Chat System Prompt', description: 'The main personality and behavior instructions sent to the LLM on every guided conversation turn. This is the most impactful prompt to tune — it controls tone, style, and constraints. Use {condition} for the memory condition.', type: 'textarea' },
  { key: 'phase_completion_prompt', label: 'Phase Completion Prompt', description: 'Sent as the system prompt when the participant finishes the last question of the entire study (phase 3 complete). Use {phase} for the phase number.', type: 'textarea' },
  { key: 'bridge_instructions', label: 'Bridge Instructions', description: 'Optional instructions that help the companion connect a new topic to something the participant shared earlier. Each key is a question (lowercase), and the value is the bridging instruction added to the system prompt when context from prior answers exists.', type: 'string-map' },
  { key: 'followup_variants_with_prompt', label: 'Follow-up Variants (with prompt)', description: 'Canned follow-up messages used when a participant gives a very short or generic answer to a specific question. These are cycled in order before the system falls back to LLM-based assessment.', type: 'string-list' },
  { key: 'followup_variants_without_prompt', label: 'Follow-up Variants (without prompt)', description: 'Same as above, but used in free-form chat when there is no specific required question active.', type: 'string-list' },
];

const INTERNAL_SECTIONS: SectionDef[] = [
  { key: 'effort_assessment_system', label: 'Effort Assessment — System', description: 'System message for the LLM call that judges whether a participant\'s answer is sufficient or needs a follow-up question. Only fires after the canned follow-ups are exhausted.', type: 'textarea' },
  { key: 'effort_assessment_user_template', label: 'Effort Assessment — User Template', description: 'The evaluation prompt sent to the LLM to assess effort and relevance. Use {last_assistant_prompt} and {user_response} as placeholders. Must return strict JSON.', type: 'textarea' },
  { key: 'memory_extraction_system', label: 'Memory Extraction — System', description: 'System message for the LLM call that extracts factual memories from participant messages after each turn.', type: 'textarea' },
  { key: 'memory_extraction_user_template', label: 'Memory Extraction — User Template', description: 'The extraction prompt that tells the LLM what to pull from the user\'s message. Use {user_message} and {existing_context} as placeholders.', type: 'textarea' },
];

// ---------------------------------------------------------------------------
// Study-simulation test chat
// ---------------------------------------------------------------------------
function StudyChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [phaseStatus, setPhaseStatus] = useState<PhaseStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const bootstrap = useCallback(async () => {
    setError(null);
    setBootstrapping(true);
    setMessages([]);
    setPhaseStatus(null);
    setUserId(null);
    setSessionId(null);
    try {
      const qualtricsId = `playground_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
      const auth = await authAPI.qualtricsAuthenticate(qualtricsId, qualtricsId, null);
      const uid = auth.user_id;
      const sid = auth.session_id;
      setUserId(uid);
      setSessionId(sid);

      const msgs: Message[] = await sessionAPI.getMessages(sid);
      setMessages(msgs);

      const progress = await chatAPI.getProgress(uid, sid);
      setPhaseStatus(progress);
    } catch (e: any) {
      setError(`Failed to create test session: ${e.message}`);
    }
    setBootstrapping(false);
  }, []);

  useEffect(() => { bootstrap(); }, [bootstrap]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading || !userId || !sessionId) return;
    const text = input;
    setInput('');
    const userMsg: Message = { msg_id: '', session_id: sessionId, role: 'user', content: text, created_at: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);
    try {
      const resp = await chatAPI.send(userId, sessionId, text, null);
      const assistantMsg: Message = { msg_id: '', session_id: sessionId, role: 'assistant', content: resp.response, created_at: new Date().toISOString() };
      setMessages(prev => [...prev, assistantMsg]);
      if (resp.phase_status) {
        setPhaseStatus(resp.phase_status);
      }
    } catch (e: any) {
      setMessages(prev => [...prev, { msg_id: '', session_id: sessionId, role: 'assistant', content: `Error: ${e.message}`, created_at: new Date().toISOString() }]);
    }
    setLoading(false);
  };

  const handleAdvancePhase = async () => {
    if (!userId || !sessionId) return;
    setLoading(true);
    try {
      const resp = await chatAPI.advancePhase(userId, sessionId);
      const openingMsg: Message = { msg_id: '', session_id: sessionId, role: 'assistant', content: resp.opening_message, created_at: new Date().toISOString() };
      setMessages(prev => [...prev, openingMsg]);
      setPhaseStatus(resp.phase_status);
    } catch (e: any) {
      setError(`Failed to advance phase: ${e.message}`);
    }
    setLoading(false);
  };

  const phaseComplete = phaseStatus?.phase_complete ?? false;
  const studyComplete = phaseStatus?.study_complete ?? false;
  const showContinue = phaseComplete && !studyComplete;
  const chatDisabled = loading || !sessionId || studyComplete || showContinue;

  const progressLabel = (() => {
    if (!phaseStatus) return null;
    if (studyComplete) return 'Study Complete';
    const qIdx = (phaseStatus.current_prompt_index ?? phaseStatus.prompts_answered) + 1;
    if (phaseComplete) return `Phase ${phaseStatus.phase} Complete`;
    return `Phase ${phaseStatus.phase} — Question ${qIdx}/${phaseStatus.total_prompts}`;
  })();

  return (
    <div className="flex flex-col h-full">
      {/* toolbar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-200 bg-white/90 shrink-0">
        <span className="text-xs font-semibold text-gray-700">Study Simulation</span>
        <button type="button" onClick={bootstrap} disabled={bootstrapping} className="ml-auto text-xs px-3 py-1 rounded-full bg-gray-100 hover:bg-gray-200 transition disabled:opacity-50">
          New Session
        </button>
      </div>

      {/* phase progress */}
      {progressLabel && (
        <div className={`px-4 py-2 text-xs font-medium border-b shrink-0 ${
          studyComplete ? 'bg-green-50 text-green-700 border-green-200' :
          phaseComplete ? 'bg-amber-50 text-amber-700 border-amber-200' :
          'bg-blue-50 text-blue-700 border-blue-200'
        }`}>
          {progressLabel}
        </div>
      )}

      {error && <div className="px-4 py-2 text-xs text-red-600 bg-red-50 shrink-0">{error}</div>}

      {/* messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {bootstrapping && (
          <p className="text-center text-gray-400 text-sm mt-8">Setting up study session...</p>
        )}
        {!bootstrapping && messages.length === 0 && (
          <p className="text-center text-gray-400 text-sm mt-8">No messages yet.</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] px-4 py-2 rounded-2xl text-sm whitespace-pre-wrap ${
              m.role === 'user'
                ? 'bg-gradient-to-r from-[#f5e6d3] to-[#d4c5a9] text-black'
                : 'bg-white border border-gray-200 text-gray-800'
            }`}>
              {m.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 px-4 py-2 rounded-2xl text-sm text-gray-500">Thinking...</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* continue / finish banner */}
      {showContinue && (
        <div className="px-4 py-3 border-t border-amber-200 bg-amber-50 shrink-0">
          <button
            type="button"
            onClick={handleAdvancePhase}
            disabled={loading}
            className="w-full py-2 px-4 rounded-full bg-[#d4c5a9] text-black font-semibold text-sm hover:bg-[#c9b99b] transition disabled:opacity-50"
          >
            Continue to Phase {(phaseStatus?.phase ?? 0) + 1}
          </button>
        </div>
      )}

      {studyComplete && (
        <div className="px-4 py-3 border-t border-green-200 bg-green-50 text-center shrink-0">
          <p className="text-sm font-medium text-green-700">All phases complete. Click "New Session" to test again.</p>
        </div>
      )}

      {/* input */}
      <form onSubmit={send} className="border-t border-gray-200 bg-white/90 p-3 flex gap-2 shrink-0">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder={chatDisabled && !loading ? (studyComplete ? 'Study complete' : 'Phase complete — click Continue') : 'Type a message...'}
          disabled={chatDisabled}
          className="flex-1 px-4 py-2 text-sm rounded-full border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#d4c5a9] disabled:bg-gray-100"
        />
        <button type="submit" disabled={chatDisabled || !input.trim()} className="lavender-btn text-sm disabled:opacity-50">Send</button>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Collapsible section wrapper
// ---------------------------------------------------------------------------
function Section({ title, description, children, defaultOpen = false }: { title: string; description?: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden bg-white">
      <button type="button" onClick={() => setOpen(o => !o)} className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition text-sm font-semibold text-gray-700">
        {title}
        <span className={`transform transition ${open ? 'rotate-180' : ''}`}>&#9662;</span>
      </button>
      {open && (
        <div className="px-4 py-3 space-y-3">
          {description && <p className="text-xs text-gray-500 leading-relaxed bg-blue-50/60 border border-blue-100 rounded-lg px-3 py-2">{description}</p>}
          {children}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section group header
// ---------------------------------------------------------------------------
function SectionGroup({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-2">
        <h3 className="text-sm font-bold text-gray-700">{title}</h3>
        <p className="text-xs text-gray-400">{subtitle}</p>
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main playground page
// ---------------------------------------------------------------------------
export default function PlaygroundPage() {
  const [config, setConfig] = useState<PromptConfig | null>(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const cfg = await promptsAPI.get();
      setConfig(cfg);
      setDirty(false);
      setLoadError(null);
    } catch (e: any) {
      setLoadError(`Could not load prompt config: ${e.message}`);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const flash = (msg: string) => { setStatus(msg); setTimeout(() => setStatus(null), 3000); };

  const updateField = (key: keyof PromptConfig, value: any) => {
    setConfig(prev => prev ? { ...prev, [key]: value } : prev);
    setDirty(true);
  };

  const handleApply = async () => {
    if (!config) return;
    setSaving(true);
    try {
      const resp = await promptsAPI.update(config);
      setConfig(resp.config);
      setDirty(false);
      flash('Applied — chatbot now uses these prompts');
    } catch (e: any) { flash(`Error: ${e.message}`); }
    setSaving(false);
  };

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      await promptsAPI.update(config);
      await promptsAPI.save();
      setDirty(false);
      flash('Saved to server (persists across restarts)');
    } catch (e: any) { flash(`Error: ${e.message}`); }
    setSaving(false);
  };

  const handleReset = async () => {
    if (!confirm('Discard all in-memory changes and revert to saved defaults?')) return;
    setSaving(true);
    try {
      const resp = await promptsAPI.reset();
      setConfig(resp.config);
      setDirty(false);
      flash('Reset to saved defaults');
    } catch (e: any) { flash(`Error: ${e.message}`); }
    setSaving(false);
  };

  // ---------------------------------------------------------------------------
  // Render helpers
  // ---------------------------------------------------------------------------
  const renderTextarea = (key: keyof PromptConfig) => {
    const val = (config as any)?.[key] ?? '';
    return (
      <textarea
        value={val}
        onChange={e => updateField(key, e.target.value)}
        rows={Math.max(4, val.split('\n').length + 1)}
        className="w-full text-sm font-mono border border-gray-300 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-[#d4c5a9] resize-y"
      />
    );
  };

  const renderStringList = (key: keyof PromptConfig) => {
    const items: string[] = (config as any)?.[key] ?? [];
    return (
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="flex gap-2 items-start">
            <span className="text-xs text-gray-400 mt-2 shrink-0">{i + 1}.</span>
            <textarea
              value={item}
              onChange={e => {
                const next = [...items];
                next[i] = e.target.value;
                updateField(key, next);
              }}
              rows={2}
              className="flex-1 text-sm font-mono border border-gray-300 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-[#d4c5a9] resize-y"
            />
            <button type="button" onClick={() => { const next = items.filter((_, j) => j !== i); updateField(key, next); }} className="text-red-400 hover:text-red-600 text-xs mt-2 shrink-0">Remove</button>
          </div>
        ))}
        <button type="button" onClick={() => updateField(key, [...items, ''])} className="text-xs text-blue-600 hover:underline">+ Add variant</button>
      </div>
    );
  };

  const renderStringMap = (key: keyof PromptConfig) => {
    const map: Record<string, string> = (config as any)?.[key] ?? {};
    const entries = Object.entries(map);
    return (
      <div className="space-y-3">
        {entries.map(([k, v], i) => (
          <div key={i} className="border border-gray-100 rounded-lg p-3 bg-gray-50/50 space-y-1">
            <label className="text-xs font-medium text-gray-500 block">Key:</label>
            <input
              value={k}
              onChange={e => {
                const next: Record<string, string> = {};
                for (const [ek, ev] of entries) {
                  next[ek === k ? e.target.value : ek] = ev;
                }
                updateField(key, next);
              }}
              className="w-full text-xs font-mono border border-gray-300 rounded p-1.5 focus:outline-none focus:ring-1 focus:ring-[#d4c5a9]"
            />
            <label className="text-xs font-medium text-gray-500 block mt-1">Value:</label>
            <textarea
              value={v}
              onChange={e => {
                const next = { ...map, [k]: e.target.value };
                updateField(key, next);
              }}
              rows={2}
              className="w-full text-sm font-mono border border-gray-300 rounded p-1.5 focus:outline-none focus:ring-1 focus:ring-[#d4c5a9] resize-y"
            />
          </div>
        ))}
      </div>
    );
  };

  const renderPhaseBank = (key: keyof PromptConfig) => {
    const banks: Record<string, string[]> = (config as any)?.[key] ?? {};
    return (
      <div className="space-y-4">
        {Object.entries(banks).map(([phase, questions]) => (
          <div key={phase}>
            <h4 className="text-xs font-semibold text-gray-500 mb-1">Phase {phase}</h4>
            {questions.map((q, qi) => (
              <div key={qi} className="flex gap-2 items-start mb-2">
                <span className="text-xs text-gray-400 mt-2 shrink-0">Q{qi + 1}.</span>
                <textarea
                  value={q}
                  onChange={e => {
                    const next = { ...banks, [phase]: questions.map((qq, j) => j === qi ? e.target.value : qq) };
                    updateField(key, next);
                  }}
                  rows={2}
                  className="flex-1 text-sm font-mono border border-gray-300 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-[#d4c5a9] resize-y"
                />
                <button type="button" onClick={() => {
                  const next = { ...banks, [phase]: questions.filter((_, j) => j !== qi) };
                  updateField(key, next);
                }} className="text-red-400 hover:text-red-600 text-xs mt-2 shrink-0">Remove</button>
              </div>
            ))}
            <button type="button" onClick={() => {
              const next = { ...banks, [phase]: [...questions, ''] };
              updateField(key, next);
            }} className="text-xs text-blue-600 hover:underline">+ Add question</button>
          </div>
        ))}
      </div>
    );
  };

  const renderSection = (sec: SectionDef) => {
    switch (sec.type) {
      case 'textarea': return renderTextarea(sec.key);
      case 'string-list': return renderStringList(sec.key);
      case 'string-map': return renderStringMap(sec.key);
      case 'phase-bank': return renderPhaseBank(sec.key);
    }
  };

  // ---------------------------------------------------------------------------
  // Page layout
  // ---------------------------------------------------------------------------
  if (loadError) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card rounded-2xl p-8 max-w-md text-center">
          <h2 className="text-lg font-semibold mb-2">Cannot Load Prompts</h2>
          <p className="text-sm text-gray-600 mb-4">{loadError}</p>
          <button onClick={load} className="lavender-btn text-sm">Retry</button>
        </div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500">Loading prompt config...</p>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      {/* top bar */}
      <header className="shrink-0 flex items-center justify-between px-6 py-3 bg-white/90 backdrop-blur-xl border-b border-gray-200 shadow-sm">
        <h1 className="text-lg font-bold text-gray-800">Prompt Playground</h1>
        <div className="flex items-center gap-3">
          {status && <span className="text-xs text-green-700 bg-green-50 px-3 py-1 rounded-full">{status}</span>}
          {dirty && <span className="text-xs text-amber-700 bg-amber-50 px-2 py-1 rounded-full">Unsaved changes</span>}
          <button onClick={handleApply} disabled={saving} className="lavender-btn text-sm disabled:opacity-50">Apply</button>
          <button onClick={handleSave} disabled={saving} className="text-sm px-4 py-2 rounded-full bg-green-600 text-white hover:bg-green-700 transition disabled:opacity-50">Save to Server</button>
          <button onClick={handleReset} disabled={saving} className="lavender-secondary-btn text-sm disabled:opacity-50">Reset</button>
        </div>
      </header>

      {/* split pane */}
      <div className="flex-1 flex overflow-hidden">
        {/* left: editor */}
        <div className="w-1/2 border-r border-gray-200 overflow-y-auto p-5 space-y-6 bg-gray-50/30">
          <p className="text-xs text-gray-500 mb-1">
            Edit prompts below, click <strong>Apply</strong>, then test in the study simulation on the right.
            Template variables like <code className="bg-gray-100 px-1 rounded">{'{condition}'}</code>, <code className="bg-gray-100 px-1 rounded">{'{phase}'}</code>, <code className="bg-gray-100 px-1 rounded">{'{first_question}'}</code> are filled at runtime.
          </p>

          <SectionGroup title="Conversation Prompts" subtitle="Directly shape what the participant sees and hears">
            {CONVERSATION_SECTIONS.map(sec => (
              <Section key={sec.key} title={sec.label} description={sec.description} defaultOpen={sec.key === 'guided_system_prompt'}>
                {renderSection(sec)}
              </Section>
            ))}
          </SectionGroup>

          <SectionGroup title="Internal LLM Prompts" subtitle="Affect follow-up decisions and memory extraction (not directly visible to participants)">
            {INTERNAL_SECTIONS.map(sec => (
              <Section key={sec.key} title={sec.label} description={sec.description}>
                {renderSection(sec)}
              </Section>
            ))}
          </SectionGroup>
        </div>

        {/* right: study simulation chat */}
        <div className="w-1/2 flex flex-col">
          <StudyChat />
        </div>
      </div>
    </div>
  );
}

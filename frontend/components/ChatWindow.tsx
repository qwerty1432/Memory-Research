'use client';

import { useState, useRef, useEffect } from 'react';
import { Message } from '@/lib/api';
import { chatAPI, memoryAPI } from '@/lib/api';
import AiAvatar, { AssistantAvatarSettings } from '@/components/AiAvatar';

interface ChatWindowProps {
  userId: string;
  sessionId: string;
  conditionId: string;
  phase?: number | null;
  messages: Message[];
  onNewMessage: (message: Message) => void;
  onNewCandidates: (candidates: any[]) => void;
  onManualMemoryAdded: () => void;
  onPhaseStatusUpdate?: (status: {
    phase: number;
    prompts_answered: number;
    total_prompts: number;
    phase_complete: boolean;
    // Present once the entire 3-phase study is complete in single-block mode.
    study_complete?: boolean;
  } | null) => void;
  chatInputRef?: React.RefObject<HTMLInputElement>;
  assistantAvatar?: AssistantAvatarSettings;
}

export default function ChatWindow({
  userId,
  sessionId,
  conditionId,
  phase,
  messages,
  onNewMessage,
  onNewCandidates,
  onManualMemoryAdded,
  onPhaseStatusUpdate,
  chatInputRef,
  assistantAvatar,
}: ChatWindowProps) {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState('');
  const [savingMessageIndex, setSavingMessageIndex] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const internalInputRef = useRef<HTMLInputElement>(null);
  const lastMessageCountRef = useRef<number>(messages.length);
  
  // Use provided ref or internal ref
  const inputRef = chatInputRef || internalInputRef;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    // Only auto-scroll when a new message is appended.
    if (messages.length > lastMessageCountRef.current) {
      scrollToBottom();
    }
    lastMessageCountRef.current = messages.length;
  }, [messages.length]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      msg_id: '',
      session_id: sessionId,
      role: 'user',
      content: input,
      created_at: new Date().toISOString(),
    };

    onNewMessage(userMessage);
    setInput('');
    setLoading(true);
    setLoadingStatus('Thinking...');

    const MAX_ATTEMPTS = 3;
    for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
      try {
        if (attempt > 1) {
          setLoadingStatus(`Still working on it... (attempt ${attempt}/${MAX_ATTEMPTS})`);
        }
        const response = await chatAPI.send(userId, sessionId, input, phase ?? null);

        const assistantMessage: Message = {
          msg_id: '',
          session_id: sessionId,
          role: 'assistant',
          content: response.response,
          created_at: new Date().toISOString(),
        };

        onNewMessage(assistantMessage);

        if (response.memory_candidates && response.memory_candidates.length > 0) {
          onNewCandidates(response.memory_candidates);
        }
        if (onPhaseStatusUpdate) {
          onPhaseStatusUpdate(response.phase_status ?? null);
        }
        setLoading(false);
        setLoadingStatus('');
        return;
      } catch (error: any) {
        console.error(`Chat attempt ${attempt}/${MAX_ATTEMPTS} failed:`, error);
        const isTimeout = error?.code === 'ECONNABORTED' || error?.message?.includes('timeout');
        if (isTimeout && attempt < MAX_ATTEMPTS) {
          continue;
        }
        const errorMessage: Message = {
          msg_id: '',
          session_id: sessionId,
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try sending your message again.',
          created_at: new Date().toISOString(),
        };
        onNewMessage(errorMessage);
        break;
      }
    }
    setLoading(false);
    setLoadingStatus('');
  };

  const handleSaveToMemory = async (message: Message, index: number) => {
    if (savingMessageIndex !== null) return;
    setSavingMessageIndex(index);
    try {
      await memoryAPI.create({
        user_id: userId,
        session_id: sessionId,
        text: message.content,
        is_active: false,
      });
      onManualMemoryAdded();
    } catch (error) {
      console.error('Error saving memory:', error);
      alert('Failed to save memory. Please try again.');
    } finally {
      setSavingMessageIndex(null);
    }
  };

  const isUserControlled = conditionId.includes('USER');
  const avatar = assistantAvatar ?? { name: 'AI', bgColor: '#d4c5a9', symbol: '🤖' };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            Start a conversation by typing a message below.
          </div>
        )}
        {messages.map((msg, idx) => (
          <div
            key={`${msg.msg_id || msg.created_at || idx}-${idx}`}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} group`}
          >
            {msg.role !== 'user' && (
              <div className="mr-3 mt-1 flex flex-col items-center shrink-0">
                <AiAvatar settings={avatar} />
                <div className="text-[11px] text-gray-600 mt-1 max-w-[72px] truncate">
                  {avatar.name || 'AI'}
                </div>
              </div>
            )}
            <div
              className={`relative max-w-xl px-5 py-3 rounded-3xl shadow-sm ${
                msg.role === 'user'
                  ? 'bg-gradient-to-r from-[#f5e6d3] via-[#d4c5a9] to-[#c9b99b] text-black shadow-lg'
                  : 'glass-card text-[#1a1a1a]'
              }`}
            >
              {msg.role === 'user' && isUserControlled && (
                <button
                  type="button"
                  onClick={() => handleSaveToMemory(msg, idx)}
                  disabled={savingMessageIndex === idx}
                  className={`absolute -top-6 right-0 px-2 py-1 text-xs rounded-md shadow transition-opacity ${
                    savingMessageIndex === idx
                      ? 'bg-[#68d391] text-black opacity-100'
                      : 'bg-[#d4c5a9] text-black opacity-0 group-hover:opacity-100 hover:bg-[#c9b99b]'
                  }`}
                >
                  {savingMessageIndex === idx ? 'Saving...' : 'Save memory'}
                </button>
              )}
              <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="mr-3 mt-1 flex flex-col items-center shrink-0">
              <AiAvatar settings={avatar} />
            </div>
            <div className="glass-card px-4 py-2 rounded-3xl text-[#1a1a1a]">
              <p className="text-sm">{loadingStatus || 'Thinking...'}</p>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form
        onSubmit={handleSend}
        className="border-t border-white/40 bg-white/60 backdrop-blur-xl pt-4 px-4 pb-[calc(env(safe-area-inset-bottom)+1rem)] rounded-t-3xl"
      >
        <div className="flex gap-3 items-center">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 px-5 py-3 rounded-full focus:outline-none focus:ring-2 focus:ring-[#d4c5a9] border border-white/60 shadow-inner bg-white/90 text-[#1a1a1a]"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="lavender-btn disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}


'use client';

import { useState, useRef, useEffect } from 'react';
import { Message } from '@/lib/api';
import { chatAPI, memoryAPI } from '@/lib/api';

interface ChatWindowProps {
  userId: string;
  sessionId: string;
  conditionId: string;
  messages: Message[];
  onNewMessage: (message: Message) => void;
  onNewCandidates: (candidates: any[]) => void;
  onManualMemoryAdded: () => void;
  chatInputRef?: React.RefObject<HTMLInputElement>;
}

export default function ChatWindow({
  userId,
  sessionId,
  conditionId,
  messages,
  onNewMessage,
  onNewCandidates,
  onManualMemoryAdded,
  chatInputRef,
}: ChatWindowProps) {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [savingMessageIndex, setSavingMessageIndex] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const internalInputRef = useRef<HTMLInputElement>(null);
  
  // Use provided ref or internal ref
  const inputRef = chatInputRef || internalInputRef;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

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

    try {
      const response = await chatAPI.send(userId, sessionId, input);
      
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
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: Message = {
        msg_id: '',
        session_id: sessionId,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        created_at: new Date().toISOString(),
      };
      onNewMessage(errorMessage);
    } finally {
      setLoading(false);
    }
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
            <div className="glass-card px-4 py-2 rounded-3xl text-[#1a1a1a]">
              <p className="text-sm">Thinking...</p>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSend} className="border-t border-white/40 bg-white/60 backdrop-blur-xl p-4 rounded-t-3xl">
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


'use client';

import { useState, useEffect, useCallback } from 'react';
import { Memory, memoryAPI } from '@/lib/api';
import { getConditionDisclaimer } from '@/lib/conditionDisclaimer';

interface PhaseMemoryRecapProps {
  userId: string;
  sessionId: string;
  conditionId: string;
  /** Phase that just ended (1–3); drives recap query. */
  untilPhase: number;
  /** When false, recap block is hidden (e.g. new session bootstrap). */
  visible: boolean;
  onMemoriesChanged?: () => void;
}

export default function PhaseMemoryRecap({
  userId,
  sessionId,
  conditionId,
  untilPhase,
  visible,
  onMemoriesChanged,
}: PhaseMemoryRecapProps) {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');

  const isUserControlled = conditionId.includes('USER');
  const disclaimer = getConditionDisclaimer(conditionId);

  const load = useCallback(async () => {
    if (!visible || !userId || !sessionId || untilPhase < 1 || untilPhase > 3) {
      setMemories([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await memoryAPI.recap(userId, sessionId, untilPhase);
      setMemories(data);
    } catch (e: unknown) {
      console.error('Phase recap load failed:', e);
      setError('Could not load memory recap.');
      setMemories([]);
    } finally {
      setLoading(false);
    }
  }, [userId, sessionId, untilPhase, visible]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSaveEdit = async (memoryId: string) => {
    if (!isUserControlled) return;
    try {
      await memoryAPI.update(memoryId, editText);
      setEditingId(null);
      setEditText('');
      await load();
      onMemoriesChanged?.();
    } catch (e) {
      console.error('Error updating memory:', e);
    }
  };

  const handleDelete = async (memoryId: string) => {
    if (!isUserControlled) return;
    if (!confirm('Remove this memory?')) return;
    try {
      await memoryAPI.delete(memoryId);
      await load();
      onMemoriesChanged?.();
    } catch (e) {
      console.error('Error deleting memory:', e);
    }
  };

  if (!visible) return null;

  return (
    <div className="px-4 py-3 border-t border-[#e8e0f5] bg-[#faf8ff]">
      <h3 className="text-sm font-semibold text-[#1a1a1a] mb-1">
        Memories from phase {untilPhase}
      </h3>
      <p className="text-xs text-gray-600 mb-3">{disclaimer}</p>

      {loading && <p className="text-xs text-gray-500">Loading recap…</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}

      {!loading && !error && memories.length === 0 && (
        <p className="text-xs text-gray-500">No saved memories for this phase yet.</p>
      )}

      {!loading && memories.length > 0 && (
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {memories.map((memory) => (
            <div
              key={memory.memory_id}
              className={`glass-card rounded-xl p-3 ${memory.is_active ? 'bg-[#f3edff]' : 'bg-white/80'}`}
            >
              {isUserControlled && editingId === memory.memory_id ? (
                <div className="space-y-2">
                  <textarea
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    maxLength={200}
                    className="w-full px-2 py-1.5 rounded-lg border border-white/60 bg-white/90 text-xs focus:outline-none focus:ring-2 focus:ring-[#d4c5a9]"
                    rows={2}
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => handleSaveEdit(memory.memory_id)}
                      className="text-xs px-2 py-0.5 lavender-btn rounded-full"
                    >
                      Save
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setEditingId(null);
                        setEditText('');
                      }}
                      className="text-xs px-2 py-0.5 lavender-secondary-btn rounded-full"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <p className="text-sm text-[#1a1a1a]">{memory.text}</p>
                  {isUserControlled && (
                    <div className="flex gap-3 mt-1 text-xs">
                      <button
                        type="button"
                        onClick={() => {
                          setEditingId(memory.memory_id);
                          setEditText(memory.text);
                        }}
                        className="text-[#d4c5a9] hover:underline"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(memory.memory_id)}
                        className="text-red-500 hover:underline"
                      >
                        Delete
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

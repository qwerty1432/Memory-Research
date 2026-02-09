'use client';

import { useState, useEffect } from 'react';
import { Memory, memoryAPI } from '@/lib/api';

interface MemoryReviewPanelProps {
  userId: string;
  sessionId: string;
  conditionId: string;
  isOpen: boolean;
  onClose: () => void;
  candidates: Memory[];
  onCandidatesUpdate: () => void;
}

export default function MemoryReviewPanel({
  userId,
  sessionId,
  conditionId,
  isOpen,
  onClose,
  candidates,
  onCandidatesUpdate,
}: MemoryReviewPanelProps) {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);

  const isUserControlled = conditionId.includes('USER');

  useEffect(() => {
    if (isOpen) {
      loadMemories();
    }
  }, [isOpen, userId, sessionId]);

  useEffect(() => {
    // Add new candidates to the list
    if (candidates.length > 0) {
      setMemories((prev) => {
        const existingIds = new Set(prev.map((m) => m.memory_id));
        const newCandidates = candidates.filter((c) => !existingIds.has(c.memory_id));
        return [...prev, ...newCandidates];
      });
    }
  }, [candidates]);

  const loadMemories = async () => {
    try {
      const allMemories = await memoryAPI.get(userId, sessionId);
      setMemories(allMemories);
    } catch (error) {
      console.error('Error loading memories:', error);
    }
  };

  const handleToggle = (memoryId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(memoryId)) {
        next.delete(memoryId);
      } else {
        next.add(memoryId);
      }
      return next;
    });
  };

  const handleEdit = (memory: Memory) => {
    setEditingId(memory.memory_id);
    setEditText(memory.text);
  };

  const handleSaveEdit = async (memoryId: string) => {
    try {
      await memoryAPI.update(memoryId, editText);
      await loadMemories();
      setEditingId(null);
      setEditText('');
    } catch (error) {
      console.error('Error updating memory:', error);
    }
  };

  const handleDelete = async (memoryId: string) => {
    if (!confirm('Are you sure you want to delete this memory?')) return;
    try {
      await memoryAPI.delete(memoryId);
      await loadMemories();
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(memoryId);
        return next;
      });
      onCandidatesUpdate();
    } catch (error) {
      console.error('Error deleting memory:', error);
    }
  };

  const handleBatchSave = async () => {
    if (!isUserControlled) return;
    setLoading(true);
    try {
      const updates = Array.from(selected).map((memoryId) => ({
        memory_id: memoryId,
        is_active: true,
      }));
      await memoryAPI.batchUpdate(updates);
      await loadMemories();
      setSelected(new Set());
      onCandidatesUpdate();
    } catch (error) {
      console.error('Error saving memories:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const candidatesToShow = memories.filter((m) => !m.is_active);
  const approvedMemories = memories.filter((m) => m.is_active);

  return (
    <div className="fixed right-0 top-0 h-full w-[28rem] bg-white/80 backdrop-blur-xl border-l border-white/50 z-50 flex flex-col shadow-2xl">
      <div className="p-5 border-b border-white/60 flex justify-between items-center bg-white/60 backdrop-blur-xl">
        <div>
          <h2 className="text-lg font-semibold text-[#1a1a1a]">Memory Review</h2>
          <p className="text-xs text-[#6c4c99]">Approve or edit what the assistant remembers.</p>
        </div>
        <button
          onClick={onClose}
          className="lavender-secondary-btn px-3 py-1 rounded-full text-xs"
        >
          Close
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {isUserControlled && candidatesToShow.length > 0 && (
          <div>
            <h3 className="font-medium mb-2 text-[#1a1a1a]">New Memory Candidates</h3>
            <div className="space-y-2">
              {candidatesToShow.map((memory) => (
                <div
                  key={memory.memory_id}
                  className="glass-card rounded-2xl p-4 space-y-2"
                >
                  {editingId === memory.memory_id ? (
                    <div className="space-y-2">
                      <textarea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        maxLength={200}
                        className="w-full px-3 py-2 rounded-xl border border-white/60 bg-white/80 text-sm focus:outline-none focus:ring-2 focus:ring-[#d4c5a9]"
                        rows={2}
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleSaveEdit(memory.memory_id)}
                          className="text-xs px-3 py-1 lavender-btn rounded-full"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => {
                            setEditingId(null);
                            setEditText('');
                          }}
                          className="text-xs px-3 py-1 lavender-secondary-btn rounded-full"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-start gap-2">
                        <input
                          type="checkbox"
                          checked={selected.has(memory.memory_id)}
                          onChange={() => handleToggle(memory.memory_id)}
                          className="mt-1 accent-[#d4c5a9]"
                        />
                        <p className="text-sm flex-1 text-[#1a1a1a]">{memory.text}</p>
                      </div>
                      <div className="flex gap-4 text-xs">
                        <button
                          onClick={() => handleEdit(memory)}
                          className="text-[#d4c5a9] hover:underline"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(memory.memory_id)}
                          className="text-red-500 hover:underline"
                        >
                          Delete
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {approvedMemories.length > 0 && (
          <div>
            <h3 className="font-medium mb-2 text-[#1a1a1a]">Saved Memories</h3>
            <div className="space-y-2">
              {approvedMemories.map((memory) => (
                <div
                  key={memory.memory_id}
                  className="glass-card rounded-2xl p-4 space-y-2 bg-[#f3edff]"
                >
                  {editingId === memory.memory_id ? (
                    <div className="space-y-2">
                      <textarea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        maxLength={200}
                        className="w-full px-3 py-2 rounded-xl border border-white/60 bg-white/80 text-sm focus:outline-none focus:ring-2 focus:ring-[#d4c5a9]"
                        rows={2}
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleSaveEdit(memory.memory_id)}
                          className="text-xs px-3 py-1 lavender-btn rounded-full"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => {
                            setEditingId(null);
                            setEditText('');
                          }}
                          className="text-xs px-3 py-1 lavender-secondary-btn rounded-full"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <p className="text-sm text-[#1a1a1a]">{memory.text}</p>
                      <div className="flex gap-4 text-xs">
                        <button
                          onClick={() => handleEdit(memory)}
                          className="text-[#d4c5a9] hover:underline"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(memory.memory_id)}
                          className="text-red-500 hover:underline"
                        >
                          Delete
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {candidatesToShow.length === 0 && approvedMemories.length === 0 && (
          <div className="text-center text-sm mt-8 text-[#7a5bb0]">
            No memories yet. Memories will appear here as you chat.
          </div>
        )}
      </div>

      {isUserControlled && selected.size > 0 && (
        <div className="p-4 border-t border-white/60 bg-white/70 backdrop-blur-xl">
          <button
            onClick={handleBatchSave}
            disabled={loading}
            className="w-full lavender-btn disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Saving...' : `Save ${selected.size} Memory${selected.size > 1 ? 'ies' : ''}`}
          </button>
        </div>
      )}
    </div>
  );
}


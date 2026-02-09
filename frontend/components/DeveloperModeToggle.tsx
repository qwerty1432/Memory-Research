'use client';

import { useState, useEffect } from 'react';
import { conditionAPI } from '@/lib/api';
import { storage, STORAGE_KEYS } from '@/lib/storage';

interface DeveloperModeToggleProps {
  userId: string;
  currentCondition: string;
  onConditionChange: (conditionId: string) => void;
}

const CONDITIONS = [
  { id: 'SESSION_AUTO', label: 'Session + Auto' },
  { id: 'SESSION_USER', label: 'Session + User' },
  { id: 'PERSISTENT_AUTO', label: 'Persistent + Auto' },
  { id: 'PERSISTENT_USER', label: 'Persistent + User' },
];

export default function DeveloperModeToggle({
  userId,
  currentCondition,
  onConditionChange,
}: DeveloperModeToggleProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isDeveloperMode, setIsDeveloperMode] = useState(false);
  const [password, setPassword] = useState('');
  const [showPasswordInput, setShowPasswordInput] = useState(false);

  useEffect(() => {
    const devMode = storage.get(STORAGE_KEYS.DEVELOPER_MODE) === 'true';
    setIsDeveloperMode(devMode);
    if (devMode) {
      setIsOpen(true);
    }
  }, []);

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Simple password check for MVP (change in production)
    if (password === 'dev123' || process.env.NEXT_PUBLIC_ENVIRONMENT === 'development') {
      setIsDeveloperMode(true);
      storage.set(STORAGE_KEYS.DEVELOPER_MODE, 'true');
      setShowPasswordInput(false);
      setIsOpen(true);
    } else {
      alert('Incorrect password');
    }
  };

  const handleConditionChange = async (conditionId: string) => {
    try {
      await conditionAPI.update(userId, conditionId);
      onConditionChange(conditionId);
      alert(`Condition changed to ${conditionId}. This is temporary and will not persist.`);
    } catch (error) {
      console.error('Error changing condition:', error);
      alert('Failed to change condition');
    }
  };

  if (process.env.NEXT_PUBLIC_ENVIRONMENT !== 'development' && !isDeveloperMode) {
    return (
      <div className="fixed bottom-4 right-4">
        <button
          onClick={() => setShowPasswordInput(true)}
          className="lavender-secondary-btn text-xs px-4 py-1 rounded-full shadow-sm"
        >
          Dev
        </button>
        {showPasswordInput && (
          <div className="absolute bottom-full right-0 mb-2 p-4 glass-card rounded-2xl min-w-[220px]">
            <form onSubmit={handlePasswordSubmit} className="space-y-2">
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                className="w-full px-3 py-2 border border-white/60 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#d4c5a9]"
              />
              <div className="flex gap-2 justify-end">
                <button
                  type="button"
                  onClick={() => setShowPasswordInput(false)}
                  className="lavender-secondary-btn text-xs px-3 py-1 rounded-full"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="lavender-btn text-xs px-3 py-1 rounded-full"
                >
                  Submit
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    );
  }

  if (!isOpen) {
    return (
      <div className="fixed bottom-4 right-4">
        <button
          onClick={() => setIsOpen(true)}
          className="px-3 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Dev Mode
        </button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 glass-card rounded-3xl shadow-2xl p-5 w-72">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-semibold text-sm text-[#1a1a1a]">Developer Mode</h3>
        <button
          onClick={() => setIsOpen(false)}
          className="text-[#d4c5a9] hover:text-[#1a1a1a]"
        >
          ✕
        </button>
      </div>
      <p className="text-xs text-[#6c4c99] mb-3">
        Current condition: <span className="font-medium">{currentCondition}</span>
      </p>
      <div className="space-y-2">
        {CONDITIONS.map((condition) => (
          <button
            key={condition.id}
            onClick={() => handleConditionChange(condition.id)}
            className={`w-full text-left px-4 py-2 text-xs rounded-2xl border transition ${
              currentCondition === condition.id
                ? 'border-transparent text-black bg-gradient-to-r from-[#f5e6d3] to-[#d4c5a9] shadow-lg'
                : 'border-white/60 bg-white/70 text-[#1a1a1a] hover:border-[#d4c5a9]'
            }`}
          >
            {condition.label}
          </button>
        ))}
      </div>
    </div>
  );
}


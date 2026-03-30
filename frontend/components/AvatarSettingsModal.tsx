'use client';

import { useEffect, useMemo, useState } from 'react';
import AiAvatar, { AssistantAvatarSettings } from '@/components/AiAvatar';

interface AvatarSettingsModalProps {
  isOpen: boolean;
  initialSettings: AssistantAvatarSettings;
  onClose: () => void;
  onSave: (settings: AssistantAvatarSettings) => void;
}

const COLORS = [
  { label: 'Cream', value: '#f5e6d3' },
  { label: 'Sand', value: '#d4c5a9' },
  { label: 'Deep Cream', value: '#c9b99b' },
  { label: 'White', value: '#ffffff' },
  { label: 'Mint', value: '#b7e4c7' },
  { label: 'Sky', value: '#a9d6e5' },
] as const;

const SYMBOLS = ['🤖', '★', '☀', '✿', '●', '■'] as const;

export default function AvatarSettingsModal({
  isOpen,
  initialSettings,
  onClose,
  onSave,
}: AvatarSettingsModalProps) {
  const [name, setName] = useState(initialSettings.name);
  const [bgColor, setBgColor] = useState(initialSettings.bgColor);
  const [symbol, setSymbol] = useState(initialSettings.symbol);

  useEffect(() => {
    if (!isOpen) return;
    setName(initialSettings.name);
    setBgColor(initialSettings.bgColor);
    setSymbol(initialSettings.symbol);
  }, [isOpen, initialSettings]);

  const canSave = useMemo(() => {
    const trimmed = name.trim();
    return trimmed.length >= 1 && trimmed.length <= 20 && symbol.trim().length <= 2;
  }, [name, symbol]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />

      <div className="relative w-[92vw] max-w-md rounded-2xl bg-white shadow-xl border border-gray-200 p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">Customize your AI Avatar</h2>
            <p className="text-sm text-gray-600 mt-1">
              Pick a name, icon color, and a simple symbol. This only changes how the AI looks in the chat.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-2 py-1 rounded-md hover:bg-gray-100 text-gray-700"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="mt-4 flex items-center gap-3">
          <AiAvatar settings={{ name, bgColor, symbol }} size={40} />
          <div className="text-sm">
            <div className="font-medium">{name.trim() || 'AI'}</div>
            <div className="text-gray-600">Preview</div>
          </div>
        </div>

        <div className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">AI name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-[#d4c5a9]"
              placeholder="e.g., Sunny"
              maxLength={20}
            />
          </div>

          <div>
            <div className="block text-sm font-medium mb-2">Avatar color</div>
            <div className="flex flex-wrap gap-2">
              {COLORS.map((c) => (
                <button
                  key={c.value}
                  type="button"
                  onClick={() => setBgColor(c.value)}
                  className={`px-3 py-2 rounded-lg border text-sm hover:bg-gray-50 ${
                    bgColor === c.value ? 'border-gray-800' : 'border-gray-200'
                  }`}
                >
                  <span
                    className="inline-block w-3 h-3 rounded-full mr-2 align-middle border border-black/10"
                    style={{ backgroundColor: c.value }}
                  />
                  {c.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <div className="block text-sm font-medium mb-2">Symbol</div>
            <div className="flex flex-wrap gap-2">
              {SYMBOLS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setSymbol(s)}
                  className={`px-3 py-2 rounded-lg border text-sm hover:bg-gray-50 ${
                    symbol === s ? 'border-gray-800' : 'border-gray-200'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="lavender-secondary-btn">
            Cancel
          </button>
          <button
            type="button"
            disabled={!canSave}
            onClick={() => onSave({ name: name.trim(), bgColor, symbol: symbol.trim() })}
            className="lavender-btn disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}


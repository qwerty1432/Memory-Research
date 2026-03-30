'use client';

import { useMemo, useState } from 'react';
import AiAvatar, { AssistantAvatarSettings } from '@/components/AiAvatar';

interface AvatarOnboardingProps {
  initialSettings: AssistantAvatarSettings;
  onComplete: (settings: AssistantAvatarSettings) => void;
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

export default function AvatarOnboarding({ initialSettings, onComplete }: AvatarOnboardingProps) {
  const [name, setName] = useState(initialSettings.name || 'AI Companion');
  const [bgColor, setBgColor] = useState(
    initialSettings.bgColor || COLORS[1]?.value || '#d4c5a9',
  );
  const [symbol, setSymbol] = useState(initialSettings.symbol || '🤖');

  const canContinue = useMemo(() => {
    const trimmed = name.trim();
    return trimmed.length >= 1 && trimmed.length <= 20 && symbol.trim().length <= 2;
  }, [name, symbol]);

  const handleUseDefault = () => {
    onComplete({
      name: 'AI Companion',
      bgColor: '#d4c5a9',
      symbol: '🤖',
    });
  };

  const handleContinue = () => {
    if (!canContinue) return;
    onComplete({
      name: name.trim(),
      bgColor,
      symbol: symbol.trim(),
    });
  };

  return (
    <div className="flex flex-col min-h-[100dvh] h-[100dvh] bg-gray-50">
      <div className="flex-1 flex items-center justify-center px-4">
        <div className="w-full max-w-lg glass-card rounded-2xl p-6">
          <h1 className="text-xl font-semibold mb-2">Set up your AI companion</h1>
          <p className="text-sm text-gray-600 mb-4">
            Before we start, you can personalize how your AI companion looks. This only changes how
            the bot appears to you.
          </p>

          <div className="flex items-center gap-3 mb-5">
            <AiAvatar settings={{ name, bgColor, symbol }} size={44} />
            <div className="text-sm">
              <div className="font-medium">
                {name.trim().length > 0 ? name.trim() : 'AI Companion'}
              </div>
              <div className="text-gray-600">This is how your companion will appear in chat.</div>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Companion name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-[#d4c5a9]"
                placeholder="e.g., Sunny"
                maxLength={20}
              />
              <p className="text-xs text-gray-500 mt-1">You can change this later from the menu.</p>
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

          <div className="mt-6 flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={handleUseDefault}
              className="text-xs text-gray-600 underline underline-offset-2"
            >
              Skip for now (use default)
            </button>
            <button
              type="button"
              disabled={!canContinue}
              onClick={handleContinue}
              className="lavender-btn disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Continue to chat
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}


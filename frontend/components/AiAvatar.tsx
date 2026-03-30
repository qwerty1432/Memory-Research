'use client';

export interface AssistantAvatarSettings {
  name: string;
  bgColor: string; // CSS color string (limited by UI choices)
  symbol: string; // emoji or short text
}

interface AiAvatarProps {
  settings: AssistantAvatarSettings;
  size?: number; // px
}

export default function AiAvatar({ settings, size = 28 }: AiAvatarProps) {
  const initialsFallback = (settings.name || 'AI').trim().slice(0, 2).toUpperCase();
  const symbol = (settings.symbol || '').trim();

  return (
    <div
      className="flex items-center justify-center rounded-full border border-white/60 shadow-sm select-none"
      style={{
        width: size,
        height: size,
        backgroundColor: settings.bgColor,
      }}
      aria-label={`Avatar for ${settings.name || 'AI'}`}
      title={settings.name || 'AI'}
    >
      <span className="text-xs leading-none text-black">
        {symbol.length > 0 ? symbol.slice(0, 2) : initialsFallback}
      </span>
    </div>
  );
}


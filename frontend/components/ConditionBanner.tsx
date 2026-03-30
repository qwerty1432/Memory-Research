'use client';

interface ConditionBannerProps {
  conditionId: string;
}

const CONDITION_MESSAGES: Record<string, string> = {
  SESSION_AUTO: 'This companion will only use your memory in this session.',
  SESSION_USER:
    'This companion will only use your memory in this session. You can review or alter it in Menu -> Memory.',
  PERSISTENT_AUTO: 'This companion may use memory from this and future sessions.',
  PERSISTENT_USER:
    'This companion may use memory across sessions. You can review or alter it in Menu -> Memory.',
};

export default function ConditionBanner({ conditionId }: ConditionBannerProps) {
  const message = CONDITION_MESSAGES[conditionId] || 'Unknown condition';

  return (
    <div className="px-4 py-3 text-sm">
      <div className="glass-card rounded-2xl px-4 py-2 text-center text-[0.9rem] text-[#1a1a1a] shadow-lg">
        {message}
      </div>
    </div>
  );
}


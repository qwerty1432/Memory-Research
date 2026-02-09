'use client';

interface ConditionBannerProps {
  conditionId: string;
}

const CONDITION_MESSAGES: Record<string, string> = {
  SESSION_AUTO: 'Your conversation will not be saved after this session ends.',
  SESSION_USER: 'You can review saved memories, but they will be cleared after this session ends.',
  PERSISTENT_AUTO: 'Your conversation is automatically saved and will persist in future sessions.',
  PERSISTENT_USER: 'You can choose which information to save, edit, or delete, and it will persist in future sessions.',
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


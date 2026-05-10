'use client';
import { getConditionDisclaimer } from '@/lib/conditionDisclaimer';

interface ConditionBannerProps {
  conditionId: string;
}

export default function ConditionBanner({ conditionId }: ConditionBannerProps) {
  const message = getConditionDisclaimer(conditionId);

  return (
    <div className="px-4 py-3 text-sm">
      <div className="glass-card rounded-2xl px-4 py-2 text-center text-[0.9rem] text-[#1a1a1a] shadow-lg">
        {message}
      </div>
    </div>
  );
}


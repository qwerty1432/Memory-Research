'use client';

import { useState } from 'react';
import { notifyQualtricsFinished } from '@/lib/qualtrics';

interface FinishConversationButtonProps {
  qualtricsId: string;
  phase?: number | null;
  disabled?: boolean;
  mode?: 'continue' | 'finish';
  onContinue?: () => Promise<void> | void;
  avatarData?: { agent_name?: string; agent_symbol?: string; agent_color?: string } | null;
}

export default function FinishConversationButton({
  qualtricsId,
  phase,
  disabled = false,
  mode = 'finish',
  onContinue,
  avatarData,
}: FinishConversationButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  const handleClick = async () => {
    console.log('Finish/Continue button clicked, qualtricsId:', qualtricsId);
    setIsLoading(true);
    setShowSuccess(false);

    try {
      if (mode === 'continue') {
        if (onContinue) {
          await onContinue();
        }
        setIsLoading(false);
        return;
      }

      // mode === 'finish'
      notifyQualtricsFinished(qualtricsId, phase, avatarData);
      console.log('Finish notification sent');

      setTimeout(() => {
        setIsLoading(false);
        setShowSuccess(true);
        setTimeout(() => setShowSuccess(false), 3000);
      }, 800);
    } catch (e) {
      console.error('Error in finish/continue handler:', e);
      setIsLoading(false);
    }
  };

  return (
    <div>
      <button
        onClick={handleClick}
        disabled={isLoading || showSuccess || disabled}
        className="w-full py-3 px-6 bg-[#d4c5a9] text-black font-semibold rounded-lg hover:bg-[#c9b99b] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <svg
              className="animate-spin h-5 w-5"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              ></circle>
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            <span>Finishing...</span>
          </>
        ) : showSuccess ? (
          <>
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            <span>Message Sent! ✓</span>
          </>
        ) : (
          <>
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            <span>{mode === 'continue' ? 'Continue' : 'Finish Conversation'}</span>
          </>
        )}
      </button>
      {showSuccess && (
        <p className="mt-2 text-sm text-green-600 text-center">
          Finish message sent! Check browser console (F12) to see the postMessage.
        </p>
      )}
      {disabled && !showSuccess && (
        <p className="mt-2 text-sm text-amber-700 text-center">
          Please complete all phases before finishing.
        </p>
      )}
    </div>
  );
}

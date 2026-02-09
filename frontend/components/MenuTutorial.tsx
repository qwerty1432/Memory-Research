'use client';

import { useState, useEffect } from 'react';
import { storage } from '@/lib/storage';

interface MenuTutorialProps {
  menuButtonRef: React.RefObject<HTMLDivElement>;
  onDismiss: () => void;
  showMemoryOption: boolean;
  isVisible: boolean;
}

export default function MenuTutorial({ menuButtonRef, onDismiss, showMemoryOption, isVisible }: MenuTutorialProps) {
  const [position, setPosition] = useState({ top: 0, right: 0 });

  useEffect(() => {
    if (menuButtonRef.current) {
      // Calculate position relative to menu button
      const updatePosition = () => {
        if (menuButtonRef.current) {
          const rect = menuButtonRef.current.getBoundingClientRect();
          setPosition({
            top: rect.bottom + 10,
            right: window.innerWidth - rect.right,
          });
        }
      };

      // Update position on mount and resize
      updatePosition();
      window.addEventListener('resize', updatePosition);
      window.addEventListener('scroll', updatePosition);

      return () => {
        window.removeEventListener('resize', updatePosition);
        window.removeEventListener('scroll', updatePosition);
      };
    }
  }, [menuButtonRef]);

  useEffect(() => {
    // Mark as seen when tutorial is shown
    if (isVisible) {
      storage.set('has_seen_menu_tutorial', 'true');
    }
  }, [isVisible]);

  if (!isVisible) return null;

  const handleDismiss = (e?: React.MouseEvent) => {
    if (e) {
      e.stopPropagation();
    }
    onDismiss();
  };

  return (
    <>
      {/* Overlay to dim background */}
      <div
        className="fixed inset-0 bg-black bg-opacity-20 z-40"
        onClick={handleDismiss}
      />

      {/* Bouncing Arrow */}
      <div
        className="fixed z-50 pointer-events-none"
        style={{
          top: `${position.top}px`,
          right: `${position.right + 20}px`,
        }}
      >
        <div className="animate-bounce">
          <svg
            className="w-8 h-8 text-[#d4c5a9]"
            fill="currentColor"
            viewBox="0 0 24 24"
          >
            <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z" />
          </svg>
        </div>
      </div>

      {/* Tooltip Box */}
      <div
        className="fixed z-50 bg-white rounded-lg shadow-xl border-2 border-[#d4c5a9] p-4 max-w-xs"
        style={{
          top: `${position.top + 40}px`,
          right: `${position.right}px`,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={handleDismiss}
          type="button"
          className="absolute top-2 right-2 text-gray-400 hover:text-gray-600 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        
        <h3 className="font-semibold text-sm mb-3 text-[#1a1a1a]">Menu Options</h3>
        <div className="space-y-2.5 text-xs text-gray-700">
          {showMemoryOption && (
            <div>
              <span className="font-medium text-[#1a1a1a]">Memory:</span>{' '}
              <span>Review and manage saved memories from your conversations.</span>
            </div>
          )}
          <div>
            <span className="font-medium text-[#1a1a1a]">New Session:</span>{' '}
            <span>Start a fresh conversation. Previous messages will be cleared.</span>
          </div>
          <div>
            <span className="font-medium text-[#1a1a1a]">Logout:</span>{' '}
            <span>Sign out of your account.</span>
          </div>
        </div>
      </div>
    </>
  );
}

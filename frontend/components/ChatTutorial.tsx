'use client';

import { useState, useEffect, useRef } from 'react';
import { storage } from '@/lib/storage';

interface ChatTutorialProps {
  chatInputRef: React.RefObject<HTMLInputElement>;
  onDismiss: () => void;
  isVisible: boolean;
}

export default function ChatTutorial({ chatInputRef, onDismiss, isVisible }: ChatTutorialProps) {
  const [position, setPosition] = useState({ bottom: 0, left: 0, width: 0 });

  useEffect(() => {
    if (chatInputRef.current && isVisible) {
      // Calculate position relative to chat input (above it)
      const updatePosition = () => {
        if (chatInputRef.current) {
          const rect = chatInputRef.current.getBoundingClientRect();
          setPosition({
            bottom: window.innerHeight - rect.top + 10, // Position above the input
            left: rect.left,
            width: rect.width,
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
  }, [chatInputRef, isVisible]);

  useEffect(() => {
    // Mark as seen when tutorial is shown
    if (isVisible) {
      storage.set('has_seen_chat_tutorial', 'true');
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

      {/* Tutorial Box above chat input */}
      <div
        className="fixed z-50 bg-white rounded-lg shadow-xl border-2 border-[#d4c5a9] p-4"
        style={{
          bottom: `${position.bottom}px`,
          left: `${position.left}px`,
          width: `${Math.max(position.width, 300)}px`,
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
        
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-1">
            <svg
              className="w-6 h-6 text-[#d4c5a9]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
              />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-sm mb-1 text-[#1a1a1a]">Start Chatting</h3>
            <p className="text-xs text-gray-700">
              Type your message in the chat box below to start a conversation with your AI companion.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}

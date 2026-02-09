'use client';

import { useState, useEffect, useRef } from 'react';

interface CollapsibleButtonMenuProps {
  children: React.ReactNode;
  label?: string;
}

export default function CollapsibleButtonMenu({ children, label = 'Menu' }: CollapsibleButtonMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  return (
    <div className="relative" ref={menuRef}>
      {/* Collapsed Widget Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="px-4 py-2 bg-[#d4c5a9] text-black rounded-lg hover:bg-[#c9b99b] transition-all flex items-center gap-2"
      >
        <span>{label}</span>
        <svg
          className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded Menu */}
      {isOpen && (
        <div 
          className="absolute top-full right-0 mt-2 bg-white rounded-lg shadow-lg border border-gray-200 py-2 min-w-[200px] z-50"
          onClick={(e) => {
            // Close menu when clicking on any button inside
            if ((e.target as HTMLElement).tagName === 'BUTTON') {
              setIsOpen(false);
            }
          }}
        >
          <div className="flex flex-col gap-1">
            {children}
          </div>
        </div>
      )}
    </div>
  );
}

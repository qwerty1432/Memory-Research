'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { authAPI, sessionAPI, conditionAPI, memoryAPI, Message, Memory } from '@/lib/api';
import { storage, STORAGE_KEYS } from '@/lib/storage';
import ChatWindow from '@/components/ChatWindow';
import MemoryReviewPanel from '@/components/MemoryReviewPanel';
import ConditionBanner from '@/components/ConditionBanner';
import DeveloperModeToggle from '@/components/DeveloperModeToggle';
import CollapsibleButtonMenu from '@/components/CollapsibleButtonMenu';
import MenuTutorial from '@/components/MenuTutorial';
import ChatTutorial from '@/components/ChatTutorial';

export default function Home() {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [conditionId, setConditionId] = useState<string>('SESSION_AUTO');
  const [messages, setMessages] = useState<Message[]>([]);
  const [memoryCandidates, setMemoryCandidates] = useState<Memory[]>([]);
  const [isMemoryPanelOpen, setIsMemoryPanelOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showTutorial, setShowTutorial] = useState(false);
  const [showChatTutorial, setShowChatTutorial] = useState(false);
  const menuButtonRef = useRef<HTMLDivElement>(null);
  const chatInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Check if user is logged in
    const storedUserId = storage.get(STORAGE_KEYS.USER_ID);
    const storedSessionId = storage.get(STORAGE_KEYS.SESSION_ID);
    const storedUsername = storage.get(STORAGE_KEYS.USERNAME);
    const storedConditionId = storage.get(STORAGE_KEYS.CONDITION_ID);

    if (storedUserId && storedSessionId) {
      setUserId(storedUserId);
      setSessionId(storedSessionId);
      setUsername(storedUsername);
      if (storedConditionId) {
        setConditionId(storedConditionId);
      }
      loadSessionData(storedUserId, storedSessionId);
    } else {
      // Redirect to login
      router.push('/login');
    }
  }, [router]);

  const loadSessionData = async (uid: string, sid: string) => {
    try {
      // Load condition
      const condition = await conditionAPI.get(uid);
      setConditionId(condition.condition_id);
      storage.set(STORAGE_KEYS.CONDITION_ID, condition.condition_id);

      // Load messages
      const sessionMessages = await sessionAPI.getMessages(sid);
      setMessages(sessionMessages);

      // Load memory candidates
      const candidates = await memoryAPI.getCandidates(uid, sid);
      setMemoryCandidates(candidates);

      setLoading(false);
      
      // Check if we should show tutorials after loading
      const hasSeenMenuTutorial = storage.get('has_seen_menu_tutorial');
      const hasSeenChatTutorial = storage.get('has_seen_chat_tutorial');
      
      if (!hasSeenMenuTutorial) {
        // Small delay to ensure menu button is rendered
        setTimeout(() => {
          setShowTutorial(true);
        }, 500);
      } else if (!hasSeenChatTutorial) {
        // If menu tutorial was already seen, show chat tutorial directly
        setTimeout(() => {
          setShowChatTutorial(true);
        }, 500);
      }
    } catch (error) {
      console.error('Error loading session data:', error);
      setLoading(false);
    }
  };

  const handleNewSession = async () => {
    if (!userId) return;
    try {
      const newSession = await sessionAPI.create(userId);
      setSessionId(newSession.session_id);
      storage.set(STORAGE_KEYS.SESSION_ID, newSession.session_id);
      setMessages([]);
      setMemoryCandidates([]);
    } catch (error) {
      console.error('Error creating new session:', error);
    }
  };

  const handleNewMessage = (message: Message) => {
    setMessages((prev) => [...prev, message]);
  };

  const handleNewCandidates = (candidates: Memory[]) => {
    setMemoryCandidates((prev) => {
      const existingIds = new Set(prev.map((c) => c.memory_id));
      const newCandidates = candidates.filter((c) => !existingIds.has(c.memory_id));
      return [...prev, ...newCandidates];
    });
    // Show notification if there are new candidates
    if (candidates.length > 0 && conditionId.includes('USER')) {
      // Could show a toast notification here
    }
  };

  const handleLogout = () => {
    storage.clear();
    router.push('/login');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p>Loading...</p>
      </div>
    );
  }

  if (!userId || !sessionId) {
    return null;
  }

  const isUserControlled = conditionId.includes('USER');

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header at the top */}
      <div className="sticky top-0 z-20 shadow-sm border-b bg-white">
        <div className="p-4 flex justify-between items-center">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <svg
                className="w-7 h-7 text-[#d4c5a9]"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                />
              </svg>
              <h1 className="text-xl font-semibold">AI Companion</h1>
            </div>
            <p className="text-sm text-gray-600">Logged in as {username}</p>
          </div>
          <div ref={menuButtonRef} className="relative">
            <CollapsibleButtonMenu label="Menu">
              <button
                onClick={() => {
                  setIsMemoryPanelOpen(!isMemoryPanelOpen);
                }}
                className="px-4 py-2 text-left hover:bg-gray-100 transition-colors text-sm"
              >
                Memory {memoryCandidates.length > 0 && `(${memoryCandidates.length})`}
              </button>
              <button
                onClick={() => router.push(`/survey?session_id=${sessionId}&type=mid_checkpoint`)}
                className="px-4 py-2 text-left hover:bg-gray-100 transition-colors text-sm"
              >
                Checkpoint Survey
              </button>
              <button
                onClick={handleNewSession}
                className="px-4 py-2 text-left hover:bg-gray-100 transition-colors text-sm"
              >
                New Session
              </button>
              <button
                onClick={handleLogout}
                className="px-4 py-2 text-left hover:bg-gray-100 transition-colors text-sm text-red-600"
              >
                Logout
              </button>
            </CollapsibleButtonMenu>
            {showTutorial && (
              <MenuTutorial
                menuButtonRef={menuButtonRef}
                onDismiss={() => {
                  setShowTutorial(false);
                  // Show chat tutorial after menu tutorial is dismissed
                  const hasSeenChatTutorial = storage.get('has_seen_chat_tutorial');
                  if (!hasSeenChatTutorial) {
                    setTimeout(() => {
                      setShowChatTutorial(true);
                    }, 300);
                  }
                }}
                showMemoryOption={isUserControlled}
                isVisible={showTutorial}
              />
            )}
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 flex flex-col">
          {/* Condition Banner above chat */}
          <div className="px-4 py-2">
            <ConditionBanner conditionId={conditionId} />
          </div>
          
          {/* Chat Window */}
          <ChatWindow
            userId={userId}
            sessionId={sessionId}
            conditionId={conditionId}
            messages={messages}
            onNewMessage={handleNewMessage}
            onNewCandidates={handleNewCandidates}
            onManualMemoryAdded={() => {
              memoryAPI.getCandidates(userId, sessionId).then(setMemoryCandidates);
            }}
            chatInputRef={chatInputRef}
          />
          
          {/* Chat Tutorial */}
          {showChatTutorial && (
            <ChatTutorial
              chatInputRef={chatInputRef}
              onDismiss={() => setShowChatTutorial(false)}
              isVisible={showChatTutorial}
            />
          )}
        </div>

        {/* Memory Panel */}
        {isMemoryPanelOpen && (
          <MemoryReviewPanel
            userId={userId}
            sessionId={sessionId}
            conditionId={conditionId}
            isOpen={isMemoryPanelOpen}
            onClose={() => setIsMemoryPanelOpen(false)}
            candidates={memoryCandidates}
            onCandidatesUpdate={() => {
              // Reload candidates
              memoryAPI.getCandidates(userId, sessionId).then(setMemoryCandidates);
            }}
          />
        )}
      </div>

      {/* Developer Mode Toggle */}
      <DeveloperModeToggle
        userId={userId}
        currentCondition={conditionId}
        onConditionChange={(newCondition) => {
          setConditionId(newCondition);
          storage.set(STORAGE_KEYS.CONDITION_ID, newCondition);
        }}
      />
    </div>
  );
}


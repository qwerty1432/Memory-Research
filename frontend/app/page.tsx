'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { authAPI, sessionAPI, conditionAPI, memoryAPI, chatAPI, Message, Memory } from '@/lib/api';
import { storage, STORAGE_KEYS } from '@/lib/storage';
import { parseQualtricsParams, isQualtricsMode } from '@/lib/qualtrics';
import ChatWindow from '@/components/ChatWindow';
import MemoryReviewPanel from '@/components/MemoryReviewPanel';
import ConditionBanner from '@/components/ConditionBanner';
import DeveloperModeToggle from '@/components/DeveloperModeToggle';
import CollapsibleButtonMenu from '@/components/CollapsibleButtonMenu';
import MenuTutorial from '@/components/MenuTutorial';
import ChatTutorial from '@/components/ChatTutorial';
import FinishConversationButton from '@/components/FinishConversationButton';
import AvatarSettingsModal from '@/components/AvatarSettingsModal';
import AvatarOnboarding from '@/components/AvatarOnboarding';
import { AssistantAvatarSettings } from '@/components/AiAvatar';
import { getConditionDisclaimer } from '@/lib/conditionDisclaimer';

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
  const [isQualtrics, setIsQualtrics] = useState(false);
  const [qualtricsId, setQualtricsId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isAvatarModalOpen, setIsAvatarModalOpen] = useState(false);
  const [assistantAvatar, setAssistantAvatar] = useState<AssistantAvatarSettings>({
    name: 'AI Companion',
    bgColor: '#d4c5a9',
    symbol: '🤖',
  });
  const menuButtonRef = useRef<HTMLDivElement>(null);
  const chatInputRef = useRef<HTMLInputElement>(null);
  const [showAvatarOnboarding, setShowAvatarOnboarding] = useState(false);
  const [hasAcknowledgedDisclaimer, setHasAcknowledgedDisclaimer] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<number | null>(null);
  const [phaseProgress, setPhaseProgress] = useState<{
    phase: number;
    prompts_answered: number;
    total_prompts: number;
    phase_complete: boolean;
    // Only set once the multi-phase study reaches the end (single-block mode / final phase).
    // Marked optional because earlier phases may not include it.
    study_complete?: boolean;
    current_prompt_index?: number;
  } | null>(null);

  useEffect(() => {
    // Check for Qualtrics mode first
    const params = parseQualtricsParams();
    const qualMode = isQualtricsMode();
    setIsQualtrics(qualMode);
    
    const participantId = params.response_id || params.qualtrics_id;
    if (qualMode && participantId) {
      // Qualtrics mode: authenticate automatically
      // Single-block mode: phase is optional (will be determined by backend progress state)
      setQualtricsId(participantId);
      setCurrentPhase(null); // Single-block mode only
      handleQualtricsAuthentication(participantId, params.response_id, null);
    } else {
      // Normal mode: check if user is logged in
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
    }
  }, [router]);

  // Load avatar settings
  useEffect(() => {
    const raw = storage.get(STORAGE_KEYS.ASSISTANT_AVATAR);
    const qualMode = isQualtricsMode();
    const params = parseQualtricsParams();
    const participantId = params.response_id || params.qualtrics_id;
    const avatarIntroDoneKey = participantId
      ? `qualtrics_avatar_intro_done_${participantId}`
      : null;
    const introDone = avatarIntroDoneKey ? storage.get(avatarIntroDoneKey) : null;

    const shouldForceIntro = qualMode && !!participantId && introDone !== 'true';

    // If an avatar exists, load it regardless of whether we need to show the intro gate.
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === 'object') {
          setAssistantAvatar({
            name: typeof parsed.name === 'string' ? parsed.name : 'AI Companion',
            bgColor: typeof parsed.bgColor === 'string' ? parsed.bgColor : '#d4c5a9',
            symbol: typeof parsed.symbol === 'string' ? parsed.symbol : '🤖',
          });
        }
      } catch {
        // Fall back to defaults; we'll show onboarding anyway.
      }
    }

    // Gate chat behind avatar onboarding:
    // - if no avatar is stored
    // - OR (Qualtrics) if this participant hasn't seen the intro screen yet
    if (!raw || shouldForceIntro) {
      setShowAvatarOnboarding(true);
      return;
    }

    setShowAvatarOnboarding(false);
  }, []);

  const handleQualtricsAuthentication = async (
    qId: string,
    responseId?: string | null,
    phase?: number | null,
  ) => {
    try {
      setLoading(true);
      setError(null);
      console.log('Attempting Qualtrics authentication with ID:', qId);
      const response = await authAPI.qualtricsAuthenticate(
        qId,
        responseId ?? undefined,
        phase ?? null, // null for single-block mode
      );
      console.log('Qualtrics authentication successful:', response);
      
      // Store authentication data
      setUserId(response.user_id);
      setSessionId(response.session_id);
      setUsername(response.username);
      setConditionId(response.condition_id);
      // Phase will be determined by backend progress state, not URL
      setCurrentPhase(response.phase ?? null);
      
      storage.set(STORAGE_KEYS.USER_ID, response.user_id);
      storage.set(STORAGE_KEYS.SESSION_ID, response.session_id);
      storage.set(STORAGE_KEYS.USERNAME, response.username);
      storage.set(STORAGE_KEYS.CONDITION_ID, response.condition_id);
      
      // Load session data
      await loadSessionData(response.user_id, response.session_id);
    } catch (error: any) {
      console.error('Error authenticating with Qualtrics:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to authenticate. Please check console for details.';
      setError(errorMessage);
      setLoading(false);
    }
  };

  const loadSessionData = async (uid: string, sid: string) => {
    try {
      // Load condition
      const condition = await conditionAPI.get(uid);
      setConditionId(condition.condition_id);
      storage.set(STORAGE_KEYS.CONDITION_ID, condition.condition_id);

      // Load messages
      const sessionMessages = await sessionAPI.getMessages(sid);
      setMessages(sessionMessages);
      setHasAcknowledgedDisclaimer(sessionMessages.length > 0);

      // Load memory candidates
      const candidates = await memoryAPI.getCandidates(uid, sid);
      setMemoryCandidates(candidates);

      // In Qualtrics single-block mode, reload persisted progress so the UI is correct on refresh.
      if (isQualtrics) {
        const progress = await chatAPI.getProgress(uid, sid);
        setCurrentPhase(progress.phase ?? null);
        setPhaseProgress({
          phase: progress.phase,
          prompts_answered: progress.prompts_answered,
          total_prompts: progress.total_prompts,
          phase_complete: progress.phase_complete,
          study_complete: progress.study_complete,
        });
      }

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

  // Phase progress is now managed by backend and updated via onPhaseStatusUpdate callback
  // No need to calculate locally from message count

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[100dvh]">
        <p className="text-lg">Loading...</p>
        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg max-w-md">
            <p className="font-semibold">Error:</p>
            <p>{error}</p>
            <p className="mt-2 text-sm">Check browser console (F12) for more details.</p>
          </div>
        )}
      </div>
    );
  }

  if (error && !loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[100dvh]">
        <div className="p-6 bg-red-50 border border-red-200 text-red-700 rounded-lg max-w-md">
          <p className="font-semibold text-lg mb-2">Authentication Error</p>
          <p>{error}</p>
          <p className="mt-4 text-sm">Please check:</p>
          <ul className="mt-2 text-sm list-disc list-inside">
            <li>Backend server is running (port 8000)</li>
            <li>Database schema was updated (run: python init_db.py)</li>
            <li>Browser console (F12) for detailed errors</li>
          </ul>
        </div>
      </div>
    );
  }

  if (!userId || !sessionId) {
    return null;
  }

  if (showAvatarOnboarding) {
    return (
      <AvatarOnboarding
        initialSettings={assistantAvatar}
        onComplete={(settings) => {
          setAssistantAvatar(settings);
          storage.set(STORAGE_KEYS.ASSISTANT_AVATAR, JSON.stringify(settings));
          // For Qualtrics participants, mark the intro screen as completed so they can start chatting.
          const qualMode = isQualtricsMode();
          const params = parseQualtricsParams();
          const participantId = params.response_id || params.qualtrics_id;
          if (qualMode && participantId) {
            storage.set(`qualtrics_avatar_intro_done_${participantId}`, 'true');
          }
          setShowAvatarOnboarding(false);
        }}
      />
    );
  }

  const isUserControlled = conditionId.includes('USER');
  const conditionDisclaimer = getConditionDisclaimer(conditionId);
  const mustAcknowledgeDisclaimer = messages.length === 0 && !hasAcknowledgedDisclaimer;

  return (
    <div className="flex flex-col min-h-[100dvh] h-[100dvh] bg-gray-50">
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
            {!isQualtrics && <p className="text-sm text-gray-600">Logged in as {username}</p>}
            {isQualtrics && phaseProgress && (
              <p className="text-sm text-gray-600">
                Phase {phaseProgress.phase}
                {phaseProgress.study_complete ? (
                  <span className="ml-2 text-green-600 font-semibold">Study Complete</span>
                ) : (
                  <span>
                    {' '}
                    - Topic {(phaseProgress.current_prompt_index ?? phaseProgress.prompts_answered) + 1}/{phaseProgress.total_prompts}
                    {(phaseProgress.followups_used_for_prompt ?? 0) > 0 ? ' (follow-up)' : ''}
                  </span>
                )}
              </p>
            )}
          </div>
          <div ref={menuButtonRef} className="relative">
            <CollapsibleButtonMenu label="Menu">
              {/* Participant-facing options (available in both normal and Qualtrics modes) */}
              <button
                onClick={() => setIsAvatarModalOpen(true)}
                className="px-4 py-2 text-left hover:bg-gray-100 transition-colors text-sm"
              >
                Avatar
              </button>

              <button
                onClick={() => {
                  setIsMemoryPanelOpen(!isMemoryPanelOpen);
                }}
                className="px-4 py-2 text-left hover:bg-gray-100 transition-colors text-sm"
              >
                Memory {memoryCandidates.length > 0 && `(${memoryCandidates.length})`}
              </button>

              {/* Normal mode options */}
              {!isQualtrics && (
                <>
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
                </>
              )}
            </CollapsibleButtonMenu>
            {showTutorial && !isQualtrics && (
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
          {mustAcknowledgeDisclaimer ? (
            <div className="flex-1 flex items-center justify-center px-4 py-6">
              <div className="w-full max-w-2xl glass-card rounded-2xl p-6">
                <h2 className="text-lg font-semibold text-[#1a1a1a] mb-2">Memory Use Disclaimer</h2>
                <p className="text-sm text-gray-700 leading-relaxed">{conditionDisclaimer}</p>
                <div className="mt-5 flex justify-end">
                  <button
                    onClick={() => setHasAcknowledgedDisclaimer(true)}
                    className="lavender-btn"
                  >
                    I Understand
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <ChatWindow
              userId={userId}
              sessionId={sessionId}
              conditionId={conditionId}
              phase={isQualtrics ? null : currentPhase}
              messages={messages}
              onNewMessage={handleNewMessage}
              onNewCandidates={handleNewCandidates}
              onPhaseStatusUpdate={(status) => setPhaseProgress(status)}
              onManualMemoryAdded={() => {
                memoryAPI.getCandidates(userId, sessionId).then(setMemoryCandidates);
              }}
              chatInputRef={chatInputRef}
              assistantAvatar={assistantAvatar}
            />
          )}
          
          {/* Finish Conversation Button (Qualtrics mode only) */}
          {isQualtrics && qualtricsId && (
            <div className="px-4 py-3 border-t bg-white">
              <FinishConversationButton
                qualtricsId={qualtricsId}
                phase={phaseProgress?.phase ?? currentPhase}
                mode={
                  phaseProgress?.phase_complete && !(phaseProgress?.study_complete ?? false)
                    ? 'continue'
                    : 'finish'
                }
                disabled={
                  phaseProgress == null ||
                  (!phaseProgress?.phase_complete && !(phaseProgress?.study_complete ?? false))
                }
                onContinue={async () => {
                  if (!userId || !sessionId) return;
                  const next = await chatAPI.advancePhase(userId, sessionId);
                  setCurrentPhase(next.phase_status.phase ?? null);
                  setPhaseProgress(next.phase_status);
                  setMessages((prev) => [
                    ...prev,
                    {
                      msg_id: '',
                      session_id: sessionId,
                      role: 'assistant',
                      content: next.opening_message,
                      created_at: new Date().toISOString(),
                    },
                  ]);
                }}
                avatarData={{
                  agent_name: assistantAvatar.name,
                  agent_symbol: assistantAvatar.symbol,
                  agent_color: assistantAvatar.bgColor,
                }}
              />
              {phaseProgress?.phase_complete && !(phaseProgress?.study_complete ?? false) && (
                <p className="mt-2 text-sm text-gray-600 text-center">
                  Phase complete. Click Continue to start the next phase.
                </p>
              )}
            </div>
          )}
          
          {/* Chat Tutorial */}
          {showChatTutorial && !isQualtrics && (
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

      {/* Developer Mode Toggle (hidden in Qualtrics mode) */}
      {!isQualtrics && (
        <DeveloperModeToggle
          userId={userId}
          currentCondition={conditionId}
          onConditionChange={(newCondition) => {
            setConditionId(newCondition);
            storage.set(STORAGE_KEYS.CONDITION_ID, newCondition);
          }}
        />
      )}

      <AvatarSettingsModal
        isOpen={isAvatarModalOpen}
        initialSettings={assistantAvatar}
        onClose={() => setIsAvatarModalOpen(false)}
        onSave={(settings) => {
          setAssistantAvatar(settings);
          storage.set(STORAGE_KEYS.ASSISTANT_AVATAR, JSON.stringify(settings));
          setIsAvatarModalOpen(false);
        }}
      />
    </div>
  );
}


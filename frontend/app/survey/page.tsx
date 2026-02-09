'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { storage, STORAGE_KEYS } from '@/lib/storage';
import CheckpointSurvey from '@/components/CheckpointSurvey';
import { sessionAPI } from '@/lib/api';

export default function SurveyPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [userId, setUserId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [surveyType, setSurveyType] = useState<string>('mid_checkpoint');

  useEffect(() => {
    // Get user info from storage
    const storedUserId = storage.get(STORAGE_KEYS.USER_ID);
    const storedSessionId = storage.get(STORAGE_KEYS.SESSION_ID);

    // Get params from URL
    const urlSessionId = searchParams.get('session_id');
    const urlSurveyType = searchParams.get('type') || 'mid_checkpoint';

    if (!storedUserId) {
      // Not logged in, redirect to login
      router.push('/login');
      return;
    }

    setUserId(storedUserId);
    setSessionId(urlSessionId || storedSessionId);
    setSurveyType(urlSurveyType);
  }, [router, searchParams]);

  const handleSurveyComplete = async () => {
    if (!userId) return;

    try {
      // Create new session (this will end the previous one)
      const newSession = await sessionAPI.create(userId);
      
      // Update storage with new session
      storage.set(STORAGE_KEYS.SESSION_ID, newSession.session_id);
      
      // Navigate back to chat (messages will be cleared automatically on load)
      router.push('/');
    } catch (error) {
      console.error('Error creating new session after survey:', error);
      // Still navigate back even if there's an error
      router.push('/');
    }
  };

  if (!userId || !sessionId) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <CheckpointSurvey
      userId={userId}
      sessionId={sessionId}
      surveyType={surveyType}
      onComplete={handleSurveyComplete}
    />
  );
}

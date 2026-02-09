'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { authAPI, sessionAPI } from '@/lib/api';
import { storage, STORAGE_KEYS } from '@/lib/storage';

export default function LoginPage() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [conditionId, setConditionId] = useState('SESSION_AUTO');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLogin) {
        // Login
        const user = await authAPI.login(username, password);
        const session = await sessionAPI.create(user.user_id);
        
        storage.set(STORAGE_KEYS.USER_ID, user.user_id);
        storage.set(STORAGE_KEYS.SESSION_ID, session.session_id);
        storage.set(STORAGE_KEYS.USERNAME, user.username);
        storage.set(STORAGE_KEYS.CONDITION_ID, user.condition_id);
        
        router.push('/');
      } else {
        // Register
        const user = await authAPI.register(username, password, conditionId);
        const session = await sessionAPI.create(user.user_id);
        
        storage.set(STORAGE_KEYS.USER_ID, user.user_id);
        storage.set(STORAGE_KEYS.SESSION_ID, session.session_id);
        storage.set(STORAGE_KEYS.USERNAME, user.username);
        storage.set(STORAGE_KEYS.CONDITION_ID, user.condition_id);
        
        router.push('/');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white rounded-lg shadow-md p-8">
        <h1 className="text-2xl font-bold text-center mb-6">
          AI Companion Research Platform
        </h1>

        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setIsLogin(true)}
            className={`flex-1 py-2 rounded ${
              isLogin ? 'bg-blue-500 text-white' : 'bg-gray-200'
            }`}
          >
            Login
          </button>
          <button
            onClick={() => setIsLogin(false)}
            className={`flex-1 py-2 rounded ${
              !isLogin ? 'bg-blue-500 text-white' : 'bg-gray-200'
            }`}
          >
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {!isLogin && (
              <p className="text-xs text-gray-500 mt-1">
                Must be at least 8 characters with at least one letter and one number
              </p>
            )}
          </div>

          {!isLogin && (
            <div>
              <label className="block text-sm font-medium mb-1">Condition (for testing)</label>
              <select
                value={conditionId}
                onChange={(e) => setConditionId(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="SESSION_AUTO">Session + Automatic</option>
                <option value="SESSION_USER">Session + User-Controlled</option>
                <option value="PERSISTENT_AUTO">Persistent + Automatic</option>
                <option value="PERSISTENT_USER">Persistent + User-Controlled</option>
              </select>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300"
          >
            {loading ? 'Loading...' : isLogin ? 'Login' : 'Register'}
          </button>
        </form>
      </div>
    </div>
  );
}


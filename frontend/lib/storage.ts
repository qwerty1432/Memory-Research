// LocalStorage utilities for storing user and session data

export const storage = {
  get: (key: string): string | null => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(key);
  },

  set: (key: string, value: string): void => {
    if (typeof window === 'undefined') return;
    localStorage.setItem(key, value);
  },

  remove: (key: string): void => {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(key);
  },

  clear: (): void => {
    if (typeof window === 'undefined') return;
    localStorage.clear();
  },
};

export const STORAGE_KEYS = {
  USER_ID: 'user_id',
  SESSION_ID: 'session_id',
  USERNAME: 'username',
  CONDITION_ID: 'condition_id',
  DEVELOPER_MODE: 'developer_mode',
} as const;


import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
export interface User {
  user_id: string;
  username: string;
  condition_id: string;
  created_at: string;
}

export interface Session {
  session_id: string;
  user_id: string;
  started_at: string;
  ended_at: string | null;
}

export interface Message {
  msg_id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface Memory {
  memory_id: string;
  user_id: string;
  session_id: string | null;
  text: string;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface Condition {
  condition_id: string;
  description: string;
}

// Auth API
export const authAPI = {
  register: async (username: string, password: string, conditionId?: string) => {
    const response = await api.post('/auth/register', {
      username,
      password,
      condition_id: conditionId,
    });
    return response.data;
  },

  login: async (username: string, password: string) => {
    const response = await api.post('/auth/login', {
      username,
      password,
    });
    return response.data;
  },

  getUser: async (userId: string) => {
    const response = await api.get(`/auth/user/${userId}`);
    return response.data;
  },
};

// Session API
export const sessionAPI = {
  create: async (userId: string) => {
    const response = await api.post('/session', {
      user_id: userId,
    });
    return response.data;
  },

  get: async (sessionId: string) => {
    const response = await api.get(`/session/${sessionId}`);
    return response.data;
  },

  getUserSessions: async (userId: string) => {
    const response = await api.get(`/session/user/${userId}`);
    return response.data;
  },

  getMessages: async (sessionId: string) => {
    const response = await api.get(`/session/${sessionId}/messages`);
    return response.data;
  },

  end: async (sessionId: string) => {
    const response = await api.post(`/session/${sessionId}/end`);
    return response.data;
  },
};

// Chat API
export const chatAPI = {
  send: async (userId: string, sessionId: string, message: string) => {
    const response = await api.post('/chat', {
      user_id: userId,
      session_id: sessionId,
      message,
    });
    return response.data;
  },
};

// Memory API
export const memoryAPI = {
  get: async (userId: string, sessionId?: string) => {
    const params = sessionId ? { session_id: sessionId } : {};
    const response = await api.get(`/memory/${userId}`, { params });
    return response.data;
  },

  getCandidates: async (userId: string, sessionId: string) => {
    const response = await api.get(`/memory/candidates/${userId}/${sessionId}`);
    return response.data;
  },

  create: async (data: { user_id: string; session_id?: string | null; text: string; is_active?: boolean }) => {
    const response = await api.post('/memory', {
      user_id: data.user_id,
      session_id: data.session_id ?? null,
      text: data.text,
      is_active: data.is_active ?? false,
    });
    return response.data;
  },

  approve: async (memoryId: string) => {
    const response = await api.post(`/memory/${memoryId}/approve`);
    return response.data;
  },

  update: async (memoryId: string, text?: string, isActive?: boolean) => {
    const response = await api.put(`/memory/${memoryId}`, {
      text,
      is_active: isActive,
    });
    return response.data;
  },

  delete: async (memoryId: string) => {
    await api.delete(`/memory/${memoryId}`);
  },

  batchUpdate: async (updates: Array<{ memory_id: string; text?: string; is_active?: boolean }>) => {
    const response = await api.post('/memory/batch-update', updates);
    return response.data;
  },
};

// Condition API
export const conditionAPI = {
  get: async (userId: string) => {
    const response = await api.get(`/condition/${userId}`);
    return response.data;
  },

  update: async (userId: string, conditionId: string) => {
    const response = await api.put(`/condition/${userId}?condition_id=${conditionId}`);
    return response.data;
  },
};


// Survey API
export interface SurveyQuestion {
  question_id: string;
  question_text: string;
  question_type: 'free_response' | 'mcq' | 'rating' | 'likert' | 'yes_no';
  options?: string[];
  min_rating?: number;
  max_rating?: number;
  required: boolean;
}

export interface SurveyTemplate {
  survey_type: string;
  questions: SurveyQuestion[];
}

export interface SurveyResponseItem {
  question_id: string;
  response_value: any;
}

export interface SurveySubmission {
  user_id: string;
  session_id?: string | null;
  survey_type: string;
  responses: SurveyResponseItem[];
}

export const surveyAPI = {
  getTemplate: async (surveyType: string): Promise<SurveyTemplate> => {
    const response = await api.get(`/survey/template/${surveyType}`);
    return response.data;
  },

  submit: async (submission: SurveySubmission) => {
    const response = await api.post('/survey/submit', submission);
    return response.data;
  },

  getUserResponses: async (userId: string, surveyType?: string) => {
    const params = surveyType ? { survey_type: surveyType } : {};
    const response = await api.get(`/survey/${userId}/responses`, { params });
    return response.data;
  },
};

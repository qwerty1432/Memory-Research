'use client';

import { useState, useEffect } from 'react';
import { surveyAPI, SurveyQuestion, SurveyResponseItem } from '@/lib/api';
import FreeResponse from './QuestionTypes/FreeResponse';
import MCQ from './QuestionTypes/MCQ';
import Rating from './QuestionTypes/Rating';
import Likert from './QuestionTypes/Likert';
import YesNo from './QuestionTypes/YesNo';

interface CheckpointSurveyProps {
  userId: string;
  sessionId: string;
  surveyType: string;
  onComplete: () => void;
}

export default function CheckpointSurvey({
  userId,
  sessionId,
  surveyType,
  onComplete,
}: CheckpointSurveyProps) {
  const [questions, setQuestions] = useState<SurveyQuestion[]>([]);
  const [responses, setResponses] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadTemplate();
  }, [surveyType]);

  const loadTemplate = async () => {
    try {
      setLoading(true);
      const template = await surveyAPI.getTemplate(surveyType);
      setQuestions(template.questions);
      // Initialize responses
      const initialResponses: Record<string, any> = {};
      template.questions.forEach((q) => {
        if (q.question_type === 'rating') {
          initialResponses[q.question_id] = null;
        } else {
          initialResponses[q.question_id] = '';
        }
      });
      setResponses(initialResponses);
    } catch (err: any) {
      setError(err.message || 'Failed to load survey');
    } finally {
      setLoading(false);
    }
  };

  const handleResponseChange = (questionId: string, value: any) => {
    setResponses((prev) => ({
      ...prev,
      [questionId]: value,
    }));
  };

  const validateForm = (): boolean => {
    for (const question of questions) {
      if (question.required) {
        const value = responses[question.question_id];
        if (value === null || value === '' || value === undefined) {
          return false;
        }
      }
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      setError('Please answer all required questions');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      const responseItems: SurveyResponseItem[] = questions.map((q) => ({
        question_id: q.question_id,
        response_value: {
          value: responses[q.question_id],
          type: q.question_type,
        },
      }));

      await surveyAPI.submit({
        user_id: userId,
        session_id: sessionId,
        survey_type: surveyType,
        responses: responseItems,
      });

      onComplete();
    } catch (err: any) {
      setError(err.message || 'Failed to submit survey');
    } finally {
      setSubmitting(false);
    }
  };

  const renderQuestion = (question: SurveyQuestion) => {
    const value = responses[question.question_id];

    switch (question.question_type) {
      case 'free_response':
        return (
          <FreeResponse
            key={question.question_id}
            questionId={question.question_id}
            questionText={question.question_text}
            required={question.required}
            value={value || ''}
            onChange={(val) => handleResponseChange(question.question_id, val)}
          />
        );
      case 'mcq':
        return (
          <MCQ
            key={question.question_id}
            questionId={question.question_id}
            questionText={question.question_text}
            options={question.options || []}
            required={question.required}
            value={value || ''}
            onChange={(val) => handleResponseChange(question.question_id, val)}
          />
        );
      case 'rating':
        return (
          <Rating
            key={question.question_id}
            questionId={question.question_id}
            questionText={question.question_text}
            minRating={question.min_rating || 1}
            maxRating={question.max_rating || 5}
            required={question.required}
            value={value}
            onChange={(val) => handleResponseChange(question.question_id, val)}
          />
        );
      case 'likert':
        return (
          <Likert
            key={question.question_id}
            questionId={question.question_id}
            questionText={question.question_text}
            options={question.options || []}
            required={question.required}
            value={value || ''}
            onChange={(val) => handleResponseChange(question.question_id, val)}
          />
        );
      case 'yes_no':
        return (
          <YesNo
            key={question.question_id}
            questionId={question.question_id}
            questionText={question.question_text}
            required={question.required}
            value={value || ''}
            onChange={(val) => handleResponseChange(question.question_id, val)}
          />
        );
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-[#fff8e7] to-[#f5e6d3]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#d4c5a9] mx-auto mb-4"></div>
          <p className="text-gray-600">Loading survey...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#fff8e7] to-[#f5e6d3] py-12 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Checkpoint Survey</h1>
          <p className="text-gray-600 mb-8">Please take a moment to share your thoughts about your conversation experience.</p>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="space-y-6">
              {questions.map((question) => renderQuestion(question))}
            </div>

            <div className="mt-8 flex gap-4">
              <button
                type="submit"
                disabled={submitting}
                className="flex-1 bg-gradient-to-r from-[#d4c5a9] to-[#c9b99b] text-black py-3 px-6 rounded-lg font-semibold hover:from-[#c9b99b] hover:to-[#d4c5a9] transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
              >
                {submitting ? 'Submitting...' : 'Submit Survey'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

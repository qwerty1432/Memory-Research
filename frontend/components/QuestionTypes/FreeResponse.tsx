'use client';

interface FreeResponseProps {
  questionId: string;
  questionText: string;
  required: boolean;
  value: string;
  onChange: (value: string) => void;
}

export default function FreeResponse({
  questionId,
  questionText,
  required,
  value,
  onChange,
}: FreeResponseProps) {
  return (
    <div className="mb-6">
      <label htmlFor={questionId} className="block text-sm font-medium text-gray-700 mb-2">
        {questionText}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <textarea
        id={questionId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        rows={4}
        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#d4c5a9] focus:border-transparent resize-none"
        placeholder="Type your response here..."
      />
    </div>
  );
}

'use client';

interface MCQProps {
  questionId: string;
  questionText: string;
  options: string[];
  required: boolean;
  value: string;
  onChange: (value: string) => void;
}

export default function MCQ({
  questionId,
  questionText,
  options,
  required,
  value,
  onChange,
}: MCQProps) {
  return (
    <div className="mb-6">
      <label className="block text-sm font-medium text-gray-700 mb-3">
        {questionText}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <div className="space-y-2">
        {options.map((option, index) => (
          <label
            key={index}
            className="flex items-center p-3 border border-gray-300 rounded-lg cursor-pointer hover:bg-[#fff8e7] transition-colors"
          >
            <input
              type="radio"
              name={questionId}
              value={option}
              checked={value === option}
              onChange={(e) => onChange(e.target.value)}
              required={required}
              className="mr-3 text-[#d4c5a9] focus:ring-[#d4c5a9]"
            />
            <span className="text-gray-700">{option}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

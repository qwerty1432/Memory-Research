'use client';

interface YesNoProps {
  questionId: string;
  questionText: string;
  required: boolean;
  value: string;
  onChange: (value: string) => void;
}

export default function YesNo({
  questionId,
  questionText,
  required,
  value,
  onChange,
}: YesNoProps) {
  return (
    <div className="mb-6">
      <label className="block text-sm font-medium text-gray-700 mb-3">
        {questionText}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <div className="flex gap-4">
        <label
          className={`flex items-center p-4 border-2 rounded-lg cursor-pointer flex-1 transition-all hover:bg-[#fff8e7] ${
            value === 'Yes' ? 'border-[#d4c5a9] bg-[#fff8e7]' : 'border-gray-300'
          }`}
        >
          <input
            type="radio"
            name={questionId}
            value="Yes"
            checked={value === 'Yes'}
            onChange={(e) => onChange(e.target.value)}
            required={required}
            className="mr-3 text-[#d4c5a9] focus:ring-[#d4c5a9]"
          />
          <span className="text-gray-700 font-medium">Yes</span>
        </label>
        <label
          className={`flex items-center p-4 border-2 rounded-lg cursor-pointer flex-1 transition-all hover:bg-[#fff8e7] ${
            value === 'No' ? 'border-[#d4c5a9] bg-[#fff8e7]' : 'border-gray-300'
          }`}
        >
          <input
            type="radio"
            name={questionId}
            value="No"
            checked={value === 'No'}
            onChange={(e) => onChange(e.target.value)}
            required={required}
            className="mr-3 text-[#d4c5a9] focus:ring-[#d4c5a9]"
          />
          <span className="text-gray-700 font-medium">No</span>
        </label>
      </div>
    </div>
  );
}

'use client';

interface RatingProps {
  questionId: string;
  questionText: string;
  minRating: number;
  maxRating: number;
  required: boolean;
  value: number | null;
  onChange: (value: number) => void;
}

export default function Rating({
  questionId,
  questionText,
  minRating,
  maxRating,
  required,
  value,
  onChange,
}: RatingProps) {
  const ratings = Array.from({ length: maxRating - minRating + 1 }, (_, i) => minRating + i);

  return (
    <div className="mb-6">
      <label className="block text-sm font-medium text-gray-700 mb-3">
        {questionText}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-500">{minRating}</span>
        <div className="flex gap-2 flex-1">
          {ratings.map((rating) => (
            <button
              key={rating}
              type="button"
              onClick={() => onChange(rating)}
              className={`flex-1 py-3 px-4 rounded-lg border-2 transition-all ${
                value === rating
                  ? 'border-[#d4c5a9] bg-[#fff8e7] text-black font-semibold'
                  : 'border-gray-300 bg-white text-gray-700 hover:border-[#d4c5a9] hover:bg-[#fff8e7]'
              }`}
            >
              {rating}
            </button>
          ))}
        </div>
        <span className="text-sm text-gray-500">{maxRating}</span>
      </div>
      {value !== null && (
        <p className="mt-2 text-sm text-gray-600">Selected: {value}</p>
      )}
    </div>
  );
}

'use client';

interface ProgressDashboardProps {
  onBack: () => void;
}

export function ProgressDashboard({ onBack }: ProgressDashboardProps) {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Learning Progress
          </h2>
          <button
            onClick={onBack}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
          >
            Back to Topics
          </button>
        </div>

        <div className="text-center py-12">
          <div className="text-gray-400 mb-4">
            <svg className="mx-auto h-16 w-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h3 className="text-xl font-medium text-gray-900 dark:text-white mb-2">
            Progress Dashboard Coming Soon
          </h3>
          <p className="text-gray-600 dark:text-gray-400 max-w-md mx-auto mb-6">
            Track your learning journey, view skill mastery levels, and get personalized 
            recommendations based on your performance.
          </p>
          
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6 max-w-2xl mx-auto">
            <h4 className="text-lg font-medium text-blue-900 dark:text-blue-300 mb-3">
              🚀 Coming Features
            </h4>
            <ul className="text-left text-blue-800 dark:text-blue-400 space-y-2">
              <li>• Skill mastery heat maps</li>
              <li>• Learning streak tracking</li>
              <li>• Performance analytics over time</li>
              <li>• Personalized learning recommendations</li>
              <li>• Achievement badges and milestones</li>
              <li>• Spaced repetition scheduling</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
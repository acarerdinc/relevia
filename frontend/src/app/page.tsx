'use client';

import { useState, useEffect } from 'react';
import { AdaptiveLearning } from '@/components/AdaptiveLearning';
import { ProgressDashboard } from '@/components/ProgressDashboard';

export default function Home() {
  const [currentView, setCurrentView] = useState<'learning' | 'progress'>('learning');
  const handleViewChange = (view: string) => {
    setCurrentView(view as 'learning' | 'progress');
  };

  const handleBackToLearning = () => {
    setCurrentView('learning');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <button
                onClick={() => setCurrentView('learning')}
                className="flex items-center group hover:opacity-80 transition-opacity"
              >
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                  🧠 Relevia
                </h1>
                <span className="ml-2 text-sm text-gray-500 dark:text-gray-400 group-hover:text-blue-500 dark:group-hover:text-blue-300 transition-colors">
                  Adaptive AI Learning
                </span>
              </button>
            </div>
            <nav className="flex space-x-4">
              <button
                onClick={() => setCurrentView('learning')}
                className={`px-3 py-2 rounded-md text-sm font-medium ${
                  currentView === 'learning'
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                }`}
              >
                🧠 Learning
              </button>
              <button
                onClick={() => setCurrentView('progress')}
                className={`px-3 py-2 rounded-md text-sm font-medium ${
                  currentView === 'progress'
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                }`}
              >
                📊 Progress
              </button>
            </nav>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentView === 'learning' && (
          <AdaptiveLearning onViewChange={handleViewChange} />
        )}
        
        {currentView === 'progress' && (
          <ProgressDashboard onBack={handleBackToLearning} />
        )}
      </main>
    </div>
  );
}

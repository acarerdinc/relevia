'use client';

import { useState, useEffect } from 'react';
import { apiService, type Topic } from '@/lib/api';

interface TopicSelectorProps {
  onTopicSelect: (topic: Topic) => void;
}

export function TopicSelector({ onTopicSelect }: TopicSelectorProps) {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  useEffect(() => {
    loadTopics();
  }, []);

  const loadTopics = async () => {
    try {
      setLoading(true);
      const response = await apiService.getTopics();
      setTopics(response.topics);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load topics');
    } finally {
      setLoading(false);
    }
  };

  const getTopicsByCategory = () => {
    if (selectedCategory === 'all') {
      return topics.filter(topic => topic.parent_id !== null); // Exclude root topic
    }
    
    // Find parent topic
    const parentTopic = topics.find(t => t.name === selectedCategory);
    if (!parentTopic) return [];
    
    return topics.filter(topic => topic.parent_id === parentTopic.id);
  };

  const getMainCategories = () => {
    const rootTopic = topics.find(t => t.parent_id === null);
    if (!rootTopic) return [];
    
    return topics.filter(topic => topic.parent_id === rootTopic.id);
  };

  const getDifficultyColor = (min: number, max: number) => {
    const avg = (min + max) / 2;
    if (avg <= 3) return 'bg-green-100 text-green-800 border-green-200';
    if (avg <= 6) return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    return 'bg-red-100 text-red-800 border-red-200';
  };

  const getDifficultyLabel = (min: number, max: number) => {
    const avg = (min + max) / 2;
    if (avg <= 3) return 'Beginner';
    if (avg <= 6) return 'Intermediate';
    return 'Advanced';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading topics...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-red-800 mb-2">Error Loading Topics</h3>
        <p className="text-red-600 mb-4">{error}</p>
        <button
          onClick={loadTopics}
          className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  const mainCategories = getMainCategories();
  const displayedTopics = getTopicsByCategory();

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Choose Your AI Learning Path
        </h2>
        <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
          Select a topic to start your personalized learning journey. Our adaptive quiz engine 
          will adjust to your knowledge level in real-time.
        </p>
      </div>

      {/* Category Filter */}
      <div className="flex flex-wrap justify-center gap-2">
        <button
          onClick={() => setSelectedCategory('all')}
          className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
            selectedCategory === 'all'
              ? 'bg-blue-600 text-white'
              : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
          }`}
        >
          All Topics
        </button>
        {mainCategories.map((category) => (
          <button
            key={category.id}
            onClick={() => setSelectedCategory(category.name)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              selectedCategory === category.name
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
            }`}
          >
            {category.name}
          </button>
        ))}
      </div>

      {/* Topics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {displayedTopics.map((topic) => (
          <div
            key={topic.id}
            className="bg-white dark:bg-gray-800 rounded-lg shadow-md hover:shadow-lg transition-shadow border border-gray-200 dark:border-gray-700"
          >
            <div className="p-6">
              <div className="flex items-start justify-between mb-3">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {topic.name}
                </h3>
                <span
                  className={`px-2 py-1 rounded-full text-xs font-medium border ${getDifficultyColor(
                    topic.difficulty_min,
                    topic.difficulty_max
                  )}`}
                >
                  {getDifficultyLabel(topic.difficulty_min, topic.difficulty_max)}
                </span>
              </div>
              
              <p className="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-3">
                {topic.description}
              </p>
              
              <div className="flex items-center justify-between">
                <div className="text-xs text-gray-500">
                  Difficulty: {topic.difficulty_min}-{topic.difficulty_max}/10
                </div>
                <button
                  onClick={() => onTopicSelect(topic)}
                  className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 transition-colors"
                >
                  Start Quiz
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {displayedTopics.length === 0 && (
        <div className="text-center py-12">
          <div className="text-gray-400 mb-2">
            <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-1">
            No topics found
          </h3>
          <p className="text-gray-500 dark:text-gray-400">
            Try selecting a different category or refresh the page.
          </p>
        </div>
      )}
    </div>
  );
}
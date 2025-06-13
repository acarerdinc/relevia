'use client';

import { useState } from 'react';
import { apiService } from '@/lib/api';

interface LearningRequestInputProps {
  onTopicCreated: (result: any) => void;
  onLoading: (loading: boolean) => void;
}

export function LearningRequestInput({ onTopicCreated, onLoading }: LearningRequestInputProps) {
  const [requestText, setRequestText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!requestText.trim() || requestText.length < 3) {
      return;
    }

    setIsSubmitting(true);
    onLoading(true);

    try {
      const result = await apiService.requestLearningTopic(requestText.trim());
      
      if (result.success) {
        onTopicCreated(result);
        setRequestText(''); // Clear the input
        setShowSuggestions(false);
      } else {
        console.error('Failed to create topic:', result);
      }
    } catch (error) {
      console.error('Error requesting learning topic:', error);
    } finally {
      setIsSubmitting(false);
      onLoading(false);
    }
  };

  const loadSuggestions = async () => {
    try {
      const result = await apiService.getLearningSuggestions(1, 3);
      setSuggestions(result.suggestions || []);
      setShowSuggestions(true);
    } catch (error) {
      console.error('Error loading suggestions:', error);
    }
  };

  const handleSuggestionClick = (suggestion: any) => {
    setRequestText(suggestion.topic_name);
    setShowSuggestions(false);
  };

  const exampleRequests = [
    "I want to learn about computer vision for medical imaging",
    "Teach me reinforcement learning for robotics",
    "I'm interested in natural language processing with transformers",
    "Show me how GANs work in practice",
    "I want to understand gradient descent optimization"
  ];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="text-2xl">🚀</div>
        <h3 className="text-xl font-bold text-gray-900 dark:text-white">
          What do you want to learn?
        </h3>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="relative">
          <textarea
            value={requestText}
            onChange={(e) => setRequestText(e.target.value)}
            placeholder="Describe what you'd like to learn... (e.g., 'I want to learn about computer vision for medical imaging')"
            className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg 
                     bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                     focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     resize-none transition-colors"
            rows={3}
            maxLength={500}
            disabled={isSubmitting}
          />
          <div className="absolute bottom-2 right-2 text-xs text-gray-500">
            {requestText.length}/500
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={loadSuggestions}
              disabled={isSubmitting}
              className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 
                       dark:hover:text-blue-300 transition-colors disabled:opacity-50"
            >
              💡 Get suggestions
            </button>
            
            {suggestions.length > 0 && showSuggestions && (
              <span className="text-xs text-gray-500">
                ({suggestions.length} available)
              </span>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting || requestText.length < 3}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 
                     disabled:bg-gray-400 disabled:cursor-not-allowed
                     transition-colors flex items-center gap-2"
          >
            {isSubmitting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                Creating...
              </>
            ) : (
              <>
                <span>🎯</span>
                Create Learning Path
              </>
            )}
          </button>
        </div>
      </form>

      {/* Suggestions dropdown */}
      {showSuggestions && suggestions.length > 0 && (
        <div className="mt-4 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700">
          <div className="p-3 border-b border-gray-200 dark:border-gray-600">
            <h4 className="text-sm font-medium text-gray-900 dark:text-white">
              💡 Recommended based on your progress:
            </h4>
          </div>
          <div className="p-2 space-y-2">
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                onClick={() => handleSuggestionClick(suggestion)}
                className="w-full text-left p-3 rounded-lg hover:bg-white dark:hover:bg-gray-600 
                         transition-colors group"
              >
                <div className="text-sm font-medium text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400">
                  {suggestion.topic_name}
                </div>
                {suggestion.reasoning && (
                  <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                    {suggestion.reasoning}
                  </div>
                )}
              </button>
            ))}
          </div>
          <div className="p-2 border-t border-gray-200 dark:border-gray-600">
            <button
              onClick={() => setShowSuggestions(false)}
              className="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            >
              Hide suggestions
            </button>
          </div>
        </div>
      )}

      {/* Example requests */}
      <div className="mt-4 border-t border-gray-200 dark:border-gray-600 pt-4">
        <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
          ✨ Example requests:
        </h4>
        <div className="flex flex-wrap gap-2">
          {exampleRequests.slice(0, 3).map((example, index) => (
            <button
              key={index}
              onClick={() => setRequestText(example)}
              disabled={isSubmitting}
              className="text-xs px-3 py-1 bg-gray-100 dark:bg-gray-600 text-gray-700 dark:text-gray-300 
                       rounded-full hover:bg-gray-200 dark:hover:bg-gray-500 transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {example.length > 50 ? example.substring(0, 47) + '...' : example}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
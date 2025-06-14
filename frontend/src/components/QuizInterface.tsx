'use client';

import { useState, useEffect } from 'react';
import { apiService, type Topic, type Question, type QuizSession } from '@/lib/api';

interface QuizInterfaceProps {
  topic: Topic;
  onQuizComplete: () => void;
  onBack: () => void;
}

export function QuizInterface({ topic, onQuizComplete, onBack }: QuizInterfaceProps) {
  const [session, setSession] = useState<QuizSession | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<string>('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [questionStartTime, setQuestionStartTime] = useState<number>(Date.now());
  const [questionCount, setQuestionCount] = useState(0);

  useEffect(() => {
    startQuiz();
  }, [topic]);

  const startQuiz = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const quizSession = await apiService.startQuiz(topic.id);
      setSession(quizSession);
      
      await loadNextQuestion(quizSession.session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start quiz');
    } finally {
      setLoading(false);
    }
  };

  const loadNextQuestion = async (sessionId: number) => {
    try {
      setLoading(true);
      const question = await apiService.getQuestion(sessionId);
      setCurrentQuestion(question);
      setSelectedAnswer('');
      setShowFeedback(false);
      setFeedback(null);
      setQuestionStartTime(Date.now());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load question');
    } finally {
      setLoading(false);
    }
  };

  const submitAction = async (action: 'answer' | 'teach_me' | 'skip') => {
    if (!currentQuestion || !session) return;
    if (action === 'answer' && !selectedAnswer) return;

    try {
      setLoading(true);
      const timeSpent = Math.floor((Date.now() - questionStartTime) / 1000);
      
      const result = await apiService.submitAnswer(
        currentQuestion.quiz_question_id,
        action === 'answer' ? selectedAnswer : '',
        timeSpent,
        action
      );
      
      setFeedback(result);
      setShowFeedback(true);
      // Increment question count for all actions (answer, teach_me, skip)
      setQuestionCount(prev => prev + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit action');
    } finally {
      setLoading(false);
    }
  };

  const handleNext = async () => {
    if (!session) return;

    // After 5 questions, offer to complete the quiz
    if (questionCount >= 5) {
      const shouldContinue = confirm('You\'ve completed 5 questions! Would you like to continue with more questions?');
      if (!shouldContinue) {
        onQuizComplete();
        return;
      }
    }

    try {
      await loadNextQuestion(session.session_id);
    } catch (err) {
      // If no more questions, complete the quiz
      onQuizComplete();
    }
  };

  const getDifficultyColor = (difficulty: number) => {
    if (difficulty <= 3) return 'text-green-600 bg-green-100';
    if (difficulty <= 6) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getAccuracyColor = (accuracy: number) => {
    if (accuracy >= 0.8) return 'text-green-600';
    if (accuracy >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  if (loading && !currentQuestion) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading quiz...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-red-800 mb-2">Quiz Error</h3>
        <p className="text-red-600 mb-4">{error}</p>
        <div className="flex gap-2">
          <button
            onClick={startQuiz}
            className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
          <button
            onClick={onBack}
            className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 transition-colors"
          >
            Back to Topics
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
              {topic.name} Quiz
            </h2>
            <p className="text-gray-600 dark:text-gray-400">{topic.description}</p>
          </div>
          <button
            onClick={onBack}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {feedback && (
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-4">
              <span className="text-gray-600 dark:text-gray-400">
                Questions: {feedback.session_progress.total_questions}
              </span>
              <span className="text-gray-600 dark:text-gray-400">
                Correct: {feedback.session_progress.correct_answers}
              </span>
              <span className={`font-medium ${getAccuracyColor(feedback.session_progress.accuracy)}`}>
                Accuracy: {Math.round(feedback.session_progress.accuracy * 100)}%
              </span>
            </div>
            {currentQuestion && (
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getDifficultyColor(currentQuestion.difficulty)}`}>
                Difficulty: {currentQuestion.difficulty}/10
              </span>
            )}
          </div>
        )}
      </div>

      {/* Question */}
      {currentQuestion && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <div className="mb-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                Question {questionCount + 1}
              </h3>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getDifficultyColor(currentQuestion.difficulty)}`}>
                Level {currentQuestion.difficulty}
              </span>
            </div>
            <p className="text-gray-800 dark:text-gray-200 text-lg leading-relaxed">
              {currentQuestion.question}
            </p>
          </div>

          {/* Answer Options */}
          <div className="space-y-3 mb-6">
            {currentQuestion.options.map((option, index) => {
              // Debug mode highlighting
              const isDebugCorrect = currentQuestion.debug_correct_index === index;
              
              return (
                <button
                  key={index}
                  onClick={() => !showFeedback && setSelectedAnswer(option)}
                  disabled={showFeedback}
                  className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
                    showFeedback
                      ? option === feedback?.correct_answer
                        ? 'border-green-500 bg-green-50 text-green-800'
                        : option === selectedAnswer && option !== feedback?.correct_answer
                        ? 'border-red-500 bg-red-50 text-red-800'
                        : 'border-gray-200 bg-gray-50 text-gray-600'
                      : selectedAnswer === option
                      ? 'border-blue-500 bg-blue-50 text-blue-800'
                      : isDebugCorrect && !showFeedback
                      ? 'border-emerald-400 bg-emerald-50 text-emerald-800 ring-2 ring-emerald-200'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  }`}
              >
                <div className="flex items-center">
                  <span className="w-8 h-8 rounded-full border-2 border-current flex items-center justify-center text-sm font-medium mr-3">
                    {String.fromCharCode(65 + index)}
                  </span>
                  {option}
                  {/* Debug mode indicator */}
                  {isDebugCorrect && !showFeedback && (
                    <span className="ml-auto text-emerald-600 font-bold">🎯</span>
                  )}
                  {showFeedback && option === feedback?.correct_answer && (
                    <span className="ml-auto text-green-600">✓</span>
                  )}
                  {showFeedback && option === selectedAnswer && option !== feedback?.correct_answer && (
                    <span className="ml-auto text-red-600">✗</span>
                  )}
                </div>
              </button>
              );
            })}
          </div>

          {/* Feedback */}
          {showFeedback && feedback && (
            <div className={`p-4 rounded-lg mb-6 ${
              feedback.correct ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
            }`}>
              <div className={`font-medium mb-2 ${feedback.correct ? 'text-green-800' : 'text-red-800'}`}>
                {feedback.correct ? '✅ Correct!' : '❌ Incorrect'}
              </div>
              <p className={`text-sm ${feedback.correct ? 'text-green-700' : 'text-red-700'}`}>
                {feedback.explanation}
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-between">
            <button
              onClick={onQuizComplete}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
            >
              End Quiz
            </button>
            
            {!showFeedback ? (
              <div className="flex gap-2">
                <button
                  onClick={() => submitAction('skip')}
                  disabled={loading}
                  className="bg-gray-500 text-white px-4 py-2 rounded-md hover:bg-gray-600 disabled:bg-gray-400 transition-colors"
                  title="Skip this question - signals low interest"
                >
                  {loading ? '...' : '⏭️ Skip'}
                </button>
                <button
                  onClick={() => submitAction('teach_me')}
                  disabled={loading}
                  className="bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700 disabled:bg-gray-400 transition-colors"
                  title="Learn more about this topic - signals high interest"
                >
                  {loading ? '...' : '🎓 Teach Me'}
                </button>
                <button
                  onClick={() => submitAction('answer')}
                  disabled={!selectedAnswer || loading}
                  className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? 'Submitting...' : 'Submit Answer'}
                </button>
              </div>
            ) : (
              <div className="flex justify-between items-center">
                {feedback?.unlocked_topics && feedback.unlocked_topics.length > 0 && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                    <div className="text-green-800 font-medium text-sm">🎉 New Topics Unlocked!</div>
                    {feedback.unlocked_topics.map((topic: any) => (
                      <div key={topic.id} className="text-green-700 text-sm">
                        • {topic.name}
                      </div>
                    ))}
                  </div>
                )}
                <button
                  onClick={handleNext}
                  className="bg-green-600 text-white px-6 py-2 rounded-md hover:bg-green-700 transition-colors ml-auto"
                >
                  Next Question
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
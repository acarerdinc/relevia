'use client';

import { useState, useEffect, useRef } from 'react';
import { LearningRequestInput } from './LearningRequestInput';

interface LearningDashboard {
  learning_state: {
    focus_area: string;
    recent_accuracy: number;
    learning_momentum: number;
    readiness_score: number;
    sessions_completed: number;
  };
  exploration: {
    topics_unlocked: number;
    total_topics: number;
    exploration_coverage: number;
    recent_discoveries: number;
    discovery_rate: number;
  };
  interests: {
    high_interest_topics: any[];
    growing_interest_topics: any[];
    total_topics_explored: number;
  };
  next_action: {
    type: string;
    description: string;
    confidence: number;
  };
}

interface Question {
  question_id: number;
  quiz_question_id: number;
  question: string;
  options: string[];
  difficulty: number;
  topic_name: string;
  selection_strategy: string;
  mastery_level?: string;
  session_progress?: {
    questions_answered: number;
    session_accuracy: number;
    questions_remaining: number;
  };
  topic_progress?: {
    topic_name: string;
    skill_level: number;
    confidence: number;
    mastery_level: string;
    questions_answered: number;
    proficiency: {
      mastery_level: string;
      questions_answered: number;
      progress_to_next: number;
      can_unlock_subtopics: boolean;
    };
  };
}

interface AdaptiveLearningProps {
  onViewChange: (view: string) => void;
  startSession?: {sessionId: number, topicId: number} | null;
  onSessionUsed?: () => void;
  onTopicsUnlocked?: () => void;
}

export function AdaptiveLearning({ onViewChange, startSession, onSessionUsed, onTopicsUnlocked }: AdaptiveLearningProps) {
  const [dashboard, setDashboard] = useState<LearningDashboard | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [feedback, setFeedback] = useState<any>(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const [questionCount, setQuestionCount] = useState(0);
  const [topicCreationResult, setTopicCreationResult] = useState<any>(null);
  const [showTopicCreationFeedback, setShowTopicCreationFeedback] = useState(false);
  const [isFocusedSession, setIsFocusedSession] = useState(false);
  const processedStartSessionRef = useRef<{sessionId: number, topicId: number} | null>(null);

  useEffect(() => {
    loadDashboard();
  }, []);

  // Handle starting a session passed from ProgressDashboard
  useEffect(() => {
    if (startSession && 
        !sessionId && 
        (!processedStartSessionRef.current || 
         processedStartSessionRef.current.sessionId !== startSession.sessionId)) {
      
      console.log('🎯 Starting session from ProgressDashboard:', startSession);
      
      // Mark this session as processed to prevent double execution
      processedStartSessionRef.current = startSession;
      
      setSessionId(startSession.sessionId);
      setIsFocusedSession(true); // Mark this as a focused session
      
      // Get the first question for this session (focused session)
      getNextQuestion(startSession.sessionId, true);
      
      // Clear the startSession from parent to prevent re-triggering
      if (onSessionUsed) {
        onSessionUsed();
      }
    }
  }, [startSession, sessionId, onSessionUsed]); // Keep all dependencies for React compliance

  // Helper function to reset session state
  const resetSession = () => {
    setSessionId(null);
    setCurrentQuestion(null);
    setIsFocusedSession(false);
    processedStartSessionRef.current = null; // Reset the processed session ref
  };

  const loadDashboard = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/adaptive/dashboard/1');
      const data = await response.json();
      
      // Ensure data has the expected structure
      if (data && data.learning_state && data.exploration && data.interests) {
        setDashboard(data);
      } else {
        console.error('Dashboard data has unexpected structure:', data);
        // Set a default dashboard structure
        setDashboard({
          learning_state: {
            focus_area: "Starting your AI learning journey",
            recent_accuracy: 0,
            learning_momentum: 0,
            readiness_score: 0.5,
            sessions_completed: 0
          },
          exploration: {
            topics_unlocked: 1,
            total_topics: 1,
            exploration_coverage: 0,
            recent_discoveries: 0,
            discovery_rate: 0
          },
          interests: {
            high_interest_topics: [],
            growing_interest_topics: [],
            total_topics_explored: 0
          },
          next_action: {
            type: "continue_learning",
            description: "Start your adaptive learning journey",
            confidence: 0.8
          }
        });
      }
    } catch (error) {
      console.error('Failed to load dashboard:', error);
      // Set default dashboard on error
      setDashboard({
        learning_state: {
          focus_area: "Starting your AI learning journey",
          recent_accuracy: 0,
          learning_momentum: 0,
          readiness_score: 0.5,
          sessions_completed: 0
        },
        exploration: {
          topics_unlocked: 1,
          total_topics: 1,
          exploration_coverage: 0,
          recent_discoveries: 0,
          discovery_rate: 0
        },
        interests: {
          high_interest_topics: [],
          growing_interest_topics: [],
          total_topics_explored: 0
        },
        next_action: {
          type: "continue_learning",
          description: "Start your adaptive learning journey",
          confidence: 0.8
        }
      });
    }
  };

  const startLearning = async () => {
    console.log('🚀 Continue Learning button clicked');
    setIsLoading(true);
    setIsFocusedSession(false); // This is adaptive learning, not focused
    try {
      console.log('📡 Fetching from: http://localhost:8000/api/v1/adaptive/continue/1');
      const response = await fetch('http://localhost:8000/api/v1/adaptive/continue/1');
      console.log('📡 Response status:', response.status);
      const data = await response.json();
      console.log('📡 Response data:', data);
      
      if (data.session && data.question) {
        console.log('✅ Got session and question, setting up...');
        setSessionId(data.session.session_id);
        setCurrentQuestion(data.question);
        setQuestionCount(1);
      } else if (data.session_id) {
        console.log('✅ Got session_id only, fetching question...');
        setSessionId(data.session_id);
        await getNextQuestion(data.session_id, false); // Explicitly use adaptive endpoint
      } else {
        console.error('❌ Unexpected response structure:', data);
      }
    } catch (error) {
      console.error('❌ Failed to start learning:', error);
      resetSession(); // Reset session on start error
    } finally {
      setIsLoading(false);
    }
  };


  const getNextQuestion = async (sessionId: number, isFocusedSession: boolean = false) => {
    try {
      // Use focused quiz endpoint if this is a session started from ProgressDashboard
      const endpoint = isFocusedSession 
        ? `http://localhost:8000/api/v1/quiz/question/${sessionId}`
        : `http://localhost:8000/api/v1/adaptive/question/${sessionId}`;
      
      const response = await fetch(endpoint);
      
      if (!response.ok) {
        setCurrentQuestion(null);
        await loadDashboard(); // Refresh dashboard
        return;
      }
      
      const data = await response.json();
      
      if (data.error) {
        console.log('No more questions available, resetting session');
        resetSession(); // Reset session so Continue Learning works again
        await loadDashboard(); // Refresh dashboard
      } else {
        setCurrentQuestion(data);
        setQuestionCount(prev => prev + 1);
      }
      
      setIsLoading(false);
    } catch (error) {
      console.error('Failed to get question:', error);
      resetSession(); // Reset session on error too
      await loadDashboard();
      setIsLoading(false);
    }
  };

  const submitAnswer = async (answer: string | null, action: string) => {
    if (!currentQuestion || !sessionId) return;

    setIsLoading(true);
    try {
      // Determine endpoint based on selection strategy
      const isFocused = currentQuestion.selection_strategy === 'focused';
      const isAdaptive = currentQuestion.selection_strategy !== 'traditional' && !isFocused;
      
      const endpoint = isFocused 
        ? 'http://localhost:8000/api/v1/quiz/answer'
        : isAdaptive 
          ? 'http://localhost:8000/api/v1/adaptive/answer'
          : 'http://localhost:8000/api/v1/quiz/answer';
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          quiz_question_id: currentQuestion.quiz_question_id,
          answer: answer,
          time_spent: 15,
          action: action
        })
      });

      const result = await response.json();
      setFeedback(result);
      setShowFeedback(true);
      setIsLoading(false);

      // Don't auto-advance - let user control when to continue

      // Refresh dashboard if topics were unlocked
      if (result.unlocked_topics?.length > 0) {
        setTimeout(() => loadDashboard(), 1000);
        // Notify parent component to refresh tree view
        if (onTopicsUnlocked) {
          onTopicsUnlocked();
        }
      }

    } catch (error) {
      console.error('Failed to submit answer:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const formatPercentage = (value: number) => Math.round(value * 100);

  const handleTopicCreated = (result: any) => {
    setTopicCreationResult(result);
    setShowTopicCreationFeedback(true);
    // Refresh dashboard to show new topic
    setTimeout(() => {
      loadDashboard();
    }, 1000);
    // Keep the feedback visible until user manually dismisses or navigates
  };

  const handleTopicCreationLoading = (loading: boolean) => {
    // You can add additional loading states here if needed
  };

  const navigateToNewTopic = async () => {
    if (topicCreationResult?.topic_id) {
      try {
        // Start a quiz session for the specific topic
        setIsLoading(true);
        console.log('🚀 Starting learning for topic:', topicCreationResult.topic_id);
        
        // Use the regular quiz API for specific topics
        const response = await fetch('http://localhost:8000/api/v1/quiz/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            topic_id: topicCreationResult.topic_id,
            user_id: 1
          })
        });
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error('Quiz start failed:', response.status, errorText);
          throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
        }
        
        const session = await response.json();
        console.log('✅ Quiz session created:', session);
        setSessionId(session.session_id);
        
        // Get first question using the regular quiz endpoint
        const questionResponse = await fetch(`http://localhost:8000/api/v1/quiz/question/${session.session_id}`);
        
        if (!questionResponse.ok) {
          const questionErrorText = await questionResponse.text();
          console.error('Get question failed:', questionResponse.status, questionErrorText);
          throw new Error(`Failed to get question: ${questionResponse.status} - ${questionErrorText}`);
        }
        
        const questionData = await questionResponse.json();
        console.log('✅ First question received:', questionData);
        setCurrentQuestion(questionData);
        setShowTopicCreationFeedback(false);
        setIsLoading(false);
      } catch (error) {
        console.error('Failed to start learning new topic:', error);
        alert(`Failed to start learning: ${error instanceof Error ? error.message : 'Unknown error'}. The topic has been created and you can access it from the main Continue Learning button.`);
        setIsLoading(false);
      }
    }
  };

  if (!dashboard) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (currentQuestion) {
    return (
      <div className="max-w-4xl mx-auto">
        {/* Progress Header */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Question {questionCount}
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Topic: {currentQuestion.topic_name} • Strategy: {currentQuestion.selection_strategy}
              </p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  Infinite Learning
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Session accuracy: {formatPercentage(currentQuestion.session_progress?.session_accuracy || 0)}%
                </p>
              </div>
              <button
                onClick={() => {
                  resetSession();
                  setQuestionCount(0);
                  setShowFeedback(false);
                }}
                className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                title="Exit to main page"
              >
                ← Exit
              </button>
            </div>
          </div>
        </div>


        {/* Question Card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-8">
          {isLoading ? (
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600 dark:text-gray-400">Loading next question...</p>
            </div>
          ) : showFeedback ? (
            <div className="text-center">
              <div className={`text-6xl mb-4 ${feedback.correct ? 'text-green-500' : feedback.correct === false ? 'text-red-500' : 'text-blue-500'}`}>
                {feedback.correct ? '✅' : feedback.correct === false ? '❌' : '💡'}
              </div>
              <h3 className={`text-xl font-semibold mb-4 ${feedback.correct ? 'text-green-700 dark:text-green-400' : feedback.correct === false ? 'text-red-700 dark:text-red-400' : 'text-blue-700 dark:text-blue-400'}`}>
                {feedback.correct ? 'Correct!' : feedback.correct === false ? 'Let\'s learn from this!' : 'Learning moment!'}
              </h3>
              <div className="text-gray-700 dark:text-gray-300 mb-6 text-left max-w-3xl mx-auto">
                <p className="leading-relaxed">{feedback.explanation}</p>
              </div>
              
              {/* Mastery Progress Info */}
              {feedback?.mastery_advancement && (
                <div className="mb-4 p-4 rounded-lg bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 border border-purple-200 dark:border-purple-800">
                  <div className="text-center">
                    <span className="text-sm font-medium text-purple-800 dark:text-purple-200">
                      Mastery Progress
                    </span>
                    <p className="text-xs text-purple-600 dark:text-purple-400 mt-1">
                      {feedback.mastery_advancement.questions_at_level} question{feedback.mastery_advancement.questions_at_level !== 1 ? 's' : ''} answered at {feedback.mastery_advancement.current_level} level
                    </p>
                    {!feedback.mastery_advancement.advanced && feedback.mastery_advancement.questions_needed > 0 && (
                      <p className="text-xs text-purple-600 dark:text-purple-400">
                        {feedback.mastery_advancement.questions_needed} more correct answers needed for {(() => {
                          const currentLevel = feedback.mastery_advancement.current_level.toLowerCase();
                          const nextLevel: {[key: string]: string} = {
                            'novice': 'Competent',
                            'competent': 'Proficient', 
                            'proficient': 'Expert',
                            'expert': 'Master'
                          };
                          return nextLevel[currentLevel] || 'next';
                        })()} level
                      </p>
                    )}
                    {!feedback.mastery_advancement.advanced && feedback.mastery_advancement.questions_needed === 0 && feedback.mastery_advancement.current_level !== 'master' && (
                      <p className="text-xs text-green-600 dark:text-green-400">
                        ✨ Ready to advance! Keep answering correctly to level up!
                      </p>
                    )}
                    {feedback.mastery_advancement.advanced && (
                      <div className="mt-2">
                        <span className="text-sm font-bold text-green-600 dark:text-green-400">
                          🎉 Level Up!
                        </span>
                        <p className="text-xs text-green-600 dark:text-green-400">
                          {feedback.mastery_advancement.old_level} → {feedback.mastery_advancement.new_level}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {feedback.unlocked_topics?.length > 0 && (
                <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 mb-4">
                  <h4 className="font-semibold text-green-800 dark:text-green-200 mb-2">
                    🎉 New Areas Unlocked!
                  </h4>
                  {feedback.unlocked_topics.map((topic: any, index: number) => (
                    <p key={index} className="text-sm text-green-700 dark:text-green-300">
                      • {topic.name}
                    </p>
                  ))}
                </div>
              )}
              
              <button
                onClick={() => {
                  setShowFeedback(false);
                  setIsLoading(true);
                  if (sessionId) {
                    getNextQuestion(sessionId, isFocusedSession);
                  }
                }}
                className="mt-6 px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                Continue Learning
              </button>
            </div>
          ) : (
            <>
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
                {currentQuestion.question}
              </h3>
              
              <div className="space-y-3 mb-6">
                {(currentQuestion.options || []).map((option, index) => {
                  // Clean option text by removing any existing letter prefixes (A., B., etc.) and parentheses
                  const cleanOption = option.replace(/^[A-Z]\.?\s*[A-Z]\)\s*/, '').replace(/^[A-Z]\.\s*/, '').replace(/^[A-Z]\)\s*/, '');
                  
                  // Debug mode highlighting
                  const isDebugCorrect = currentQuestion.debug_correct_index === index;
                  
                  return (
                    <button
                      key={index}
                      onClick={() => submitAnswer(index.toString(), 'answer')}
                      disabled={isLoading}
                      className={`w-full text-left p-4 border rounded-lg transition-colors disabled:opacity-50 ${
                        isDebugCorrect
                          ? 'border-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 ring-2 ring-emerald-200 dark:ring-emerald-800'
                          : 'border-gray-200 dark:border-gray-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-300 dark:hover:border-blue-600'
                      }`}
                    >
                      <div className="flex items-center">
                        <span className={`font-medium mr-3 ${
                          isDebugCorrect 
                            ? 'text-emerald-600 dark:text-emerald-400' 
                            : 'text-blue-600 dark:text-blue-400'
                        }`}>
                          {String.fromCharCode(65 + index)}.
                        </span>
                        {cleanOption}
                        {/* Debug mode indicator */}
                        {isDebugCorrect && (
                          <span className="ml-auto text-emerald-600 dark:text-emerald-400 font-bold">🎯</span>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
              
              {/* Action Buttons */}
              <div className="flex justify-between">
                <button
                  onClick={() => submitAnswer(null, 'teach_me')}
                  disabled={isLoading}
                  className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                >
                  💡 Teach Me
                </button>
                
                <button
                  onClick={() => submitAnswer(null, 'skip')}
                  disabled={isLoading}
                  className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50"
                >
                  ⏭️ Skip
                </button>
              </div>
            </>
          )}
        </div>

        {/* Topic Progress with Mastery Levels - Bottom */}
        {currentQuestion.topic_progress && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 mt-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              📊 Current Topic Progress
            </h3>
            
            {/* Mastery Level Display */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Mastery Journey
                </span>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {currentQuestion.mastery_level ? currentQuestion.mastery_level.charAt(0).toUpperCase() + currentQuestion.mastery_level.slice(1) : 'Novice'}
                </span>
              </div>
              
              {/* Mastery Level Progress Bar */}
              <div className="relative">
                {/* Progress Line - Behind the circles */}
                <div className="absolute top-4 left-0 right-0 h-0.5 bg-gray-200 dark:bg-gray-700 z-0" style={{ width: '100%' }}>
                  <div 
                    className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-red-500 transition-all duration-500"
                    style={{ 
                      width: `${
                        (currentQuestion.mastery_level || 'novice').toLowerCase() === 'novice' ? '10%' :
                        (currentQuestion.mastery_level || 'novice').toLowerCase() === 'competent' ? '30%' :
                        (currentQuestion.mastery_level || 'novice').toLowerCase() === 'proficient' ? '50%' :
                        (currentQuestion.mastery_level || 'novice').toLowerCase() === 'expert' ? '70%' :
                        '90%'
                      }` 
                    }}
                  ></div>
                </div>
                
                {/* Level Circles - In front */}
                <div className="flex justify-between mb-2 relative z-10">
                  {['Novice', 'Competent', 'Proficient', 'Expert', 'Master'].map((level, index) => (
                    <div key={level} className="flex flex-col items-center relative" style={{ width: '20%' }}>
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300 relative z-10 ${
                        index === 0 ? 'bg-blue-500 text-white' :
                        index === 1 ? 'bg-green-500 text-white' :
                        index === 2 ? 'bg-purple-500 text-white' :
                        index === 3 ? 'bg-orange-500 text-white' :
                        'bg-red-500 text-white'
                      } ${
                        // Highlight current level
                        (currentQuestion.mastery_level || 'novice').toLowerCase() === level.toLowerCase()
                          ? 'ring-4 ring-opacity-30 ring-current scale-110'
                          : ''
                      }`}>
                        {index === 0 ? '🌱' :
                         index === 1 ? '📚' :
                         index === 2 ? '🎯' :
                         index === 3 ? '🚀' :
                         '👑'}
                      </div>
                      <span className={`text-xs mt-1 ${
                        (currentQuestion.mastery_level || 'novice').toLowerCase() === level.toLowerCase()
                          ? 'font-bold text-gray-900 dark:text-white'
                          : 'text-gray-500 dark:text-gray-400'
                      }`}>
                        {level}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Mastery Progress */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Progress to Next Level
                  </span>
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {Math.round(currentQuestion.topic_progress.proficiency.progress_to_next || 0)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 mb-2">
                  <div 
                    className={`h-3 rounded-full transition-all duration-500 ${
                      (currentQuestion.topic_progress.proficiency.progress_to_next || 0) >= 100 
                        ? 'bg-green-500' 
                        : (currentQuestion.topic_progress.proficiency.progress_to_next || 0) >= 75
                        ? 'bg-yellow-500'
                        : 'bg-blue-500'
                    }`}
                    style={{ width: `${Math.min(100, currentQuestion.topic_progress.proficiency.progress_to_next || 0)}%` }}
                  ></div>
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {currentQuestion.topic_progress.proficiency.questions_answered || 0} questions answered at {currentQuestion.topic_progress.proficiency.mastery_level || 'novice'} level
                </div>
              </div>

              {/* Confidence Progress */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Confidence Level
                  </span>
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {Math.round(((currentQuestion.topic_progress.confidence || 0) / 10) * 100)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 mb-2">
                  <div 
                    className={`h-3 rounded-full transition-all duration-500 ${
                      (currentQuestion.topic_progress.confidence || 0) >= 7 
                        ? 'bg-green-500' 
                        : (currentQuestion.topic_progress.confidence || 0) >= 4
                        ? 'bg-yellow-500'
                        : 'bg-red-400'
                    }`}
                    style={{ width: `${Math.min(100, ((currentQuestion.topic_progress.confidence || 0) / 10) * 100)}%` }}
                  ></div>
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  Builds through consistent correct answers and practice
                </div>
              </div>
            </div>

            {/* Mastery Progress Info */}
            {feedback?.mastery_advancement && (
              <div className="mt-4 p-4 rounded-lg bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 border border-purple-200 dark:border-purple-800">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-purple-800 dark:text-purple-200">
                      Mastery Progress
                    </span>
                    <p className="text-xs text-purple-600 dark:text-purple-400 mt-1">
                      {feedback.mastery_advancement.questions_at_level} question{feedback.mastery_advancement.questions_at_level !== 1 ? 's' : ''} answered at {feedback.mastery_advancement.current_level} level
                    </p>
                    {!feedback.mastery_advancement.advanced && feedback.mastery_advancement.questions_needed && (
                      <p className="text-xs text-purple-600 dark:text-purple-400">
                        {feedback.mastery_advancement.questions_needed} more questions needed for next level
                      </p>
                    )}
                  </div>
                  {feedback.mastery_advancement.advanced && (
                    <div className="text-right">
                      <span className="text-sm font-bold text-green-600 dark:text-green-400">
                        🎉 Level Up!
                      </span>
                      <p className="text-xs text-green-600 dark:text-green-400">
                        {feedback.mastery_advancement.old_level} → {feedback.mastery_advancement.new_level}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Unlock Status */}
            <div className="mt-4 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  🔓 Subtopic Unlocking
                </span>
                <span className={`text-sm font-semibold ${
                  currentQuestion.topic_progress.proficiency.can_unlock_subtopics 
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-gray-600 dark:text-gray-400'
                }`}>
                  {currentQuestion.topic_progress.proficiency.can_unlock_subtopics ? 'Unlocked!' : 'Locked'}
                </span>
              </div>
              
              {currentQuestion.topic_progress.proficiency.can_unlock_subtopics ? (
                <div className="text-sm text-green-600 dark:text-green-400">
                  ✨ You've reached Competent level! New subtopics are unlocked automatically as you learn.
                </div>
              ) : (
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  🎯 Reach Competent mastery level to unlock specialized subtopics in this area.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Learning State Card */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg shadow-lg p-8 mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Ready to Learn?</h1>
            <p className="text-blue-100 text-lg mb-4">{dashboard?.learning_state?.focus_area || "Starting your AI learning journey"}</p>
            <div className="flex items-center space-x-6 text-sm">
              <div>
                <span className="text-blue-200">Recent Accuracy:</span>
                <span className="font-semibold ml-1">{formatPercentage(dashboard?.learning_state?.recent_accuracy || 0)}%</span>
              </div>
              <div>
                <span className="text-blue-200">Sessions:</span>
                <span className="font-semibold ml-1">{dashboard?.learning_state?.sessions_completed || 0}</span>
              </div>
              <div>
                <span className="text-blue-200">Readiness:</span>
                <span className="font-semibold ml-1">{formatPercentage(dashboard?.learning_state?.readiness_score || 0)}%</span>
              </div>
            </div>
          </div>
          <button
            onClick={startLearning}
            disabled={isLoading}
            className="bg-white text-blue-600 px-8 py-4 rounded-lg font-semibold text-lg hover:bg-blue-50 transition-colors disabled:opacity-50 shadow-lg"
          >
            {isLoading ? '🔄 Starting...' : '🚀 Continue Learning'}
          </button>
        </div>
      </div>

      {/* Topic Creation Feedback */}
      {showTopicCreationFeedback && topicCreationResult && (
        <div className={`${
          topicCreationResult.action === 'semantic_match_unlocked' 
            ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800' 
            : 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
        } rounded-lg p-6 mb-6 relative`}>
          <button
            onClick={() => setShowTopicCreationFeedback(false)}
            className={`absolute top-2 right-2 ${
              topicCreationResult.action === 'semantic_match_unlocked'
                ? 'text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200'
                : 'text-green-600 hover:text-green-800 dark:text-green-400 dark:hover:text-green-200'
            }`}
          >
            ✕
          </button>
          <div className="flex items-center justify-between pr-8">
            <div>
              <h3 className={`text-lg font-semibold mb-2 ${
                topicCreationResult.action === 'semantic_match_unlocked'
                  ? 'text-blue-800 dark:text-blue-200'
                  : 'text-green-800 dark:text-green-200'
              }`}>
                {topicCreationResult.action === 'semantic_match_unlocked' ? '🎯' : '🎉'} {topicCreationResult.message}
              </h3>
              {topicCreationResult.parent_name && (
                <p className={`text-sm mt-1 ${
                  topicCreationResult.action === 'semantic_match_unlocked'
                    ? 'text-blue-700 dark:text-blue-300'
                    : 'text-green-700 dark:text-green-300'
                }`}>
                  {topicCreationResult.action === 'semantic_match_unlocked' ? 'Found in:' : 'Added under:'} {topicCreationResult.parent_name}
                </p>
              )}
              {topicCreationResult.reasoning && (
                <p className={`text-sm mt-2 ${
                  topicCreationResult.action === 'semantic_match_unlocked'
                    ? 'text-blue-600 dark:text-blue-400'
                    : 'text-green-600 dark:text-green-400'
                }`}>
                  {topicCreationResult.reasoning}
                </p>
              )}
            </div>
            <button
              onClick={navigateToNewTopic}
              disabled={isLoading}
              className={`px-8 py-3 text-white rounded-lg transition-colors disabled:opacity-50 font-semibold text-lg shadow-lg ${
                topicCreationResult.action === 'semantic_match_unlocked'
                  ? 'bg-blue-600 hover:bg-blue-700'
                  : 'bg-green-600 hover:bg-green-700'
              }`}
            >
              {isLoading ? '🔄 Starting...' : '🚀 Start Learning Now'}
            </button>
          </div>
        </div>
      )}

      {/* Learning Request Input */}
      <LearningRequestInput 
        onTopicCreated={handleTopicCreated}
        onLoading={handleTopicCreationLoading}
      />

      {/* Exploration Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            🗺️ Exploration
          </h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Topics Unlocked:</span>
              <span className="font-semibold">{dashboard?.exploration?.topics_unlocked || 1}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Coverage:</span>
              <span className="font-semibold">{formatPercentage(dashboard?.exploration?.exploration_coverage || 0)}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Recent Discoveries:</span>
              <span className="font-semibold">{dashboard?.exploration?.recent_discoveries || 0}</span>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            🎯 Interests
          </h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">High Interest:</span>
              <span className="font-semibold">{dashboard?.interests?.high_interest_topics?.length || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Growing:</span>
              <span className="font-semibold">{dashboard?.interests?.growing_interest_topics?.length || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Explored:</span>
              <span className="font-semibold">{dashboard?.interests?.total_topics_explored || 0}</span>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            🎲 Discovery
          </h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Strategy:</span>
              <span className="font-semibold">Adaptive</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Discovery Rate:</span>
              <span className="font-semibold">{(dashboard?.exploration?.discovery_rate || 0).toFixed(2)}/day</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">System:</span>
              <span className="font-semibold text-green-600">Infinite</span>
            </div>
          </div>
        </div>
      </div>

      {/* How It Works */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          ✨ How Adaptive Learning Works
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600 dark:text-gray-400">
          <div>
            <h4 className="font-medium text-gray-900 dark:text-white mb-2">🧠 Intelligent Selection</h4>
            <p>AI chooses the perfect questions across all topics using exploration/exploitation strategy.</p>
          </div>
          <div>
            <h4 className="font-medium text-gray-900 dark:text-white mb-2">🌱 Dynamic Growth</h4>
            <p>New topics emerge automatically when you show proficiency and interest.</p>
          </div>
          <div>
            <h4 className="font-medium text-gray-900 dark:text-white mb-2">🎯 Interest Tracking</h4>
            <p>System learns your preferences from 'Teach Me', 'Skip', and answer patterns.</p>
          </div>
          <div>
            <h4 className="font-medium text-gray-900 dark:text-white mb-2">♾️ Infinite Discovery</h4>
            <p>The knowledge tree expands infinitely based on your unique learning journey.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
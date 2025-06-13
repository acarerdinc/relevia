const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface Topic {
  id: number;
  name: string;
  description: string;
  parent_id?: number;
  difficulty_min: number;
  difficulty_max: number;
  children?: Topic[];
}

interface QuizSession {
  session_id: number;
  topic_id: number;
  message: string;
}

interface Question {
  question_id: number;
  quiz_question_id: number;
  question: string;
  options: string[];
  difficulty: number;
  topic: string;
}

interface AnswerResponse {
  correct: boolean;
  correct_answer: string;
  explanation: string;
  session_progress: {
    total_questions: number;
    correct_answers: number;
    accuracy: number;
  };
}

class ApiService {
  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async getTopics(): Promise<{ topics: Topic[] }> {
    return this.request('/topics/flat');
  }

  async getTopicHierarchy(): Promise<{ topics: Topic[] }> {
    return this.request('/topics/');
  }

  async startQuiz(topicId: number, userId: number = 1): Promise<QuizSession> {
    return this.request('/quiz/start', {
      method: 'POST',
      body: JSON.stringify({
        topic_id: topicId,
        user_id: userId,
      }),
    });
  }

  async getQuestion(sessionId: number): Promise<Question> {
    return this.request(`/quiz/question/${sessionId}`);
  }

  async submitAnswer(
    quizQuestionId: number,
    answer: string,
    timeSpent: number = 0,
    action: string = 'answer'
  ): Promise<AnswerResponse> {
    return this.request('/quiz/answer', {
      method: 'POST',
      body: JSON.stringify({
        quiz_question_id: quizQuestionId,
        answer,
        time_spent: timeSpent,
        action,
      }),
    });
  }

  async getSessionInfo(sessionId: number) {
    return this.request(`/quiz/session/${sessionId}`);
  }

  async checkHealth(): Promise<{ status: string; service: string }> {
    return this.request('/health');
  }

  // Personalization endpoints
  async getPersonalizedOntology(userId: number): Promise<{ topics: Topic[] }> {
    return this.request(`/personalization/ontology/${userId}`);
  }

  async getTopicRecommendations(userId: number, limit: number = 5): Promise<{ recommendations: any[] }> {
    return this.request(`/personalization/recommendations/${userId}?limit=${limit}`);
  }

  async getUserInterests(userId: number): Promise<{ interests: any[] }> {
    return this.request(`/personalization/interests/${userId}`);
  }

  async getUserProgress(userId: number): Promise<{ progress: any[] }> {
    return this.request(`/personalization/progress/${userId}`);
  }

  async getRecentUnlocks(userId: number, limit: number = 10): Promise<{ recent_unlocks: any[] }> {
    return this.request(`/personalization/unlocks/${userId}?limit=${limit}`);
  }
  
  // Progress endpoints
  async getUserProgressData(userId: number): Promise<any> {
    return this.request(`/progress/user/${userId}`);
  }
  
  async getTopicProgressDetails(topicId: number, userId: number = 1): Promise<any> {
    return this.request(`/progress/topic/${topicId}/details?user_id=${userId}`);
  }
  
  // Learning request endpoints
  async requestLearningTopic(requestText: string, userId: number = 1): Promise<any> {
    return this.request('/topics/request-learning', {
      method: 'POST',
      body: JSON.stringify({
        request_text: requestText,
        user_id: userId,
      }),
    });
  }
  
  async navigateToTopic(topicId: number, userId: number = 1): Promise<any> {
    return this.request('/topics/navigate-to-topic', {
      method: 'POST',
      body: JSON.stringify({
        topic_id: topicId,
        user_id: userId,
      }),
    });
  }
  
  async getLearningSuggestions(userId: number = 1, limit: number = 5): Promise<any> {
    return this.request(`/topics/suggestions?user_id=${userId}&limit=${limit}`);
  }

  async increaseTopicInterest(topicId: number, userId: number = 1): Promise<any> {
    return this.request('/topics/increase-interest', {
      method: 'POST',
      body: JSON.stringify({
        topic_id: topicId,
        user_id: userId,
        action: 'start_learning'
      }),
    });
  }
}

export const apiService = new ApiService();
export type { Topic, QuizSession, Question, AnswerResponse };
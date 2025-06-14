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
  topic_name?: string;
  debug_correct_index?: number; // Debug mode: index of correct answer for highlighting
  [key: string]: any; // Allow additional properties
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
  private token: string | null = null;

  constructor() {
    // Load token from localStorage on initialization
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('auth_token');
    }
  }

  setToken(token: string | null) {
    this.token = token;
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('auth_token', token);
      } else {
        localStorage.removeItem('auth_token');
      }
    }
  }

  async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Add auth token if available
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers: {
        ...headers,
        ...options?.headers,
      },
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

  // Authentication endpoints
  async register(email: string, username: string, password: string): Promise<any> {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        email,
        username,
        password,
      }),
    });
  }

  async login(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
    const formData = new URLSearchParams();
    formData.append('username', email); // OAuth2 expects 'username' field
    formData.append('password', password);

    const response = await this.request<{ access_token: string; token_type: string }>('/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString(),
    });

    // Store the token
    this.setToken(response.access_token);
    
    return response;
  }

  async logout() {
    this.setToken(null);
  }

  async getMe(): Promise<any> {
    return this.request('/auth/me');
  }
}

export const apiService = new ApiService();
export type { Topic, QuizSession, Question, AnswerResponse };
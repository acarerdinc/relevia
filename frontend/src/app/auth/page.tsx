'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { LoginForm } from '../../components/Auth';
import { useAuth } from '../../contexts/AuthContext';

export default function AuthPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    if (isAuthenticated) {
      router.push('/');
    }
  }, [isAuthenticated, router]);

  const handleSuccess = () => {
    router.push('/');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <div className="mb-6 text-center">
          <h1 className="text-3xl font-bold text-gray-900">🧠 Relevia</h1>
          <p className="text-gray-600 mt-2">Adaptive AI Learning Platform</p>
        </div>
        <LoginForm onSuccess={handleSuccess} />
        <p className="mt-6 text-center text-sm text-gray-600">
          Contact administrator for access
        </p>
      </div>
    </div>
  );
}
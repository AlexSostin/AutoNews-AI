'use client';

import { useState } from 'react';
import Image from 'next/image';
import { Eye, EyeOff } from 'lucide-react';
import '../register/register-password.css';
import { useRouter } from 'next/navigation';
import { login } from '@/lib/auth';
import { LogIn } from 'lucide-react';
import Link from 'next/link';
import toast from 'react-hot-toast';
import GoogleLoginButton from '@/components/auth/GoogleLoginButton';

export default function LoginPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({ username: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Check for registration success message
  useState(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      if (params.get('registered') === 'true') {
        setSuccess('Account created successfully! Please login.');
      }
    }
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setIsLoading(true);

    try {
      await login(formData);

      // Проверяем роль пользователя
      const userData = localStorage.getItem('user');
      if (userData) {
        const user = JSON.parse(userData);

        // Показываем красивое уведомление
        toast.success(
          `Welcome back, ${user.username}! 🎉`,
          {
            duration: 3000,
            position: 'top-center',
            style: {
              background: '#10B981',
              color: '#fff',
              fontWeight: 'bold',
              fontSize: '16px',
              padding: '16px 24px',
              borderRadius: '12px',
            },
            icon: '✨',
          }
        );

        // Небольшая задержка для показа уведомления, затем редирект
        setTimeout(() => {
          window.location.href = '/';
        }, 500);
      } else {
        // Если нет данных - на главную по умолчанию
        toast.success('Login successful!');
        setTimeout(() => {
          window.location.href = '/';
        }, 500);
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Invalid credentials';
      setError(errorMessage);
      toast.error(errorMessage, {
        duration: 4000,
        position: 'top-center',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500 flex items-center justify-center px-4">
      <div className="max-w-md w-full">

        <div className="bg-white rounded-2xl shadow-2xl p-8">
          {/* Logo inside card */}
          <div className="text-center mb-6 pb-6 border-b border-gray-100">
            <Link href="/" className="inline-block hover:scale-105 transition-transform duration-300">
              <Image
                src="/logo.png"
                alt="Fresh Motors"
                width={400}
                height={100}
                className="h-20 w-auto object-contain mx-auto scale-x-[1.8]"
                priority
              />
            </Link>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {success && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
                {success}
              </div>
            )}

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
                Username
              </label>
              <input
                id="username"
                type="text"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition text-gray-900 bg-white"
                required
              />
            </div>

            <div className="relative">
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition text-gray-900 bg-white pr-12"
                required
                autoComplete="current-password"
              />
              <button
                type="button"
                tabIndex={-1}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                onClick={() => setShowPassword((v) => !v)}
                className="absolute top-[2.75rem] right-3 flex items-center text-gray-400 hover:text-indigo-600 focus:outline-none"
                style={{ background: 'none', border: 'none', padding: 0 }}
              >
                {showPassword ? <EyeOff size={22} /> : <Eye size={22} />}
              </button>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-3 rounded-lg font-semibold hover:from-indigo-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
            >
              {isLoading ? 'Logging in...' : 'Login'}
            </button>
          </form>

          {/* Google OAuth - only show if client ID is configured */}
          {process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID && (
            <>
              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-300"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white text-gray-500">Or continue with</span>
                </div>
              </div>

              <div className="mb-6">
                <GoogleLoginButton
                  onSuccess={() => {
                    const userData = localStorage.getItem('user');
                    if (userData) {
                      const user = JSON.parse(userData);
                      toast.success(`Welcome back, ${user.username}! 🎉`, {
                        duration: 3000,
                        icon: '✨',
                      });
                    }
                    setTimeout(() => {
                      window.location.href = '/';
                    }, 500);
                  }}
                  onError={(error) => {
                    toast.error(error);
                  }}
                />
              </div>
            </>
          )}

          <div className="mt-6 text-center space-y-2">
            <p className="text-gray-600 text-sm">
              Don't have an account?{' '}
              <Link href="/register" className="text-indigo-600 hover:underline font-medium">
                Register here
              </Link>
            </p>
            <Link href="/" className="block text-indigo-600 hover:underline font-medium">
              ← Back to Home
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

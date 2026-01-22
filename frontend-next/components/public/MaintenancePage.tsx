'use client';

import { useState, useEffect } from 'react';
import { Wrench, LogIn } from 'lucide-react';
import Link from 'next/link';

interface MaintenancePageProps {
  message?: string;
}

export default function MaintenancePage({ message }: MaintenancePageProps) {
  const [dots, setDots] = useState('');
  
  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => prev.length >= 3 ? '' : prev + '.');
    }, 500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-indigo-800 flex items-center justify-center p-4">
      <div className="max-w-lg w-full text-center">
        {/* Animated Icon */}
        <div className="mb-8 relative">
          <div className="w-32 h-32 mx-auto bg-white/10 rounded-full flex items-center justify-center backdrop-blur-sm border border-white/20">
            <Wrench className="w-16 h-16 text-yellow-400 animate-bounce" />
          </div>
          {/* Spinning ring */}
          <div className="absolute inset-0 w-32 h-32 mx-auto border-4 border-transparent border-t-yellow-400 rounded-full animate-spin" />
        </div>

        {/* Title */}
        <h1 className="text-4xl md:text-5xl font-black text-white mb-4">
          🚧 На ремонте{dots}
        </h1>

        {/* Message */}
        <p className="text-xl text-white/80 mb-8 leading-relaxed">
          {message || 'Мы работаем над улучшением сайта. Пожалуйста, загляните позже!'}
        </p>

        {/* Progress bar animation */}
        <div className="w-full bg-white/20 rounded-full h-2 mb-8 overflow-hidden">
          <div className="h-full bg-gradient-to-r from-yellow-400 to-orange-500 rounded-full animate-pulse w-3/4" />
        </div>

        {/* Admin Login Button */}
        <Link
          href="/login"
          className="inline-flex items-center gap-2 px-6 py-3 bg-white/10 hover:bg-white/20 text-white rounded-xl font-semibold transition-all duration-300 border border-white/30 hover:border-white/50"
        >
          <LogIn size={20} />
          Войти как администратор
        </Link>

        {/* Footer */}
        <p className="mt-12 text-white/50 text-sm">
          © 2026 Fresh Motors. Скоро вернёмся!
        </p>
      </div>
    </div>
  );
}

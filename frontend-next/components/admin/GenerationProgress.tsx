'use client';

import { useEffect, useState, useRef } from 'react';
import { Loader2, CheckCircle, XCircle, Sparkles } from 'lucide-react';

interface ProgressData {
  step: number;
  progress: number;
  message: string;
  article_id?: number;
  error?: string;
}

interface GenerationProgressProps {
  taskId: string;
  isGenerating: boolean;
  onComplete?: (success: boolean, articleId?: number) => void;
  onError?: (error: string) => void;
}

const STEPS = [
  { id: 1, name: 'Инициализация', icon: '🚀' },
  { id: 2, name: 'Получение субтитров', icon: '📝' },
  { id: 3, name: 'Анализ контента', icon: '🔍' },
  { id: 4, name: 'Категоризация', icon: '🏷️' },
  { id: 5, name: 'Генерация статьи', icon: '✍️' },
  { id: 6, name: 'Скриншоты', icon: '📸' },
  { id: 7, name: 'Описание', icon: '📝' },
  { id: 8, name: 'Сохранение', icon: '📤' },
  { id: 9, name: 'Готово!', icon: '✅' },
];

export default function GenerationProgress({ 
  taskId, 
  isGenerating,
  onComplete,
  onError 
}: GenerationProgressProps) {
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  const [message, setMessage] = useState('Подготовка к генерации...');
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!isGenerating || !taskId) return;

    // Determine WebSocket URL
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      ? 'localhost:8001'
      : 'heroic-healing-production-2365.up.railway.app';
    
    const wsUrl = `${wsProtocol}//${wsHost}/ws/generation/${taskId}/`;
    
    console.log('Connecting to WebSocket:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('Progress update:', data);
        
        setCurrentStep(data.step);
        setProgress(data.progress);
        setMessage(data.message);

        if (data.progress >= 100 && data.step === 9) {
          // Completed successfully - callback is handled by parent
          onComplete?.(true, data.article_id);
        }
        
        if (data.error) {
          setError(data.message || data.error);
          onComplete?.(false);
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onerror = (event) => {
      console.error('WebSocket error:', event);
      setError('Ошибка подключения к серверу');
      onError?.('WebSocket connection failed');
    };

    ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      setIsConnected(false);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [taskId, isGenerating, onComplete, onError]);

  if (!isGenerating) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-lg w-full mx-4 transform animate-in fade-in zoom-in duration-300">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="p-3 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">Генерация статьи</h3>
            <p className="text-sm text-gray-500">AI создаёт контент для вас</p>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex justify-between text-sm mb-2">
            <span className="font-medium text-gray-700">{message}</span>
            <span className="font-bold text-indigo-600">{progress}%</span>
          </div>
          <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Steps */}
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {STEPS.map((step) => {
            const isActive = currentStep === step.id;
            const isCompleted = currentStep > step.id;

            return (
              <div 
                key={step.id}
                className={`flex items-center gap-3 p-3 rounded-lg transition-all ${
                  isActive 
                    ? 'bg-indigo-50 border border-indigo-200' 
                    : isCompleted 
                    ? 'bg-green-50' 
                    : 'bg-gray-50'
                }`}
              >
                <span className="text-xl">{step.icon}</span>
                <span className={`flex-1 font-medium ${
                  isActive ? 'text-indigo-700' : isCompleted ? 'text-green-700' : 'text-gray-400'
                }`}>
                  {step.name}
                </span>
                {isActive && (
                  <Loader2 className="w-5 h-5 text-indigo-600 animate-spin" />
                )}
                {isCompleted && (
                  <CheckCircle className="w-5 h-5 text-green-600" />
                )}
              </div>
            );
          })}
        </div>

        {/* Error State */}
        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
            <XCircle className="w-5 h-5 text-red-600" />
            <span className="text-red-700">{error}</span>
          </div>
        )}

        {/* Connection Status */}
        <div className="mt-4 flex items-center justify-center gap-2 text-xs text-gray-400">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-yellow-500'}`} />
          {isConnected ? 'Подключено' : 'Подключение...'}
        </div>
      </div>
    </div>
  );
}

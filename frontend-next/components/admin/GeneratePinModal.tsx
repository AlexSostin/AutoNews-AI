'use client';

import { useState, useEffect, useRef } from 'react';
import { Lock, KeyRound, Eye, EyeOff, ShieldCheck, AlertCircle, X, Settings } from 'lucide-react';

const PIN_STORAGE_KEY = 'freshmotor_gen_pin';

interface GeneratePinModalProps {
    /** Title shown in the modal header */
    title?: string;
    /** Short description of what will be generated */
    description?: string;
    /** Called when PIN is confirmed */
    onConfirm: () => void;
    /** Called when user cancels */
    onCancel: () => void;
}

export default function GeneratePinModal({
    title = 'Confirm Generation',
    description = 'Enter your PIN to generate this article.',
    onConfirm,
    onCancel,
}: GeneratePinModalProps) {
    const [storedPin, setStoredPin] = useState<string | null>(null);
    const [mode, setMode] = useState<'enter' | 'setup'>('enter');
    const [pin, setPin] = useState('');
    const [confirmPin, setConfirmPin] = useState('');
    const [showPin, setShowPin] = useState(false);
    const [error, setError] = useState('');
    const [shake, setShake] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        const saved = localStorage.getItem(PIN_STORAGE_KEY);
        if (!saved) {
            setMode('setup');
        } else {
            setStoredPin(saved);
            setMode('enter');
        }
        // Auto-focus input
        setTimeout(() => inputRef.current?.focus(), 100);
    }, []);

    const triggerShake = () => {
        setShake(true);
        setTimeout(() => setShake(false), 500);
    };

    const handleEnterPin = () => {
        if (pin === storedPin) {
            onConfirm();
        } else {
            setError('Incorrect PIN. Try again.');
            setPin('');
            triggerShake();
        }
    };

    const handleSetupPin = () => {
        if (pin.length < 4) {
            setError('PIN must be at least 4 characters.');
            return;
        }
        if (pin !== confirmPin) {
            setError('PINs do not match.');
            setConfirmPin('');
            return;
        }
        localStorage.setItem(PIN_STORAGE_KEY, pin);
        setStoredPin(pin);
        setMode('enter');
        setPin('');
        setConfirmPin('');
        setError('');
    };

    const handleResetPin = () => {
        if (confirm('Reset PIN? You will need to set a new one.')) {
            localStorage.removeItem(PIN_STORAGE_KEY);
            setMode('setup');
            setPin('');
            setConfirmPin('');
            setError('');
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            mode === 'enter' ? handleEnterPin() : handleSetupPin();
        }
        if (e.key === 'Escape') {
            onCancel();
        }
    };

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div
                className={`bg-white rounded-2xl shadow-2xl w-full max-w-sm transition-transform ${shake ? 'animate-[shake_0.4s_ease-in-out]' : ''}`}
                style={shake ? { animation: 'shake 0.4s ease-in-out' } : {}}
            >
                {/* Header */}
                <div className="p-6 border-b border-gray-100 flex items-start justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2.5 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 text-white shadow-lg">
                            <Lock size={20} />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-gray-900">{mode === 'setup' ? 'Set Generation PIN' : title}</h2>
                            <p className="text-xs text-gray-500 mt-0.5">
                                {mode === 'setup' ? 'Create a PIN to protect generation' : description}
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onCancel}
                        className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-600 transition-colors"
                    >
                        <X size={18} />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 space-y-4">
                    {mode === 'setup' && (
                        <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-xl">
                            <ShieldCheck size={16} className="text-amber-600 mt-0.5 flex-shrink-0" />
                            <p className="text-xs text-amber-700">
                                No PIN is set yet. Set a PIN now — it will be required every time you generate an article.
                            </p>
                        </div>
                    )}

                    {/* PIN input */}
                    <div className="relative">
                        <label className="block text-sm font-medium text-gray-700 mb-1.5">
                            {mode === 'setup' ? 'New PIN' : 'Enter PIN'}
                        </label>
                        <div className="relative">
                            <KeyRound size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                            <input
                                ref={inputRef}
                                type={showPin ? 'text' : 'password'}
                                value={pin}
                                onChange={(e) => { setPin(e.target.value); setError(''); }}
                                onKeyDown={handleKeyDown}
                                className="w-full pl-9 pr-10 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent text-gray-900 text-lg tracking-widest font-mono"
                                placeholder="••••"
                                autoComplete="off"
                            />
                            <button
                                type="button"
                                onClick={() => setShowPin(!showPin)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                            >
                                {showPin ? <EyeOff size={16} /> : <Eye size={16} />}
                            </button>
                        </div>
                    </div>

                    {/* Confirm PIN (setup mode only) */}
                    {mode === 'setup' && (
                        <div className="relative">
                            <label className="block text-sm font-medium text-gray-700 mb-1.5">Confirm PIN</label>
                            <div className="relative">
                                <KeyRound size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                                <input
                                    type={showPin ? 'text' : 'password'}
                                    value={confirmPin}
                                    onChange={(e) => { setConfirmPin(e.target.value); setError(''); }}
                                    onKeyDown={handleKeyDown}
                                    className="w-full pl-9 pr-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent text-gray-900 text-lg tracking-widest font-mono"
                                    placeholder="••••"
                                    autoComplete="off"
                                />
                            </div>
                        </div>
                    )}

                    {/* Error */}
                    {error && (
                        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-xl">
                            <AlertCircle size={14} className="text-red-500 flex-shrink-0" />
                            <p className="text-xs text-red-600 font-medium">{error}</p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-6 pt-0 space-y-3">
                    <div className="flex gap-2">
                        <button
                            onClick={onCancel}
                            className="flex-1 px-4 py-2.5 border border-gray-200 text-gray-600 rounded-xl hover:bg-gray-50 transition-colors text-sm font-medium"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={mode === 'enter' ? handleEnterPin : handleSetupPin}
                            className="flex-1 px-4 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl transition-all text-sm font-bold shadow-md"
                        >
                            {mode === 'setup' ? 'Set PIN & Generate' : 'Confirm'}
                        </button>
                    </div>

                    {mode === 'enter' && (
                        <button
                            onClick={handleResetPin}
                            className="w-full flex items-center justify-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors py-1"
                        >
                            <Settings size={12} />
                            Reset PIN
                        </button>
                    )}
                </div>
            </div>

            {/* Shake animation */}
            <style jsx>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          20% { transform: translateX(-8px); }
          40% { transform: translateX(8px); }
          60% { transform: translateX(-6px); }
          80% { transform: translateX(6px); }
        }
      `}</style>
        </div>
    );
}

'use client';

import { useEffect, useState } from 'react';
import { ShieldAlert, Clock, LogOut, RefreshCw } from 'lucide-react';

interface Props {
    visible: boolean;
    onStay: () => void;
    onLogout: () => void;
    /** Seconds until auto-logout (counts down) */
    countdownSeconds?: number;
}

export function IdleWarningModal({ visible, onStay, onLogout, countdownSeconds = 120 }: Props) {
    const [seconds, setSeconds] = useState(countdownSeconds);

    useEffect(() => {
        if (!visible) {
            setSeconds(countdownSeconds);
            return;
        }

        setSeconds(countdownSeconds);
        const interval = setInterval(() => {
            setSeconds(prev => {
                if (prev <= 1) {
                    clearInterval(interval);
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);

        return () => clearInterval(interval);
    }, [visible, countdownSeconds]);

    if (!visible) return null;

    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    const urgency = seconds < 30;

    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

            {/* Modal */}
            <div className="relative bg-white rounded-2xl shadow-2xl border border-gray-200 p-8 max-w-md w-full mx-4 animate-in fade-in zoom-in-95 duration-200">
                {/* Icon */}
                <div className={`w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-5 ${urgency ? 'bg-red-100' : 'bg-amber-100'}`}>
                    <ShieldAlert className={`w-8 h-8 ${urgency ? 'text-red-500 animate-pulse' : 'text-amber-500'}`} />
                </div>

                {/* Title */}
                <h2 className="text-xl font-black text-gray-900 text-center mb-2">
                    Session Timeout
                </h2>
                <p className="text-sm text-gray-500 text-center mb-6">
                    You&apos;ve been inactive. For security, your admin session will end automatically.
                </p>

                {/* Countdown */}
                <div className={`flex items-center justify-center gap-2 px-4 py-3 rounded-xl mb-6 border-2 ${urgency
                        ? 'bg-red-50 border-red-200 text-red-700'
                        : 'bg-amber-50 border-amber-200 text-amber-700'
                    }`}>
                    <Clock className="w-5 h-5 shrink-0" />
                    <span className="text-sm font-semibold">Logging out in</span>
                    <span className={`text-2xl font-black tabular-nums ${urgency ? 'text-red-600' : 'text-amber-600'}`}>
                        {mins > 0 ? `${mins}:${String(secs).padStart(2, '0')}` : `${secs}s`}
                    </span>
                </div>

                {/* Actions */}
                <div className="flex gap-3">
                    <button
                        onClick={onLogout}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl border border-gray-200 text-gray-600 text-sm font-semibold hover:bg-gray-50 transition-colors"
                    >
                        <LogOut className="w-4 h-4" />
                        Logout now
                    </button>
                    <button
                        onClick={onStay}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-indigo-600 text-white text-sm font-bold hover:bg-indigo-700 transition-colors shadow-lg shadow-indigo-200"
                    >
                        <RefreshCw className="w-4 h-4" />
                        Stay logged in
                    </button>
                </div>
            </div>
        </div>
    );
}

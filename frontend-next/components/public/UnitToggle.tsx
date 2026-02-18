'use client';

import { useLocaleUnits, UnitSystem } from '@/hooks/useLocaleUnits';

interface UnitToggleProps {
    className?: string;
}

export default function UnitToggle({ className = '' }: UnitToggleProps) {
    const { system, setSystem, ready } = useLocaleUnits();

    if (!ready) return null;

    return (
        <div className={`inline-flex items-center gap-1 bg-gray-100 rounded-lg p-0.5 ${className}`}>
            <button
                onClick={() => setSystem('metric')}
                className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all ${system === 'metric'
                        ? 'bg-white text-indigo-700 shadow-sm'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
            >
                km
            </button>
            <button
                onClick={() => setSystem('imperial')}
                className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all ${system === 'imperial'
                        ? 'bg-white text-indigo-700 shadow-sm'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
            >
                mi
            </button>
        </div>
    );
}

'use client';

import { UnitSystem } from '@/hooks/useLocaleUnits';

interface UnitToggleProps {
    system: UnitSystem;
    onToggle: (system: UnitSystem) => void;
    className?: string;
}

export default function UnitToggle({ system, onToggle, className = '' }: UnitToggleProps) {
    return (
        <div className={`inline-flex items-center gap-1 rounded-lg p-0.5 ${className}`}>
            <button
                onClick={() => onToggle('metric')}
                className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all ${system === 'metric'
                        ? 'bg-white text-indigo-700 shadow-sm'
                        : 'text-gray-300 hover:text-white'
                    }`}
            >
                Metric
            </button>
            <button
                onClick={() => onToggle('imperial')}
                className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all ${system === 'imperial'
                        ? 'bg-white text-indigo-700 shadow-sm'
                        : 'text-gray-300 hover:text-white'
                    }`}
            >
                Imperial
            </button>
        </div>
    );
}

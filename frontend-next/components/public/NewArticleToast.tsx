'use client';

/**
 * NewArticleToast — bottom toast notifying user that a new article is ready.
 * Appears when the user is already in the footer but a new article has been loaded.
 * Clicking "Show" scrolls to the new article.
 */

import { useEffect, useState } from 'react';
import { ChevronDown, X } from 'lucide-react';

interface NewArticleToastProps {
    title: string;
    onShow: () => void;
    onDismiss: () => void;
}

export default function NewArticleToast({ title, onShow, onDismiss }: NewArticleToastProps) {
    const [visible, setVisible] = useState(false);

    // Slide in after mount
    useEffect(() => {
        const t = setTimeout(() => setVisible(true), 50);
        return () => clearTimeout(t);
    }, []);

    const handleShow = () => {
        setVisible(false);
        setTimeout(onShow, 250);
    };

    const handleDismiss = () => {
        setVisible(false);
        setTimeout(onDismiss, 250);
    };

    return (
        <div
            role="status"
            aria-live="polite"
            className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 
                bg-white border border-indigo-100 shadow-xl rounded-2xl px-4 py-3 max-w-xs sm:max-w-sm w-full
                transition-all duration-300 ease-out
                ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}
        >
            {/* Icon */}
            <div className="shrink-0 bg-indigo-50 rounded-xl p-2">
                <ChevronDown size={18} className="text-indigo-600" />
            </div>

            {/* Text */}
            <div className="flex-1 min-w-0">
                <p className="text-xs text-gray-400 font-medium">New article loaded</p>
                <p className="text-sm font-bold text-gray-900 truncate">{title}</p>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1 shrink-0">
                <button
                    onClick={handleShow}
                    className="text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 px-3 py-1.5 rounded-xl transition"
                >
                    Show
                </button>
                <button
                    onClick={handleDismiss}
                    aria-label="Dismiss"
                    className="p-1.5 rounded-xl hover:bg-gray-100 transition text-gray-400"
                >
                    <X size={14} />
                </button>
            </div>
        </div>
    );
}

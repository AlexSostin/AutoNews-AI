'use client';

/**
 * SmartScrollButton — floating scroll-up button with two behaviors:
 * - Single click → scrolls to the top of the current active article
 * - Double click → scrolls to the very top of the page
 *
 * Shows only when scrolled past 400px. Hides within 100px of page top.
 */

import { useEffect, useRef, useState } from 'react';
import { ChevronUp, ChevronsUp } from 'lucide-react';

interface SmartScrollButtonProps {
    /** Slug of the currently active article (tracked by InfiniteArticleScroll) */
    activeSlug: string;
}

export default function SmartScrollButton({ activeSlug }: SmartScrollButtonProps) {
    const [visible, setVisible] = useState(false);
    const [hint, setHint] = useState<'article' | 'top' | null>(null);
    const clickTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const clickCountRef = useRef(0);

    // Show/hide on scroll
    useEffect(() => {
        const onScroll = () => setVisible(window.scrollY > 400);
        window.addEventListener('scroll', onScroll, { passive: true });
        return () => window.removeEventListener('scroll', onScroll);
    }, []);

    const scrollToArticle = () => {
        // Find which article the user is currently "inside" based on viewport position
        const articles = document.querySelectorAll<HTMLElement>('[data-article-slug]');
        const viewportPoint = window.scrollY + window.innerHeight / 3;
        let target: HTMLElement | null = null;
        for (const el of articles) {
            const top = el.offsetTop;
            const bottom = top + el.offsetHeight;
            if (top <= viewportPoint && bottom > viewportPoint) {
                target = el;
                break;
            }
        }
        // Fallback: use activeSlug element or first article
        if (!target) {
            target = document.querySelector<HTMLElement>(`[data-article-slug="${activeSlug}"]`);
        }
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    };

    const scrollToTop = () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const showHint = (type: 'article' | 'top') => {
        setHint(type);
        setTimeout(() => setHint(null), 1200);
    };

    const handleClick = () => {
        clickCountRef.current += 1;

        if (clickCountRef.current === 1) {
            // Wait for possible second click
            clickTimerRef.current = setTimeout(() => {
                clickCountRef.current = 0;
                // Single click → jump to current article
                scrollToArticle();
                showHint('article');
            }, 280);
        } else {
            // Double click → jump to page top
            if (clickTimerRef.current) clearTimeout(clickTimerRef.current);
            clickCountRef.current = 0;
            scrollToTop();
            showHint('top');
        }
    };

    return (
        <div
            className={`fixed bottom-6 right-4 sm:right-6 z-40 flex flex-col items-end gap-2 transition-all duration-300
                ${visible ? 'opacity-100 translate-y-0 pointer-events-auto' : 'opacity-0 translate-y-4 pointer-events-none'}`}
        >
            {/* Hint label */}
            {hint && (
                <span className={`text-xs font-semibold px-2.5 py-1 rounded-full shadow-md transition-all duration-200
                    ${hint === 'top' ? 'bg-indigo-600 text-white' : 'bg-white text-indigo-700 border border-indigo-200'}`}>
                    {hint === 'top' ? '↑ Page top' : '↑ Article top'}
                </span>
            )}

            {/* Button */}
            <button
                onClick={handleClick}
                aria-label="Scroll to top of current article (double-click for page top)"
                title="Click → article top · Double-click → page top"
                className="group flex items-center justify-center w-11 h-11 rounded-2xl
                    bg-white border border-gray-200 shadow-lg
                    hover:bg-indigo-600 hover:border-indigo-600 hover:shadow-indigo-200/60
                    active:scale-95 transition-all duration-200"
            >
                <ChevronUp
                    size={20}
                    className="text-gray-600 group-hover:text-white transition-colors"
                />
            </button>
        </div>
    );
}

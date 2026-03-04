'use client';

import { useState, useEffect, useRef } from 'react';
import { ArrowUp } from 'lucide-react';

/**
 * BackToTop — smart scroll button with two behaviors:
 *  - Single click → scroll to current article top (tracked via 'article-active-slug' custom event)
 *  - Double click → scroll to page top
 *
 * On non-article pages (no event received) both clicks go to page top.
 */
export default function BackToTop() {
  const [isVisible, setIsVisible] = useState(false);
  const [hint, setHint] = useState<string | null>(null);
  const activeSlugRef = useRef<string | null>(null);
  const clickTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const clickCountRef = useRef(0);

  // Show/hide on scroll
  useEffect(() => {
    const onScroll = () => setIsVisible(window.scrollY > 300);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Listen for active article changes dispatched by InfiniteArticleScroll
  useEffect(() => {
    const handler = (e: Event) => {
      activeSlugRef.current = (e as CustomEvent<string>).detail;
    };
    window.addEventListener('article-active-slug', handler);
    return () => window.removeEventListener('article-active-slug', handler);
  }, []);

  const showHint = (msg: string) => {
    setHint(msg);
    setTimeout(() => setHint(null), 1200);
  };

  const scrollToArticle = () => {
    const slug = activeSlugRef.current;
    if (slug) {
      const el = document.querySelector<HTMLElement>(`[data-article-slug="${slug}"]`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        showHint('↑ Article top');
        return;
      }
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
    showHint('↑ Top');
  };

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    showHint('↑ Page top');
  };

  const handleClick = () => {
    clickCountRef.current += 1;

    if (clickCountRef.current === 1) {
      clickTimerRef.current = setTimeout(() => {
        clickCountRef.current = 0;
        scrollToArticle(); // single click
      }, 280);
    } else {
      if (clickTimerRef.current) clearTimeout(clickTimerRef.current);
      clickCountRef.current = 0;
      scrollToTop(); // double click
    }
  };

  return (
    <>
      {isVisible && (
        <div className="fixed bottom-8 right-8 z-50 flex flex-col items-end gap-2">
          {/* Hint label */}
          {hint && (
            <span className="text-xs font-bold px-2.5 py-1 rounded-full shadow-md bg-white text-indigo-700 border border-indigo-200 animate-fade-in whitespace-nowrap">
              {hint}
            </span>
          )}

          <button
            onClick={handleClick}
            className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white p-4 rounded-full shadow-2xl transition-all duration-300 transform hover:scale-110 hover:rotate-12 group"
            aria-label="Back to top (double-click for page top)"
            title="Click → article top · Double-click → page top"
          >
            <ArrowUp size={24} className="group-hover:animate-bounce" />
          </button>
        </div>
      )}
    </>
  );
}

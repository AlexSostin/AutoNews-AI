'use client';

import { useState, useEffect, useRef } from 'react';
import { usePathname } from 'next/navigation';
import { ArrowUp, ArrowDown } from 'lucide-react';

/**
 * BackToTop — smart scroll buttons:
 *  - ↑ Single click → scroll to current article top
 *  - ↑ Double click → scroll to page top
 *  - ↓ Single click → scroll to footer
 *
 *  Hidden on: login, register, admin pages, and any full-screen form pages.
 */

// Paths where the scroll buttons should NOT appear
const HIDDEN_ON_PATHS = ['/login', '/register'];
const HIDDEN_ON_PREFIXES = ['/admin'];

export default function BackToTop() {
  const pathname = usePathname();
  const [isVisible, setIsVisible] = useState(false);
  const [hint, setHint] = useState<string | null>(null);
  const activeSlugRef = useRef<string | null>(null);
  const clickTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const clickCountRef = useRef(0);

  // Check if current route should hide the buttons
  const isHidden =
    HIDDEN_ON_PATHS.includes(pathname) ||
    HIDDEN_ON_PREFIXES.some(prefix => pathname.startsWith(prefix));

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

  const scrollToFooter = () => {
    const maxScroll = Math.max(
      document.body.scrollHeight,
      document.documentElement.scrollHeight
    );
    window.scrollTo({ top: maxScroll, behavior: 'smooth' });
    showHint('↓ Footer');
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
      {isVisible && !isHidden && (
        <div className="fixed bottom-8 right-8 z-50 flex flex-col items-center gap-2">
          {/* Hint label */}
          {hint && (
            <span className="text-xs font-bold px-2.5 py-1 rounded-full shadow-md bg-white text-indigo-700 border border-indigo-200 animate-fade-in whitespace-nowrap">
              {hint}
            </span>
          )}

          {/* Up button */}
          <button
            onClick={handleClick}
            className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white p-4 rounded-full shadow-2xl transition-all duration-300 transform hover:scale-110 hover:rotate-12 group"
            aria-label="Back to top (double-click for page top)"
            title="Click → article top · Double-click → page top"
          >
            <ArrowUp size={24} className="group-hover:animate-bounce" />
          </button>

          {/* Down button — scroll to footer */}
          <button
            onClick={scrollToFooter}
            className="bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white p-3 rounded-full shadow-lg transition-all duration-300 transform hover:scale-110 hover:-rotate-12 group opacity-80 hover:opacity-100"
            aria-label="Scroll to footer"
            title="Scroll to footer"
          >
            <ArrowDown size={18} className="group-hover:animate-bounce" />
          </button>
        </div>
      )}
    </>
  );
}

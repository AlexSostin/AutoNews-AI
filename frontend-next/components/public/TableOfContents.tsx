'use client';

import { useState } from 'react';
import { BookOpen, ChevronDown, ChevronUp } from 'lucide-react';

export interface TocHeading {
    id: string;
    text: string;
}

interface Props {
    headings: TocHeading[];
}

export default function TableOfContents({ headings }: Props) {
    const [open, setOpen] = useState(false);

    // Don't render for very short articles
    if (headings.length < 2) return null;

    const scrollTo = (id: string) => {
        const el = document.getElementById(id);
        if (!el) return;
        const y = el.getBoundingClientRect().top + window.scrollY - 16;
        window.scrollTo({ top: y, behavior: 'smooth' });
        setOpen(false);
    };

    const List = () => (
        <ol className="space-y-1.5 mt-3">
            {headings.map((h, i) => (
                <li key={h.id} className="flex items-start gap-2.5">
                    <span className="mt-0.5 min-w-[1.25rem] text-xs font-bold text-indigo-400">
                        {String(i + 1).padStart(2, '0')}
                    </span>
                    <button
                        onClick={() => scrollTo(h.id)}
                        className="text-left text-sm text-gray-700 hover:text-indigo-600 transition-colors leading-snug"
                    >
                        {h.text}
                    </button>
                </li>
            ))}
        </ol>
    );

    return (
        <div className="my-6 rounded-xl border border-indigo-100 bg-indigo-50/60 overflow-hidden">
            {/* ── Mobile: collapsible ── */}
            <div className="md:hidden">
                <button
                    onClick={() => setOpen(v => !v)}
                    className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold text-indigo-700"
                >
                    <span className="flex items-center gap-2">
                        <BookOpen size={15} />
                        In this article
                    </span>
                    {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>
                {open && (
                    <div className="px-4 pb-4 border-t border-indigo-100">
                        <List />
                    </div>
                )}
            </div>

            {/* ── Desktop: always visible ── */}
            <div className="hidden md:block p-5">
                <div className="flex items-center gap-2 text-sm font-semibold text-indigo-700">
                    <BookOpen size={15} />
                    In this article
                </div>
                <List />
            </div>
        </div>
    );
}

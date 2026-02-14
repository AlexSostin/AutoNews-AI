'use client';

import { useState, useMemo, useRef, useEffect } from 'react';
import Link from 'next/link';
import { fixImageUrl } from '@/lib/config';

interface ModelData {
    model: string;
    slug: string;
    trim_count: number;
    article_count: number;
    engine: string;
    horsepower: string;
    price: string;
    image: string | null;
}

type SortOption = 'name' | 'price-low' | 'price-high' | 'power' | 'articles';

const SORT_OPTIONS: { key: SortOption; label: string; icon: string }[] = [
    { key: 'name', label: 'Name (A–Z)', icon: '🔤' },
    { key: 'price-low', label: 'Price: Low to High', icon: '💰' },
    { key: 'price-high', label: 'Price: High to Low', icon: '💎' },
    { key: 'power', label: 'Most Powerful', icon: '⚡' },
    { key: 'articles', label: 'Most Reviewed', icon: '📰' },
];

function parseNumeric(val: string): number {
    const match = val.replace(/,/g, '').match(/[\d.]+/);
    return match ? parseFloat(match[0]) : 0;
}

function shortenPrice(price: string): string {
    if (!price) return '—';
    // If price has multiple values separated by commas or parens, show just the first
    const first = price.match(/^\$[\d,.]+\s*[kK]?/)?.[0];
    if (first && first.length < price.length) return `from ${first}`;
    return price;
}

export default function BrandModelsGrid({
    models,
    brand,
    brandSlug,
}: {
    models: ModelData[];
    brand: string;
    brandSlug: string;
}) {
    const [sortBy, setSortBy] = useState<SortOption>('name');
    const [dropdownOpen, setDropdownOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        function handleClick(e: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setDropdownOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, []);

    const currentSort = SORT_OPTIONS.find((o) => o.key === sortBy)!;

    const sortedModels = useMemo(() => {
        const sorted = [...models];
        switch (sortBy) {
            case 'name':
                sorted.sort((a, b) => a.model.localeCompare(b.model));
                break;
            case 'price-low':
                sorted.sort((a, b) => {
                    const pa = parseNumeric(a.price);
                    const pb = parseNumeric(b.price);
                    if (!pa && !pb) return 0;
                    if (!pa) return 1;
                    if (!pb) return -1;
                    return pa - pb;
                });
                break;
            case 'price-high':
                sorted.sort((a, b) => {
                    const pa = parseNumeric(a.price);
                    const pb = parseNumeric(b.price);
                    if (!pa && !pb) return 0;
                    if (!pa) return 1;
                    if (!pb) return -1;
                    return pb - pa;
                });
                break;
            case 'power':
                sorted.sort((a, b) => parseNumeric(b.horsepower) - parseNumeric(a.horsepower));
                break;
            case 'articles':
                sorted.sort((a, b) => b.article_count - a.article_count);
                break;
        }
        return sorted;
    }, [models, sortBy]);

    return (
        <section className="container mx-auto px-4 py-10">
            {/* Toolbar */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
                {/* Back button */}
                <Link
                    href="/cars"
                    className="inline-flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-indigo-600 transition-colors group"
                >
                    <svg className="w-4 h-4 transition-transform group-hover:-translate-x-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                    </svg>
                    All Brands
                </Link>

                {/* Sort dropdown */}
                <div className="relative" ref={dropdownRef}>
                    <button
                        onClick={() => setDropdownOpen(!dropdownOpen)}
                        className="inline-flex items-center gap-2.5 px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm font-medium text-gray-700 hover:border-indigo-300 hover:shadow-sm transition-all"
                    >
                        <span className="text-gray-400 text-xs uppercase tracking-wider">Sort</span>
                        <span className="w-px h-4 bg-gray-200" />
                        <span>{currentSort.icon}</span>
                        <span>{currentSort.label}</span>
                        <svg className={`w-4 h-4 text-gray-400 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                        </svg>
                    </button>

                    {dropdownOpen && (
                        <div className="absolute right-0 mt-2 w-56 bg-white border border-gray-200 rounded-xl shadow-lg shadow-gray-100 z-20 overflow-hidden">
                            {SORT_OPTIONS.map(({ key, label, icon }) => (
                                <button
                                    key={key}
                                    onClick={() => {
                                        setSortBy(key);
                                        setDropdownOpen(false);
                                    }}
                                    className={`w-full flex items-center gap-3 px-4 py-3 text-sm text-left transition-colors ${sortBy === key
                                        ? 'bg-indigo-50 text-indigo-700 font-semibold'
                                        : 'text-gray-600 hover:bg-gray-50'
                                        }`}
                                >
                                    <span className="text-base">{icon}</span>
                                    <span>{label}</span>
                                    {sortBy === key && (
                                        <svg className="w-4 h-4 ml-auto text-indigo-500" fill="currentColor" viewBox="0 0 20 20">
                                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                        </svg>
                                    )}
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Results count */}
            <p className="text-sm text-gray-400 mb-6">
                {sortedModels.length} {sortedModels.length === 1 ? 'model' : 'models'} found
            </p>

            {/* Models Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {sortedModels.map((model) => (
                    <Link
                        key={model.slug}
                        href={`/cars/${brandSlug}/${model.slug}`}
                        className="group flex flex-col h-full bg-white rounded-2xl border border-gray-100 overflow-hidden shadow-[0_2px_20px_rgba(0,0,0,0.06)] transition-all duration-300 hover:shadow-[0_20px_50px_rgba(79,70,229,0.15)] hover:-translate-y-1.5 hover:border-indigo-300"
                    >
                        {/* Image */}
                        <div className="aspect-video bg-gradient-to-br from-gray-100 to-gray-200 overflow-hidden relative">
                            {model.image ? (
                                <img
                                    src={fixImageUrl(model.image)}
                                    alt={`${brand} ${model.model}`}
                                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                                />
                            ) : (
                                <div className="w-full h-full flex items-center justify-center text-5xl text-gray-300">
                                    🚗
                                </div>
                            )}
                            <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-black/30 to-transparent" />
                            {model.article_count > 1 && (
                                <span className="absolute top-3 right-3 bg-white/90 backdrop-blur-sm text-xs font-bold text-indigo-600 px-2.5 py-1 rounded-full shadow-sm">
                                    {model.article_count} reviews
                                </span>
                            )}
                        </div>

                        {/* Info */}
                        <div className="p-6 flex-grow flex flex-col">
                            <h3 className="font-bold text-xl text-gray-900 group-hover:text-indigo-600 transition-colors mb-4">
                                {brand} {model.model}
                            </h3>

                            {/* Specs — stacked rows */}
                            <div className="space-y-0 mt-auto rounded-xl border border-gray-100 overflow-hidden">
                                {[
                                    { label: 'Engine', value: model.engine || '—' },
                                    { label: 'Power', value: model.horsepower ? `${model.horsepower} hp` : '—' },
                                    { label: 'Price', value: model.price || '—', highlight: true },
                                    { label: 'Articles', value: String(model.article_count) },
                                ].map((spec, i) => (
                                    <div
                                        key={spec.label}
                                        className={`flex items-center justify-between px-4 py-2.5 ${i % 2 === 0 ? 'bg-gray-50/80' : 'bg-white'
                                            }`}
                                    >
                                        <span className="text-xs text-gray-400 uppercase tracking-wider font-medium">
                                            {spec.label}
                                        </span>
                                        <span
                                            className={`text-sm font-semibold text-right max-w-[65%] ${spec.highlight ? 'text-indigo-700' : 'text-gray-800'
                                                }`}
                                            title={spec.value}
                                        >
                                            {spec.value}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Hover accent bar */}
                        <div className="h-1 bg-gradient-to-r from-indigo-600 to-purple-600 transform scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left" />
                    </Link>
                ))}
            </div>
        </section>
    );
}

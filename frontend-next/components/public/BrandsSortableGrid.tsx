'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { fixImageUrl } from '@/lib/config';

interface Brand {
    name: string;
    slug: string;
    model_count: number;
    article_count: number;
    image: string | null;
}

type SortKey = 'name' | 'articles' | 'models';
type SortDir = 'asc' | 'desc';

const SORT_OPTIONS: { key: SortKey; label: string; icon: string }[] = [
    { key: 'name', label: 'A–Z', icon: '🔤' },
    { key: 'articles', label: 'Articles', icon: '📰' },
    { key: 'models', label: 'Models', icon: '🚗' },
];

export default function BrandsSortableGrid({ brands }: { brands: Brand[] }) {
    const [sortKey, setSortKey] = useState<SortKey>('articles');
    const [sortDir, setSortDir] = useState<SortDir>('desc');

    const sorted = useMemo(() => {
        const copy = [...brands];
        copy.sort((a, b) => {
            let cmp = 0;
            switch (sortKey) {
                case 'name':
                    cmp = a.name.localeCompare(b.name, 'en', { sensitivity: 'base' });
                    break;
                case 'articles':
                    cmp = a.article_count - b.article_count;
                    break;
                case 'models':
                    cmp = a.model_count - b.model_count;
                    break;
            }
            return sortDir === 'asc' ? cmp : -cmp;
        });
        return copy;
    }, [brands, sortKey, sortDir]);

    const handleSort = (key: SortKey) => {
        if (key === sortKey) {
            setSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
        } else {
            setSortKey(key);
            setSortDir(key === 'name' ? 'asc' : 'desc');
        }
    };

    if (brands.length === 0) {
        return (
            <div className="text-center py-20">
                <div className="text-6xl mb-4">🚗</div>
                <h2 className="text-2xl font-bold text-gray-700 mb-2">No brands yet</h2>
                <p className="text-gray-500">Car catalog will auto-populate as articles are published.</p>
            </div>
        );
    }

    return (
        <>
            {/* Sort controls */}
            <div className="flex items-center justify-between mb-8 flex-wrap gap-3">
                <p className="text-sm text-gray-500">
                    {brands.length} brands
                </p>
                <div className="flex items-center gap-1 bg-white border border-gray-200 rounded-xl p-1 shadow-sm">
                    {SORT_OPTIONS.map(opt => {
                        const active = sortKey === opt.key;
                        return (
                            <button
                                key={opt.key}
                                onClick={() => handleSort(opt.key)}
                                className={`
                                    flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium
                                    transition-all duration-200
                                    ${active
                                        ? 'bg-indigo-600 text-white shadow-sm'
                                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                                    }
                                `}
                            >
                                <span className="text-xs">{opt.icon}</span>
                                <span>{opt.label}</span>
                                {active && (
                                    <span className="text-xs opacity-80">
                                        {sortDir === 'asc' ? '↑' : '↓'}
                                    </span>
                                )}
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Brands grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 sm:gap-6">
                {sorted.map((brand) => (
                    <Link
                        key={brand.slug}
                        href={`/cars/${brand.slug}`}
                        className="group relative bg-white rounded-2xl border border-gray-200 overflow-hidden transition-all duration-300 hover:border-indigo-400 hover:shadow-[0_20px_50px_rgba(79,70,229,0.12)] hover:-translate-y-1"
                    >
                        {/* Image */}
                        <div className="aspect-[16/10] bg-gradient-to-br from-gray-100 to-gray-50 overflow-hidden">
                            {brand.image ? (
                                <img
                                    src={fixImageUrl(brand.image)}
                                    alt={brand.name}
                                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                                />
                            ) : (
                                <div className="w-full h-full flex items-center justify-center text-4xl text-gray-300">
                                    🚗
                                </div>
                            )}
                        </div>

                        {/* Info */}
                        <div className="p-4">
                            <h3 className="font-bold text-gray-900 text-lg group-hover:text-indigo-600 transition-colors">
                                {brand.name}
                            </h3>
                            <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
                                <span>{brand.model_count} {brand.model_count === 1 ? 'model' : 'models'}</span>
                                <span className="text-gray-300">•</span>
                                <span>{brand.article_count} {brand.article_count === 1 ? 'article' : 'articles'}</span>
                            </div>
                        </div>

                        {/* Hover accent */}
                        <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-indigo-600 to-purple-600 transform scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left" />
                    </Link>
                ))}
            </div>
        </>
    );
}

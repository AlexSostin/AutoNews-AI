'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Hero from '@/components/public/Hero';
import EmptyState from '@/components/public/EmptyState';
import InfiniteArticleList from '@/components/public/InfiniteArticleList';
import MaintenanceGuard from '@/components/public/MaintenanceGuard';
import MaintenancePage from '@/components/public/MaintenancePage';
import TrendingSection from '@/components/public/TrendingSection';
import AdBanner from '@/components/public/AdBanner';
import { fixImageUrl } from '@/lib/config';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface HomeData {
    articles: any[];
    categories: any[];
    brands: any[];
    settings: any | null;
}

export default function ClientHomepage() {
    const [data, setData] = useState<HomeData>({
        articles: [],
        categories: [],
        brands: [],
        settings: null,
    });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        Promise.allSettled([
            fetch(`${API_URL}/articles/?is_published=true`).then(r => r.ok ? r.json() : { results: [] }),
            fetch(`${API_URL}/categories/`).then(r => r.ok ? r.json() : []),
            fetch(`${API_URL}/cars/brands/`).then(r => r.ok ? r.json() : []),
            fetch(`${API_URL}/settings/`).then(r => r.ok ? r.json() : null),
        ]).then(([articlesRes, categoriesRes, brandsRes, settingsRes]) => {
            const articles = articlesRes.status === 'fulfilled' ? (articlesRes.value?.results || []) : [];
            const rawCategories = categoriesRes.status === 'fulfilled' ? categoriesRes.value : [];
            const categories = Array.isArray(rawCategories) ? rawCategories : rawCategories?.results || [];
            const rawBrands = brandsRes.status === 'fulfilled' ? brandsRes.value : [];
            const brands = (Array.isArray(rawBrands) ? rawBrands : []).slice(0, 8);
            const settings = settingsRes.status === 'fulfilled' ? settingsRes.value : null;

            setData({ articles, categories, brands, settings });
        }).finally(() => setLoading(false));
    }, []);

    if (loading) {
        return <HomeSkeleton />;
    }

    const { articles, categories, brands, settings } = data;

    return (
        <MaintenanceGuard
            maintenanceMode={settings?.maintenance_mode || false}
            maintenanceMessage={settings?.maintenance_message}
            fallback={<MaintenancePage message={settings?.maintenance_message} />}
        >
            {/* Hero Section */}
            <Hero articles={articles} settings={settings} />

            {/* Top Leaderboard Ad */}
            <div className="container mx-auto px-4 py-8 flex justify-center">
                <AdBanner position="header" />
            </div>

            {/* Categories Section */}
            {categories.length > 0 && (
                <section className="relative py-16 overflow-hidden">
                    <div className="absolute top-1/2 left-0 -translate-y-1/2 w-64 h-64 bg-indigo-100/50 rounded-full blur-3xl -z-10"></div>
                    <div className="absolute top-1/2 right-0 -translate-y-1/2 w-96 h-96 bg-purple-100/30 rounded-full blur-3xl -z-10"></div>

                    <div className="container mx-auto px-4">
                        <div className="text-center mb-12">
                            <h2 className="text-3xl sm:text-4xl font-black text-gray-900 mb-4 tracking-tight">
                                Browse by Category
                            </h2>
                            <div className="w-20 h-1.5 bg-indigo-600 mx-auto rounded-full"></div>
                        </div>

                        <div className="flex flex-wrap gap-4 sm:gap-6 justify-center">
                            {categories.map((category: any) => (
                                <Link
                                    key={category.id}
                                    href={`/categories/${category.slug}`}
                                    className="group relative px-6 sm:px-8 py-3 sm:py-4 bg-white/70 backdrop-blur-md border border-gray-200 rounded-2xl transition-all duration-300 hover:border-indigo-500 hover:shadow-[0_20px_40px_rgba(79,70,229,0.15)] hover:-translate-y-1 overflow-hidden"
                                >
                                    <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                                    <div className="relative flex items-center gap-3">
                                        <span className="text-gray-900 font-bold text-lg sm:text-xl group-hover:text-indigo-600 transition-colors">
                                            {category.name}
                                        </span>
                                        <span className="flex items-center justify-center bg-gray-100 text-gray-500 text-xs font-black min-w-[28px] h-[28px] px-1.5 rounded-lg group-hover:bg-indigo-600 group-hover:text-white transition-all shadow-inner">
                                            {category.article_count}
                                        </span>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    </div>
                </section>
            )}

            {/* Browse by Brand Section */}
            {brands.length > 0 && settings?.show_browse_by_brand !== false && (
                <section className="py-12">
                    <div className="container mx-auto px-4">
                        <div className="text-center mb-10">
                            <h2 className="text-3xl sm:text-4xl font-black text-gray-900 mb-4 tracking-tight">
                                Browse by Brand
                            </h2>
                            <div className="w-20 h-1.5 bg-purple-600 mx-auto rounded-full" />
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
                            {brands.map((brand: any) => (
                                <Link
                                    key={brand.slug}
                                    href={`/cars/${brand.slug}`}
                                    className="group flex items-center gap-3 bg-white/70 backdrop-blur-md border border-gray-200 rounded-xl px-4 py-3 transition-all duration-300 hover:border-purple-400 hover:shadow-lg hover:-translate-y-0.5"
                                >
                                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-100 to-indigo-100 flex items-center justify-center text-lg group-hover:from-purple-200 group-hover:to-indigo-200 transition-all overflow-hidden flex-shrink-0">
                                        {brand.image ? (
                                            <img src={fixImageUrl(brand.image)} alt="" className="w-full h-full object-cover rounded-lg" />
                                        ) : (
                                            <span>🚗</span>
                                        )}
                                    </div>
                                    <div className="min-w-0">
                                        <div className="font-bold text-gray-900 group-hover:text-purple-600 transition-colors truncate">
                                            {brand.name}
                                        </div>
                                        <div className="text-xs text-gray-500">
                                            {brand.model_count} {brand.model_count === 1 ? 'model' : 'models'}
                                        </div>
                                    </div>
                                </Link>
                            ))}
                        </div>

                        <div className="text-center mt-8">
                            <Link
                                href="/cars"
                                className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600 text-white rounded-xl font-bold hover:bg-purple-700 transition-colors"
                            >
                                View All Brands →
                            </Link>
                        </div>
                    </div>
                </section>
            )}

            {/* Latest Articles */}
            <section className="container mx-auto px-4 py-16">
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                    <div className="lg:col-span-3">
                        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-10 gap-4">
                            <h2 className="text-3xl sm:text-4xl font-bold text-gray-800">Latest Articles</h2>
                            <Link href="/articles" className="text-indigo-600 hover:text-indigo-700 font-semibold hover:underline text-base sm:text-lg whitespace-nowrap">
                                View All →
                            </Link>
                        </div>

                        {articles.length === 0 ? (
                            <EmptyState />
                        ) : (
                            <InfiniteArticleList
                                initialArticles={articles.slice(0, 18)}
                                initialPage={1}
                                pageSize={18}
                                mobileRecommendedSlot={<TrendingSection />}
                            />
                        )}
                    </div>

                    <div className="hidden lg:block lg:col-span-1 space-y-6">
                        <TrendingSection />
                        <AdBanner position="sidebar" />
                    </div>
                </div>
            </section>

            {/* Bottom Ad */}
            <div className="container mx-auto px-4 pb-12 flex justify-center">
                <AdBanner position="footer" />
            </div>
        </MaintenanceGuard>
    );
}

function HomeSkeleton() {
    return (
        <>
            {/* Hero Skeleton */}
            <div className="bg-gradient-to-br from-slate-900 via-purple-900 to-gray-900 text-white py-24 animate-pulse">
                <div className="container mx-auto px-4 text-center">
                    <div className="h-10 bg-white/20 rounded-lg w-2/3 mx-auto mb-6" />
                    <div className="h-6 bg-white/10 rounded-lg w-1/2 mx-auto mb-8" />
                    <div className="h-12 bg-white/20 rounded-xl w-48 mx-auto" />
                </div>
            </div>

            {/* Categories Skeleton */}
            <div className="py-16">
                <div className="container mx-auto px-4">
                    <div className="h-8 bg-gray-200 rounded-lg w-64 mx-auto mb-8 animate-pulse" />
                    <div className="flex flex-wrap gap-4 justify-center">
                        {[1, 2, 3, 4, 5].map(i => (
                            <div key={i} className="h-12 w-32 bg-gray-200 rounded-2xl animate-pulse" />
                        ))}
                    </div>
                </div>
            </div>

            {/* Articles Skeleton */}
            <div className="container mx-auto px-4 py-16">
                <div className="h-8 bg-gray-200 rounded-lg w-48 mb-8 animate-pulse" />
                <div className="space-y-6">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 animate-pulse">
                            <div className="flex gap-4">
                                <div className="w-48 h-32 bg-gray-200 rounded-xl flex-shrink-0" />
                                <div className="flex-1 space-y-3">
                                    <div className="h-5 bg-gray-200 rounded w-3/4" />
                                    <div className="h-4 bg-gray-200 rounded w-full" />
                                    <div className="h-4 bg-gray-200 rounded w-2/3" />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </>
    );
}

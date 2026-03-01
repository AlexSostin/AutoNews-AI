'use client';

import { useState, useEffect, ReactNode } from 'react';
import Link from 'next/link';
import { fixImageUrl } from '@/lib/config';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// ===== BRAND PAGE FALLBACK =====
interface ModelData {
    model: string;
    slug: string;
    trim_count: number;
    article_count: number;
    engine: string;
    horsepower: string;
    price: string;
    price_date: string;
    image: string | null;
}

export function ClientBrandFallback({ brandSlug }: { brandSlug: string }) {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        fetch(`${API_URL}/cars/brands/${brandSlug}/`)
            .then(res => { if (!res.ok) throw new Error(); return res.json(); })
            .then(setData)
            .catch(() => setError(true))
            .finally(() => setLoading(false));
    }, [brandSlug]);

    if (loading) return <PageSkeleton title="Loading brand..." />;
    if (error || !data) return <NotFoundFallback title="Brand Not Found" backHref="/cars" backLabel="All Brands" />;

    // Dynamically import BrandModelsGrid
    const BrandModelsGrid = require('@/app/(public)/cars/[brand]/BrandModelsGrid').default;

    return (
        <main className="flex-1 bg-gradient-to-b from-gray-50 to-white min-h-screen">
            <section className="relative py-16 overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-purple-900 to-indigo-900" />
                <div className="relative container mx-auto px-4">
                    <nav className="flex items-center gap-2 text-sm text-purple-300 mb-6">
                        <Link href="/cars" className="hover:text-white transition-colors">Cars</Link>
                        <span>/</span>
                        <span className="text-white font-medium">{data.brand}</span>
                    </nav>
                    <h1 className="text-4xl sm:text-5xl font-black text-white mb-3 tracking-tight">{data.brand}</h1>
                    <p className="text-lg text-purple-200">
                        {data.model_count} {data.model_count === 1 ? 'model' : 'models'} in our catalog
                    </p>
                </div>
            </section>
            <BrandModelsGrid models={data.models} brand={data.brand} brandSlug={brandSlug} />
        </main>
    );
}

// ===== MODEL PAGE FALLBACK =====
export function ClientModelFallback({ brandSlug, modelSlug }: { brandSlug: string; modelSlug: string }) {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        fetch(`${API_URL}/cars/brands/${brandSlug}/models/${modelSlug}/`)
            .then(res => { if (!res.ok) throw new Error(); return res.json(); })
            .then(setData)
            .catch(() => setError(true))
            .finally(() => setLoading(false));
    }, [brandSlug, modelSlug]);

    if (loading) return <PageSkeleton title="Loading model..." />;
    if (error || !data) return <NotFoundFallback title="Model Not Found" backHref={`/cars/${brandSlug}`} backLabel="Back to Brand" />;

    const heroImage = data.images?.[0] ? fixImageUrl(data.images[0]) : null;
    const specs = data.specs || {};
    const hasSpecs = Object.values(specs).some((v: any) => v && v !== 'Not specified');

    // Dynamically import VehicleSpecsTable
    let VehicleSpecsTable: any = null;
    try { VehicleSpecsTable = require('@/components/public/VehicleSpecsTable').default; } catch { }

    return (
        <main className="flex-1 bg-gradient-to-b from-gray-50 to-white min-h-screen">
            {/* Hero */}
            <section className="relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-purple-900 to-indigo-900" />
                {heroImage && (
                    <div className="absolute inset-0 opacity-35">
                        <img src={heroImage} alt="" className="w-full h-full object-cover" />
                    </div>
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/20" />
                <div className="relative container mx-auto px-4 py-12 lg:py-16">
                    <nav className="flex items-center gap-2 text-sm text-purple-300 mb-6">
                        <Link href="/cars" className="hover:text-white transition-colors">Cars</Link>
                        <span>/</span>
                        <Link href={`/cars/${brandSlug}`} className="hover:text-white transition-colors">{data.brand}</Link>
                        <span>/</span>
                        <span className="text-white font-medium">{data.model}</span>
                    </nav>
                    <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
                        <div className="flex-1">
                            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black text-white mb-3 tracking-tight">
                                {data.full_name || `${data.brand} ${data.model}`}
                            </h1>
                            <div className="flex flex-wrap items-center gap-3 mt-4">
                                {specs.price && specs.price !== 'Not specified' && (
                                    <span className="bg-white/15 backdrop-blur-md rounded-xl px-4 py-2 border border-white/20 text-white font-bold text-lg">
                                        {specs.price}
                                    </span>
                                )}
                                {specs.horsepower && specs.horsepower !== 'Not specified' && (
                                    <span className="bg-white/10 backdrop-blur-md rounded-xl px-4 py-2 border border-white/15 text-purple-200 font-semibold">
                                        ⚡ {specs.horsepower}
                                    </span>
                                )}
                                {specs.zero_to_sixty && specs.zero_to_sixty !== 'Not specified' && (
                                    <span className="bg-white/10 backdrop-blur-md rounded-xl px-4 py-2 border border-white/15 text-purple-200 font-semibold">
                                        🏁 0-60 {specs.zero_to_sixty}
                                    </span>
                                )}
                            </div>
                        </div>
                        {data.trims?.[0]?.article_slug && (
                            <Link href={`/articles/${data.trims[0].article_slug}`}
                                className="inline-flex items-center gap-2 bg-white text-indigo-700 font-bold px-6 py-3 rounded-xl hover:bg-indigo-50 transition-colors shadow-lg shadow-black/20 whitespace-nowrap">
                                📖 Read Full Review →
                            </Link>
                        )}
                    </div>
                </div>
            </section>

            {/* Featured Car Image */}
            {heroImage && (
                <section className="container mx-auto px-4 -mt-6 relative z-10 mb-8">
                    <div className="rounded-2xl overflow-hidden shadow-2xl border border-gray-200">
                        <img src={heroImage} alt={data.full_name || data.model} className="w-full aspect-[21/9] object-cover" />
                    </div>
                </section>
            )}

            {/* Content */}
            <section className="container mx-auto px-4 py-8">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div className="lg:col-span-2 space-y-8">
                        {/* Specs Table (fallback) */}
                        {hasSpecs && !(data.vehicle_specs_list?.length > 0 || data.vehicle_specs) && (
                            <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
                                <div className="px-6 py-4 bg-gradient-to-r from-indigo-600 to-purple-600">
                                    <h2 className="text-xl font-bold text-white">📊 Specifications</h2>
                                </div>
                                <div className="px-6 py-2">
                                    {[
                                        ['Engine', specs.engine], ['Horsepower', specs.horsepower],
                                        ['Torque', specs.torque], ['0-60 mph', specs.zero_to_sixty],
                                        ['Top Speed', specs.top_speed],
                                        ['Price', specs.price ? (specs.price_date ? `${specs.price} (as of ${specs.price_date})` : specs.price) : ''],
                                    ].map(([label, value]) => (
                                        value && value !== 'Not specified' ? (
                                            <div key={label as string} className="flex justify-between items-center py-3 border-b border-gray-100 last:border-0">
                                                <span className="text-gray-500 font-medium">{label}</span>
                                                <span className="font-bold text-gray-900 text-right">{value}</span>
                                            </div>
                                        ) : null
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* VehicleSpecsTable */}
                        {VehicleSpecsTable && (data.vehicle_specs_list?.length > 0 || data.vehicle_specs) && (
                            <VehicleSpecsTable
                                vehicleSpecsList={
                                    data.vehicle_specs_list?.length > 0
                                        ? data.vehicle_specs_list
                                        : (data.vehicle_specs ? [data.vehicle_specs] : [])
                                }
                            />
                        )}

                        {/* Trims Table */}
                        {data.trims?.length > 0 && (
                            <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
                                <div className="px-6 py-4 bg-gradient-to-r from-slate-700 to-slate-800">
                                    <h2 className="text-xl font-bold text-white">
                                        {data.trims.length > 1 ? '⚙️ Available Trims' : '⚙️ Trim Details'}
                                    </h2>
                                </div>
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                        <thead className="bg-gray-50 border-b border-gray-200">
                                            <tr>
                                                {data.trims.length > 1 && <th className="text-left px-6 py-3 font-semibold text-gray-600">Trim</th>}
                                                <th className="text-left px-4 py-3 font-semibold text-gray-600">Engine</th>
                                                <th className="text-left px-4 py-3 font-semibold text-gray-600">Power</th>
                                                <th className="text-left px-4 py-3 font-semibold text-gray-600">Torque</th>
                                                <th className="text-left px-4 py-3 font-semibold text-gray-600">Price</th>
                                                <th className="text-left px-4 py-3 font-semibold text-gray-600">Article</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {data.trims.map((trim: any, i: number) => (
                                                <tr key={i} className="border-b border-gray-100 hover:bg-indigo-50/30 transition-colors">
                                                    {data.trims.length > 1 && (
                                                        <td className="px-6 py-3 font-bold text-gray-900">
                                                            {(!trim.trim || trim.trim === 'None') ? 'Base' : trim.trim}
                                                        </td>
                                                    )}
                                                    <td className="px-4 py-3 text-gray-600">{trim.engine || '—'}</td>
                                                    <td className="px-4 py-3 text-gray-600">{trim.horsepower || '—'}</td>
                                                    <td className="px-4 py-3 text-gray-600">{trim.torque || '—'}</td>
                                                    <td className="px-4 py-3 font-semibold text-indigo-700">{trim.price || '—'}</td>
                                                    <td className="px-4 py-3">
                                                        <Link href={`/articles/${trim.article_slug}`}
                                                            className="text-indigo-600 hover:text-indigo-700 font-medium hover:underline">
                                                            Read →
                                                        </Link>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {/* Gallery */}
                        {data.images?.length > 1 && (
                            <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
                                <div className="px-6 py-4 bg-gradient-to-r from-amber-500 to-orange-500">
                                    <h2 className="text-xl font-bold text-white">📷 Gallery ({data.images.length} photos)</h2>
                                </div>
                                <div className="p-4 space-y-2">
                                    <img src={fixImageUrl(data.images[0])} alt={`${data.full_name} — main`} className="w-full aspect-video object-cover rounded-xl" />
                                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                        {data.images.slice(1).map((img: string, i: number) => (
                                            <img key={i} src={fixImageUrl(img)} alt={`${data.full_name} photo ${i + 2}`}
                                                className="w-full aspect-video object-cover rounded-lg hover:opacity-90 transition-opacity" />
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Right sidebar */}
                    <div className="space-y-6">
                        {data.trims?.length > 0 && (
                            <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
                                <div className="px-6 py-4 bg-gradient-to-r from-green-600 to-emerald-600">
                                    <h2 className="text-lg font-bold text-white">📰 Reviews & Articles</h2>
                                </div>
                                <div className="p-4 space-y-1">
                                    {data.trims.map((trim: any, i: number) => (
                                        <Link key={i} href={`/articles/${trim.article_slug}`}
                                            className="block p-3 rounded-xl hover:bg-indigo-50 transition-colors group">
                                            <div className="font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors text-sm line-clamp-2">
                                                {trim.article_title}
                                            </div>
                                        </Link>
                                    ))}
                                </div>
                            </div>
                        )}

                        {data.related_articles?.length > 0 && (
                            <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
                                <div className="px-6 py-4 border-b border-gray-100">
                                    <h2 className="text-lg font-bold text-gray-900">More from {data.brand}</h2>
                                </div>
                                <div className="p-4 space-y-1">
                                    {data.related_articles.map((article: any) => (
                                        <Link key={article.id} href={`/articles/${article.slug}`}
                                            className="block p-3 rounded-xl hover:bg-gray-50 transition-colors group">
                                            <div className="font-medium text-gray-700 group-hover:text-indigo-600 transition-colors text-sm line-clamp-2">
                                                {article.title}
                                            </div>
                                        </Link>
                                    ))}
                                </div>
                            </div>
                        )}

                        <Link href={`/cars/${data.brand_slug || brandSlug}`}
                            className="flex items-center justify-center gap-2 w-full py-3 bg-indigo-600 text-white rounded-xl font-bold hover:bg-indigo-700 transition-colors">
                            ← All {data.brand} Models
                        </Link>
                    </div>
                </div>
            </section>
        </main>
    );
}

// ===== CATEGORY PAGE FALLBACK =====
export function ClientCategoryFallback({ slug }: { slug: string }) {
    const [category, setCategory] = useState<any>(null);
    const [articles, setArticles] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        Promise.allSettled([
            fetch(`${API_URL}/categories/?search=${slug}`).then(r => r.json()),
            fetch(`${API_URL}/articles/?category=${slug}&is_published=true`).then(r => r.json()),
        ]).then(([catRes, artRes]) => {
            if (catRes.status === 'fulfilled') {
                const cats = Array.isArray(catRes.value) ? catRes.value : catRes.value?.results || [];
                const matched = cats.find((c: any) => c.slug === slug);
                setCategory(matched || null);
            }
            if (artRes.status === 'fulfilled') {
                setArticles(artRes.value?.results || []);
            }
            setLoading(false);
        });
    }, [slug]);

    if (loading) return <PageSkeleton title="Loading category..." />;
    if (!category) return <NotFoundFallback title="Category Not Found" backHref="/articles" backLabel="All Articles" />;

    return (
        <main className="flex-1 bg-gradient-to-b from-gray-50 to-white min-h-screen">
            <section className="relative py-16 overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-indigo-900 via-purple-900 to-slate-900" />
                <div className="relative container mx-auto px-4 text-center">
                    <h1 className="text-4xl sm:text-5xl font-black text-white mb-3 tracking-tight">{category.name}</h1>
                    <p className="text-lg text-purple-200">{articles.length} articles</p>
                </div>
            </section>

            <section className="container mx-auto px-4 py-12">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {articles.map((article: any) => (
                        <Link key={article.id || article.slug} href={`/articles/${article.slug}`}
                            className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-lg transition-shadow group">
                            {article.image && (
                                <div className="h-48 overflow-hidden">
                                    <img src={fixImageUrl(article.image)} alt={article.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                                </div>
                            )}
                            <div className="p-4">
                                <h3 className="font-bold text-gray-900 mb-2 line-clamp-2">{article.title}</h3>
                                <p className="text-sm text-gray-500 line-clamp-2">{article.summary}</p>
                            </div>
                        </Link>
                    ))}
                </div>
                {articles.length === 0 && (
                    <p className="text-gray-500 text-center py-12">No articles in this category yet.</p>
                )}
            </section>
        </main>
    );
}

// ===== SHARED COMPONENTS =====
function PageSkeleton({ title }: { title: string }) {
    return (
        <main className="flex-1 bg-gray-50 min-h-screen">
            <div className="h-64 bg-gradient-to-br from-slate-900 via-purple-900 to-indigo-900 animate-pulse" />
            <div className="container mx-auto px-4 py-12">
                <div className="text-center text-gray-500 py-8">{title}</div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="bg-white rounded-xl shadow-sm p-6 space-y-3 animate-pulse">
                            <div className="h-6 bg-gray-200 rounded w-3/4" />
                            <div className="h-4 bg-gray-200 rounded w-1/2" />
                            <div className="h-4 bg-gray-200 rounded w-2/3" />
                        </div>
                    ))}
                </div>
            </div>
        </main>
    );
}

function NotFoundFallback({ title, backHref, backLabel }: { title: string; backHref: string; backLabel: string }) {
    return (
        <main className="flex-1 bg-gray-50 flex items-center justify-center min-h-screen">
            <div className="text-center py-20">
                <h1 className="text-4xl font-bold text-gray-900 mb-4">{title}</h1>
                <Link href={backHref} className="bg-indigo-600 text-white px-6 py-3 rounded-xl font-bold hover:bg-indigo-700 transition">
                    {backLabel}
                </Link>
            </div>
        </main>
    );
}

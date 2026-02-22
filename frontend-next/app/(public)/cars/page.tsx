import Link from 'next/link';
import type { Metadata } from 'next';
import { fixImageUrl } from '@/lib/config';

export const metadata: Metadata = {
    title: 'Car Catalog — Browse by Brand | Fresh Motors',
    description: 'Explore our complete car catalog. Browse by manufacturer to find detailed specs, reviews, and comparisons for every model.',
    alternates: {
        canonical: '/cars',
    },
};

export const revalidate = 3600; // revalidate every hour

const PRODUCTION_API_URL = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
const LOCAL_API_URL = 'http://localhost:8000/api/v1';

const getApiUrl = () => {
    if (typeof window === 'undefined' && process.env.API_INTERNAL_URL) {
        return process.env.API_INTERNAL_URL;
    }
    if (process.env.CUSTOM_DOMAIN_API) return process.env.CUSTOM_DOMAIN_API;
    if (process.env.RAILWAY_ENVIRONMENT === 'production') return PRODUCTION_API_URL;
    return process.env.NEXT_PUBLIC_API_URL || LOCAL_API_URL;
};

interface Brand {
    name: string;
    slug: string;
    model_count: number;
    article_count: number;
    image: string | null;
}

async function getBrands(): Promise<Brand[]> {
    try {
        const res = await fetch(`${getApiUrl()}/cars/brands/`, { next: { revalidate: 3600 } });
        if (!res.ok) return [];
        return await res.json();
    } catch {
        return [];
    }
}

export default async function CarsPage() {
    const brands = await getBrands();

    return (
        <main className="flex-1 bg-gradient-to-b from-gray-50 to-white min-h-screen">
            {/* Hero */}
            <section className="relative py-20 overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-brand-900 to-brand-900" />
                <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTSA2MCAwIEwgMCAwIDAgNjAiIGZpbGw9Im5vbmUiIHN0cm9rZT0icmdiYSgyNTUsMjU1LDI1NSwwLjAzKSIgc3Ryb2tlLXdpZHRoPSIxIi8+PC9wYXR0ZXJuPjwvZGVmcz48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSJ1cmwoI2dyaWQpIi8+PC9zdmc+')] opacity-50" />

                <div className="relative container mx-auto px-4 text-center">
                    <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-white mb-4 tracking-tight">
                        Car Catalog
                    </h1>
                    <p className="text-lg sm:text-xl text-brand-200 max-w-2xl mx-auto">
                        Browse specifications, reviews, and comparisons for every model we&apos;ve covered
                    </p>
                    <div className="mt-6 flex items-center justify-center gap-6 text-sm text-brand-300">
                        <span className="flex items-center gap-2">
                            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                            {brands.length} Brands
                        </span>
                        <span>•</span>
                        <span>{brands.reduce((sum, b) => sum + b.model_count, 0)} Models</span>
                        <span>•</span>
                        <span>{brands.reduce((sum, b) => sum + b.article_count, 0)} Articles</span>
                    </div>
                </div>
            </section>

            {/* Brands Grid */}
            <section className="container mx-auto px-4 py-16">
                {brands.length === 0 ? (
                    <div className="text-center py-20">
                        <div className="text-6xl mb-4">🚗</div>
                        <h2 className="text-2xl font-bold text-gray-700 mb-2">No brands yet</h2>
                        <p className="text-gray-500">Car catalog will auto-populate as articles are published.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 sm:gap-6">
                        {brands.map((brand) => (
                            <Link
                                key={brand.slug}
                                href={`/cars/${brand.slug}`}
                                className="group relative bg-white rounded-2xl border border-gray-200 overflow-hidden transition-all duration-300 hover:border-brand-400 hover:shadow-[0_20px_50px_rgba(79,70,229,0.12)] hover:-translate-y-1"
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
                                    <h3 className="font-bold text-gray-900 text-lg group-hover:text-brand-600 transition-colors">
                                        {brand.name}
                                    </h3>
                                    <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
                                        <span>{brand.model_count} {brand.model_count === 1 ? 'model' : 'models'}</span>
                                        <span className="text-gray-300">•</span>
                                        <span>{brand.article_count} {brand.article_count === 1 ? 'article' : 'articles'}</span>
                                    </div>
                                </div>

                                {/* Hover accent */}
                                <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-brand-600 to-brand-600 transform scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left" />
                            </Link>
                        ))}
                    </div>
                )}
            </section>

            {/* JSON-LD */}
            <script
                type="application/ld+json"
                dangerouslySetInnerHTML={{
                    __html: JSON.stringify({
                        '@context': 'https://schema.org',
                        '@type': 'CollectionPage',
                        name: 'Car Catalog — Fresh Motors',
                        description: 'Browse all car brands and models with detailed specifications.',
                        url: 'https://freshmotors.net/cars',
                        numberOfItems: brands.length,
                    }),
                }}
            />
        </main>
    );
}

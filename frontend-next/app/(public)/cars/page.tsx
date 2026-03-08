import type { Metadata } from 'next';
import BrandsSortableGrid from '@/components/public/BrandsSortableGrid';

export const metadata: Metadata = {
    title: 'Car Catalog — Browse by Brand | Fresh Motors',
    description: 'Explore our complete car catalog. Browse by manufacturer to find detailed specs, reviews, and comparisons for every model.',
    alternates: {
        canonical: '/cars',
    },
};

export const revalidate = 30; // revalidate every 30 seconds

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

interface BrandsResponse {
    brands: Brand[];
    total_articles: number;
    total_models: number;
}

async function getBrands(): Promise<BrandsResponse> {
    const fallback: BrandsResponse = { brands: [], total_articles: 0, total_models: 0 };
    try {
        const res = await fetch(`${getApiUrl()}/cars/brands/?include_totals=true`, { next: { revalidate: 30 } });
        if (!res.ok) return fallback;
        const data = await res.json();
        // Handle both array (old API) and object (new API with include_totals)
        if (Array.isArray(data)) {
            return { brands: data, total_articles: 0, total_models: 0 };
        }
        return {
            brands: Array.isArray(data?.brands) ? data.brands : [],
            total_articles: data?.total_articles ?? 0,
            total_models: data?.total_models ?? 0,
        };
    } catch {
        return fallback;
    }
}

export default async function CarsPage() {
    const { brands, total_articles, total_models } = await getBrands();

    return (
        <main className="flex-1 bg-gradient-to-b from-gray-50 to-white min-h-screen">
            {/* Hero */}
            <section className="relative py-20 overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-purple-900 to-indigo-900" />
                <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTSA2MCAwIEwgMCAwIDAgNjAiIGZpbGw9Im5vbmUiIHN0cm9rZT0icmdiYSgyNTUsMjU1LDI1NSwwLjAzKSIgc3Ryb2tlLXdpZHRoPSIxIi8+PC9wYXR0ZXJuPjwvZGVmcz48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSJ1cmwoI2dyaWQpIi8+PC9zdmc+')] opacity-50" />

                <div className="relative container mx-auto px-4 text-center">
                    <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-white mb-4 tracking-tight">
                        Car Catalog
                    </h1>
                    <p className="text-lg sm:text-xl text-purple-200 max-w-2xl mx-auto">
                        Browse specifications, reviews, and comparisons for every model we&apos;ve covered
                    </p>
                    <div className="mt-6 flex items-center justify-center gap-6 text-sm text-purple-300">
                        <span className="flex items-center gap-2">
                            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                            {brands.length} Brands
                        </span>
                        <span>•</span>
                        <span>{total_models || brands.reduce((sum, b) => sum + b.model_count, 0)} Models</span>
                        <span>•</span>
                        <span>{total_articles || brands.reduce((sum, b) => sum + b.article_count, 0)} Articles</span>
                    </div>
                </div>
            </section>

            {/* Brands Grid with sorting */}
            <section className="container mx-auto px-4 py-16">
                <BrandsSortableGrid brands={brands} />
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
                        url: 'https://www.freshmotors.net/cars',
                        numberOfItems: brands.length,
                    }),
                }}
            />
        </main>
    );
}

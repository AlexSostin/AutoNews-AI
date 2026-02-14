import Link from 'next/link';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { fixImageUrl } from '@/lib/config';
import BrandModelsGrid from './BrandModelsGrid';

export const dynamic = 'force-dynamic';

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

export interface ModelData {
    model: string;
    slug: string;
    trim_count: number;
    article_count: number;
    engine: string;
    horsepower: string;
    price: string;
    image: string | null;
}

interface BrandData {
    brand: string;
    slug: string;
    model_count: number;
    models: ModelData[];
}

async function getBrand(slug: string): Promise<BrandData | null> {
    try {
        const res = await fetch(`${getApiUrl()}/cars/brands/${slug}/`, { cache: 'no-store' });
        if (!res.ok) return null;
        return await res.json();
    } catch {
        return null;
    }
}

export async function generateMetadata({ params }: { params: Promise<{ brand: string }> }): Promise<Metadata> {
    const { brand: brandSlug } = await params;
    const data = await getBrand(brandSlug);
    if (!data) return { title: 'Brand Not Found' };

    return {
        title: `${data.brand} Cars — Models, Specs & Reviews | Fresh Motors`,
        description: `Browse all ${data.brand} models with detailed specifications, pricing, and reviews. ${data.model_count} models available.`,
        alternates: { canonical: `/cars/${brandSlug}` },
    };
}

export default async function BrandPage({ params }: { params: Promise<{ brand: string }> }) {
    const { brand: brandSlug } = await params;
    const data = await getBrand(brandSlug);

    if (!data) notFound();

    return (
        <main className="flex-1 bg-gradient-to-b from-gray-50 to-white min-h-screen">
            {/* Hero */}
            <section className="relative py-16 overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-purple-900 to-indigo-900" />
                <div className="relative container mx-auto px-4">
                    {/* Breadcrumbs */}
                    <nav className="flex items-center gap-2 text-sm text-purple-300 mb-6">
                        <Link href="/cars" className="hover:text-white transition-colors">Cars</Link>
                        <span>/</span>
                        <span className="text-white font-medium">{data.brand}</span>
                    </nav>

                    <h1 className="text-4xl sm:text-5xl font-black text-white mb-3 tracking-tight">
                        {data.brand}
                    </h1>
                    <p className="text-lg text-purple-200">
                        {data.model_count} {data.model_count === 1 ? 'model' : 'models'} in our catalog
                    </p>
                </div>
            </section>

            {/* Models Grid with Sorting (Client Component) */}
            <BrandModelsGrid models={data.models} brand={data.brand} brandSlug={brandSlug} />

            {/* JSON-LD Breadcrumb */}
            <script
                type="application/ld+json"
                dangerouslySetInnerHTML={{
                    __html: JSON.stringify({
                        '@context': 'https://schema.org',
                        '@type': 'BreadcrumbList',
                        itemListElement: [
                            { '@type': 'ListItem', position: 1, name: 'Cars', item: 'https://freshmotors.net/cars' },
                            { '@type': 'ListItem', position: 2, name: data.brand, item: `https://freshmotors.net/cars/${brandSlug}` },
                        ],
                    }),
                }}
            />
        </main>
    );
}

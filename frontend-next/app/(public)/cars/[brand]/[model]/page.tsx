import Link from 'next/link';
import { ClientModelFallback } from '@/components/public/ClientPageFallbacks';
import type { Metadata } from 'next';
import { fixImageUrl } from '@/lib/config';
import VehicleSpecsTable from '@/components/public/VehicleSpecsTable';

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

interface VehicleSpecItem {
    id: number;
    trim_name: string;
    make: string;
    model_name: string;
    drivetrain: string | null;
    motor_count: number | null;
    motor_placement: string | null;
    power_hp: number | null;
    power_kw: number | null;
    power_display: string | null;
    torque_nm: number | null;
    acceleration_0_100: number | null;
    top_speed_kmh: number | null;
    battery_kwh: number | null;
    range_km: number | null;
    range_wltp: number | null;
    range_epa: number | null;
    range_cltc: number | null;
    combined_range_km: number | null;
    range_display: string | null;
    charging_time_fast: string | null;
    charging_time_slow: string | null;
    charging_power_max_kw: number | null;
    transmission: string | null;
    body_type: string | null;
    fuel_type: string | null;
    seats: number | null;
    length_mm: number | null;
    width_mm: number | null;
    height_mm: number | null;
    wheelbase_mm: number | null;
    weight_kg: number | null;
    cargo_liters: number | null;
    cargo_liters_max: number | null;
    ground_clearance_mm: number | null;
    towing_capacity_kg: number | null;
    price_from: number | null;
    price_to: number | null;
    currency: string | null;
    price_usd_from: number | null;
    price_usd_to: number | null;
    price_updated_at: string | null;
    price_display: string | null;
    year: number | null;
    country_of_origin: string | null;
    platform: string | null;
    voltage_architecture: number | null;
    suspension_type: string | null;
    extra_specs: Record<string, unknown>;
}

interface ModelData {
    brand: string;
    brand_slug: string;
    model: string;
    model_slug: string;
    full_name: string;
    specs: {
        engine: string;
        horsepower: string;
        torque: string;
        zero_to_sixty: string;
        top_speed: string;
        price: string;
        price_date: string;
        release_date: string;
    };
    vehicle_specs: VehicleSpecItem | null;
    vehicle_specs_list: VehicleSpecItem[];
    images: string[];
    trims: {
        trim: string;
        engine: string;
        horsepower: string;
        torque: string;
        zero_to_sixty: string;
        top_speed: string;
        price: string;
        release_date: string;
        article_id: number;
        article_title: string;
        article_slug: string;
    }[];
    related_articles: {
        id: number;
        title: string;
        slug: string;
        created_at: string;
    }[];
}

async function getModel(brand: string, model: string): Promise<ModelData | null> {
    try {
        const res = await fetch(`${getApiUrl()}/cars/brands/${brand}/models/${model}/`, { next: { revalidate: 3600 } });
        if (!res.ok) return null;
        return await res.json();
    } catch {
        return null;
    }
}

export async function generateMetadata({ params }: { params: Promise<{ brand: string; model: string }> }): Promise<Metadata> {
    const { brand, model } = await params;
    const data = await getModel(brand, model);
    if (!data) return { title: 'Model Not Found' };

    const specsDesc = [
        data.specs.engine,
        data.specs.horsepower,
        data.specs.price,
    ].filter(Boolean).join(' • ');

    return {
        title: `${data.full_name} — Specs, Price & Review | Fresh Motors`,
        description: `${data.full_name} specifications and review. ${specsDesc}. Detailed specs, available trims, and related articles.`,
        alternates: { canonical: `/cars/${brand}/${model}` },
    };
}

// Spec row component
function SpecRow({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
    if (!value || value === 'Not specified') return null;
    return (
        <div className="flex justify-between items-center py-3 border-b border-gray-100 last:border-0">
            <span className="text-gray-500 font-medium">{label}</span>
            <span className={`font-bold text-right ${highlight ? 'text-indigo-700' : 'text-gray-900'}`}>{value}</span>
        </div>
    );
}

// Format date helper
function formatDate(dateStr: string) {
    try {
        const d = new Date(dateStr);
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
        return dateStr;
    }
}

export default async function ModelPage({ params }: { params: Promise<{ brand: string; model: string }> }) {
    const { brand: brandSlug, model: modelSlug } = await params;
    const data = await getModel(brandSlug, modelSlug);

    // SSR fetch failed (Docker dev mode) → client-side fallback
    if (!data) return <ClientModelFallback brandSlug={brandSlug} modelSlug={modelSlug} />;

    const hasSpecs = Object.values(data.specs).some(v => v && v !== 'Not specified');
    const primaryArticle = data.trims[0];
    const heroImage = data.images[0] ? fixImageUrl(data.images[0]) : null;
    const galleryImages = data.images.map(img => fixImageUrl(img));

    return (
        <main className="flex-1 bg-gradient-to-b from-gray-50 to-white min-h-screen">
            {/* Hero with Visible Car Image */}
            <section className="relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-purple-900 to-indigo-900" />

                {heroImage && (
                    <div className="absolute inset-0 opacity-35">
                        <img src={heroImage} alt="" className="w-full h-full object-cover" />
                    </div>
                )}

                {/* Extra gradient overlay for text readability */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/20" />

                <div className="relative container mx-auto px-4 py-12 lg:py-16">
                    {/* Breadcrumbs */}
                    <nav className="flex items-center gap-2 text-sm text-purple-300 mb-6">
                        <Link href="/cars" className="hover:text-white transition-colors">Cars</Link>
                        <span>/</span>
                        <Link href={`/cars/${data.brand_slug}`} className="hover:text-white transition-colors">{data.brand}</Link>
                        <span>/</span>
                        <span className="text-white font-medium">{data.model}</span>
                    </nav>

                    <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
                        <div className="flex-1">
                            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black text-white mb-3 tracking-tight">
                                {data.full_name}
                            </h1>

                            {/* Price & key stat as hero highlights */}
                            <div className="flex flex-wrap items-center gap-3 mt-4">
                                {data.specs.price && data.specs.price !== 'Not specified' && (
                                    <span className="bg-white/15 backdrop-blur-md rounded-xl px-4 py-2 border border-white/20 text-white font-bold text-lg">
                                        {data.specs.price}
                                    </span>
                                )}
                                {data.specs.horsepower && data.specs.horsepower !== 'Not specified' && (
                                    <span className="bg-white/10 backdrop-blur-md rounded-xl px-4 py-2 border border-white/15 text-purple-200 font-semibold">
                                        ⚡ {data.specs.horsepower}
                                    </span>
                                )}
                                {data.specs.zero_to_sixty && data.specs.zero_to_sixty !== 'Not specified' && (
                                    <span className="bg-white/10 backdrop-blur-md rounded-xl px-4 py-2 border border-white/15 text-purple-200 font-semibold">
                                        🏁 0-100 {data.specs.zero_to_sixty}
                                    </span>
                                )}
                            </div>
                        </div>

                        {/* CTA Button */}
                        {primaryArticle && (
                            <Link
                                href={`/articles/${primaryArticle.article_slug}`}
                                className="inline-flex items-center gap-2 bg-white text-indigo-700 font-bold px-6 py-3 rounded-xl hover:bg-indigo-50 transition-colors shadow-lg shadow-black/20 whitespace-nowrap"
                            >
                                📖 Read Full Review →
                            </Link>
                        )}
                    </div>
                </div>
            </section>

            {/* Featured Car Image — visible, not just background */}
            {heroImage && (
                <section className="container mx-auto px-4 -mt-6 relative z-10 mb-8">
                    <div className="rounded-2xl overflow-hidden shadow-2xl border border-gray-200">
                        <img
                            src={heroImage}
                            alt={data.full_name}
                            className="w-full aspect-[21/9] object-cover"
                        />
                    </div>
                </section>
            )}

            {/* Content */}
            <section className="container mx-auto px-4 py-8">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Left Column — Specs + Trims + Gallery */}
                    <div className="lg:col-span-2 space-y-8">
                        {/* Old Specs Table — only shown when NO VehicleSpecs exist (fallback) */}
                        {hasSpecs && !(data.vehicle_specs_list?.length > 0 || data.vehicle_specs) && (
                            <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
                                <div className="px-6 py-4 bg-gradient-to-r from-indigo-600 to-purple-600">
                                    <h2 className="text-xl font-bold text-white">📊 Specifications</h2>
                                </div>
                                <div className="px-6 py-2">
                                    <SpecRow label="Engine" value={data.specs.engine} />
                                    <SpecRow label="Horsepower" value={data.specs.horsepower} />
                                    <SpecRow label="Torque" value={data.specs.torque} />
                                    <SpecRow label="0-60 mph" value={data.specs.zero_to_sixty} />
                                    <SpecRow label="Top Speed" value={data.specs.top_speed} />
                                    <SpecRow label="Price" value={data.specs.price ? (data.specs.price_date ? `${data.specs.price} (as of ${data.specs.price_date})` : data.specs.price) : ''} highlight />
                                    <SpecRow label="Release Date" value={data.specs.release_date} />
                                </div>
                                <div className="px-6 py-3 bg-gray-50 border-t border-gray-100">
                                    <p className="text-xs text-gray-400 leading-relaxed">
                                        ⓘ Specifications are sourced from manufacturer data and video reviews. Actual specs may vary by market, configuration, and model year. Always verify with your local dealer.
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* VehicleSpecs — Trim Comparison or Single Spec */}
                        {(data.vehicle_specs_list?.length > 0 || data.vehicle_specs) && (
                            <VehicleSpecsTable
                                vehicleSpecsList={
                                    data.vehicle_specs_list?.length > 0
                                        ? data.vehicle_specs_list
                                        : (data.vehicle_specs ? [data.vehicle_specs] : [])
                                }
                            />
                        )}

                        {/* Trims Table — always show, even for 1 trim */}
                        {data.trims.length > 0 && (() => {
                            // Check if any trim has a meaningful name
                            const hasMeaningfulTrims = data.trims.some(t =>
                                t.trim && t.trim !== 'None' && t.trim !== 'Standard' && t.trim !== 'Base'
                            );
                            const showTrimColumn = hasMeaningfulTrims && data.trims.length > 1;

                            return (
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
                                                    {showTrimColumn && (
                                                        <th className="text-left px-6 py-3 font-semibold text-gray-600">Trim</th>
                                                    )}
                                                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Engine</th>
                                                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Power</th>
                                                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Torque</th>
                                                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Price</th>
                                                    <th className="text-left px-4 py-3 font-semibold text-gray-600">Article</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {data.trims.map((trim, i) => (
                                                    <tr key={i} className="border-b border-gray-100 hover:bg-indigo-50/30 transition-colors">
                                                        {showTrimColumn && (
                                                            <td className="px-6 py-3 font-bold text-gray-900">
                                                                {(!trim.trim || trim.trim === 'None') ? 'Base' : trim.trim}
                                                            </td>
                                                        )}
                                                        <td className="px-4 py-3 text-gray-600">{trim.engine || '—'}</td>
                                                        <td className="px-4 py-3 text-gray-600">{trim.horsepower || '—'}</td>
                                                        <td className="px-4 py-3 text-gray-600">{trim.torque || '—'}</td>
                                                        <td className="px-4 py-3 font-semibold text-indigo-700">{trim.price || '—'}</td>
                                                        <td className="px-4 py-3">
                                                            <Link
                                                                href={`/articles/${trim.article_slug}`}
                                                                className="text-indigo-600 hover:text-indigo-700 font-medium hover:underline"
                                                            >
                                                                Read →
                                                            </Link>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            );
                        })()}

                        {/* Gallery — featured + grid layout */}
                        {galleryImages.length > 1 && (
                            <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
                                <div className="px-6 py-4 bg-gradient-to-r from-amber-500 to-orange-500">
                                    <h2 className="text-xl font-bold text-white">📷 Gallery ({galleryImages.length} photos)</h2>
                                </div>
                                <div className="p-4 space-y-2">
                                    {/* Featured — first image large */}
                                    <img
                                        src={galleryImages[0]}
                                        alt={`${data.full_name} — main photo`}
                                        className="w-full aspect-video object-cover rounded-xl"
                                    />
                                    {/* Rest as smaller grid */}
                                    {galleryImages.length > 1 && (
                                        <div className={`grid gap-2 ${galleryImages.length === 2 ? 'grid-cols-1' : 'grid-cols-2 sm:grid-cols-3'}`}>
                                            {galleryImages.slice(1).map((img, i) => (
                                                <img
                                                    key={i}
                                                    src={img}
                                                    alt={`${data.full_name} photo ${i + 2}`}
                                                    className="w-full aspect-video object-cover rounded-lg hover:opacity-90 transition-opacity cursor-pointer"
                                                />
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Right Column — Articles & Related */}
                    <div className="space-y-6">
                        {/* Source Articles */}
                        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
                            <div className="px-6 py-4 bg-gradient-to-r from-green-600 to-emerald-600">
                                <h2 className="text-lg font-bold text-white">📰 Reviews & Articles</h2>
                            </div>
                            <div className="p-4 space-y-1">
                                {data.trims.map((trim, i) => (
                                    <Link
                                        key={i}
                                        href={`/articles/${trim.article_slug}`}
                                        className="block p-3 rounded-xl hover:bg-indigo-50 transition-colors group"
                                    >
                                        <div className="font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors text-sm line-clamp-2">
                                            {trim.article_title}
                                        </div>
                                        <div className="flex items-center gap-2 mt-1.5">
                                            {trim.trim !== 'Standard' && (
                                                <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                                                    {trim.trim}
                                                </span>
                                            )}
                                        </div>
                                    </Link>
                                ))}
                            </div>
                        </div>

                        {/* Related from same brand — with dates */}
                        {data.related_articles.length > 0 && (
                            <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
                                <div className="px-6 py-4 border-b border-gray-100">
                                    <h2 className="text-lg font-bold text-gray-900">More from {data.brand}</h2>
                                </div>
                                <div className="p-4 space-y-1">
                                    {data.related_articles.map((article) => (
                                        <Link
                                            key={article.id}
                                            href={`/articles/${article.slug}`}
                                            className="block p-3 rounded-xl hover:bg-gray-50 transition-colors group"
                                        >
                                            <div className="font-medium text-gray-700 group-hover:text-indigo-600 transition-colors text-sm line-clamp-2">
                                                {article.title}
                                            </div>
                                            <div className="text-xs text-gray-400 mt-1">
                                                {formatDate(article.created_at)}
                                            </div>
                                        </Link>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Back to brand */}
                        <Link
                            href={`/cars/${data.brand_slug}`}
                            className="flex items-center justify-center gap-2 w-full py-3 bg-indigo-600 text-white rounded-xl font-bold hover:bg-indigo-700 transition-colors"
                        >
                            ← All {data.brand} Models
                        </Link>
                    </div>
                </div>
            </section>

            {/* JSON-LD Vehicle Schema + Breadcrumb + Product */}
            <script
                type="application/ld+json"
                dangerouslySetInnerHTML={{
                    __html: JSON.stringify([
                        {
                            '@context': 'https://schema.org',
                            '@type': 'Vehicle',
                            name: data.full_name,
                            brand: { '@type': 'Brand', name: data.brand },
                            model: data.model,
                            ...(data.vehicle_specs ? {
                                ...(data.vehicle_specs.fuel_type && { fuelType: data.vehicle_specs.fuel_type }),
                                ...(data.vehicle_specs.transmission && { vehicleTransmission: data.vehicle_specs.transmission }),
                                ...(data.vehicle_specs.body_type && { bodyType: data.vehicle_specs.body_type }),
                                ...(data.vehicle_specs.seats && { seatingCapacity: data.vehicle_specs.seats }),
                                ...(data.vehicle_specs.year && { vehicleModelDate: String(data.vehicle_specs.year) }),
                                ...(data.vehicle_specs.drivetrain && { driveWheelConfiguration: data.vehicle_specs.drivetrain }),
                                ...(data.vehicle_specs.cargo_liters && { cargoVolume: { '@type': 'QuantitativeValue', value: data.vehicle_specs.cargo_liters, unitCode: 'LTR' } }),
                                ...(data.vehicle_specs.weight_kg && { weight: { '@type': 'QuantitativeValue', value: data.vehicle_specs.weight_kg, unitCode: 'KGM' } }),
                                ...(data.vehicle_specs.acceleration_0_100 && { accelerationTime: `${data.vehicle_specs.acceleration_0_100}s 0-100 km/h` }),
                                ...(data.vehicle_specs.top_speed_kmh && { speed: { '@type': 'QuantitativeValue', value: data.vehicle_specs.top_speed_kmh, unitCode: 'KMH' } }),
                                ...(data.vehicle_specs.country_of_origin && { manufacturer: { '@type': 'Organization', name: data.brand, location: data.vehicle_specs.country_of_origin } }),
                            } : {}),
                            ...(data.specs.engine && data.specs.engine !== 'Not specified' && {
                                vehicleEngine: { '@type': 'EngineSpecification', name: data.specs.engine },
                            }),
                            ...(data.vehicle_specs?.power_hp && {
                                vehicleEngine: {
                                    '@type': 'EngineSpecification',
                                    ...(data.specs.engine && data.specs.engine !== 'Not specified' && { name: data.specs.engine }),
                                    enginePower: { '@type': 'QuantitativeValue', value: data.vehicle_specs.power_hp, unitText: 'hp' },
                                    ...(data.vehicle_specs.torque_nm && { torque: { '@type': 'QuantitativeValue', value: data.vehicle_specs.torque_nm, unitText: 'Nm' } }),
                                },
                            }),
                            image: data.images[0] || undefined,
                            ...(data.vehicle_specs?.price_usd_from && {
                                offers: {
                                    '@type': 'AggregateOffer',
                                    priceCurrency: 'USD',
                                    lowPrice: data.vehicle_specs.price_usd_from,
                                    ...(data.vehicle_specs.price_usd_to && { highPrice: data.vehicle_specs.price_usd_to }),
                                    availability: 'https://schema.org/InStock',
                                },
                            }),
                            ...(!data.vehicle_specs?.price_usd_from && data.specs.price && data.specs.price !== 'Not specified' && {
                                offers: {
                                    '@type': 'Offer',
                                    price: data.specs.price.replace(/[^0-9.]/g, ''),
                                    priceCurrency: 'USD',
                                },
                            }),
                        },
                        {
                            '@context': 'https://schema.org',
                            '@type': 'BreadcrumbList',
                            itemListElement: [
                                { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://www.freshmotors.net' },
                                { '@type': 'ListItem', position: 2, name: 'Cars', item: 'https://www.freshmotors.net/cars' },
                                { '@type': 'ListItem', position: 3, name: data.brand, item: `https://www.freshmotors.net/cars/${data.brand_slug}` },
                                { '@type': 'ListItem', position: 4, name: data.model },
                            ],
                        },
                    ]),
                }}
            />
        </main>
    );
}

'use client';

import { useState, useEffect, useMemo } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { ArrowRight, ArrowLeftRight, Trophy, Zap, Battery, Gauge, Ruler, DollarSign, Weight, ChevronDown, Search, X } from 'lucide-react';

// ---------- types ----------
interface PickerBrand {
    name: string;
    slug: string;
    models: { name: string; slug: string }[];
}

interface CarSpec {
    [key: string]: any;
    full_name: string;
    make: string;
    model_name: string;
    trim_name: string;
    image: string | null;
    article_slug?: string;
    power_hp: number | null;
    torque_nm: number | null;
    acceleration_0_100: number | null;
    top_speed_kmh: number | null;
    battery_kwh: number | null;
    range_wltp: number | null;
    range_km: number | null;
    range_epa: number | null;
    charging_power_max_kw: number | null;
    charging_time_fast: string | null;
    weight_kg: number | null;
    length_mm: number | null;
    width_mm: number | null;
    height_mm: number | null;
    wheelbase_mm: number | null;
    cargo_liters: number | null;
    seats: number | null;
    drivetrain: string | null;
    body_type: string | null;
    fuel_type: string | null;
    transmission: string | null;
    price_usd_from: number | null;
    price_from: number | null;
    currency: string | null;
    country_of_origin: string | null;
    platform: string | null;
    voltage_architecture: number | null;
    suspension_type: string | null;
    year: number | null;
    ground_clearance_mm: number | null;
}

interface CompareData {
    car1: CarSpec;
    car2: CarSpec;
    winners: Record<string, 'car1' | 'car2' | 'tie'>;
}

// ---------- config ----------
const PROD_API = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
const LOCAL_API = 'http://localhost:8000/api/v1';
const getApi = () => {
    if (typeof window === 'undefined') return PROD_API;
    const h = window.location.hostname;
    return (h === 'localhost' || h === '127.0.0.1') ? LOCAL_API : PROD_API;
};

// Spec rows config — grouped sections
const SPEC_SECTIONS: { title: string; icon: React.ReactNode; rows: { key: string; label: string; unit?: string; format?: (v: any) => string }[] }[] = [
    {
        title: 'Performance',
        icon: <Zap size={20} className="text-yellow-500" />,
        rows: [
            { key: 'power_hp', label: 'Power', unit: 'hp' },
            { key: 'torque_nm', label: 'Torque', unit: 'Nm' },
            { key: 'acceleration_0_100', label: '0-100 km/h', unit: 's' },
            { key: 'top_speed_kmh', label: 'Top Speed', unit: 'km/h' },
            { key: 'drivetrain', label: 'Drivetrain' },
            { key: 'transmission', label: 'Transmission' },
        ],
    },
    {
        title: 'Battery & Range',
        icon: <Battery size={20} className="text-green-500" />,
        rows: [
            { key: 'battery_kwh', label: 'Battery', unit: 'kWh' },
            { key: 'range_wltp', label: 'Range (WLTP)', unit: 'km' },
            { key: 'range_epa', label: 'Range (EPA)', unit: 'km' },
            { key: 'range_km', label: 'Range (General)', unit: 'km' },
            { key: 'charging_power_max_kw', label: 'Max Charging Power', unit: 'kW' },
            { key: 'charging_time_fast', label: 'Fast Charging' },
            { key: 'voltage_architecture', label: 'Architecture', unit: 'V' },
        ],
    },
    {
        title: 'Dimensions',
        icon: <Ruler size={20} className="text-blue-500" />,
        rows: [
            { key: 'length_mm', label: 'Length', unit: 'mm' },
            { key: 'width_mm', label: 'Width', unit: 'mm' },
            { key: 'height_mm', label: 'Height', unit: 'mm' },
            { key: 'wheelbase_mm', label: 'Wheelbase', unit: 'mm' },
            { key: 'ground_clearance_mm', label: 'Ground Clearance', unit: 'mm' },
            { key: 'weight_kg', label: 'Weight', unit: 'kg' },
            { key: 'cargo_liters', label: 'Cargo', unit: 'L' },
            { key: 'seats', label: 'Seats' },
        ],
    },
    {
        title: 'Price & Info',
        icon: <DollarSign size={20} className="text-emerald-500" />,
        rows: [
            { key: 'price_usd_from', label: 'Price (USD)', format: (v: number) => `$${v.toLocaleString()}` },
            { key: 'body_type', label: 'Body Type' },
            { key: 'fuel_type', label: 'Fuel Type' },
            { key: 'year', label: 'Year' },
            { key: 'country_of_origin', label: 'Origin' },
            { key: 'platform', label: 'Platform' },
            { key: 'suspension_type', label: 'Suspension' },
        ],
    },
];

// ---------- Picker component ----------
function CarPicker({
    brands,
    selected,
    onChange,
    label,
}: {
    brands: PickerBrand[];
    selected: { brand: string; model: string };
    onChange: (brand: string, model: string) => void;
    label: string;
}) {
    const [search, setSearch] = useState('');
    const [open, setOpen] = useState(false);

    const filtered = useMemo(() => {
        if (!search) return brands;
        const q = search.toLowerCase();
        return brands
            .map(b => ({
                ...b,
                models: b.models.filter(m =>
                    m.name.toLowerCase().includes(q) || b.name.toLowerCase().includes(q)
                ),
            }))
            .filter(b => b.models.length > 0);
    }, [brands, search]);

    const selectedBrand = brands.find(b => b.slug === selected.brand);
    const selectedModel = selectedBrand?.models.find(m => m.slug === selected.model);
    const displayText = selectedModel ? `${selectedBrand?.name} ${selectedModel.name}` : 'Select a car...';

    return (
        <div className="relative">
            <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">{label}</label>
            <button
                onClick={() => setOpen(!open)}
                className={`w-full px-4 py-3.5 text-left rounded-xl border-2 transition-all font-semibold flex items-center justify-between ${selected.model
                        ? 'border-indigo-500 bg-indigo-50 text-gray-900'
                        : 'border-gray-200 bg-white text-gray-400 hover:border-indigo-300'
                    }`}
            >
                <span className="truncate">{displayText}</span>
                <ChevronDown size={18} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
            </button>

            {open && (
                <div className="absolute z-50 mt-2 w-full bg-white rounded-xl shadow-2xl border border-gray-200 max-h-80 overflow-hidden">
                    <div className="p-3 border-b border-gray-100 sticky top-0 bg-white">
                        <div className="relative">
                            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                            <input
                                type="text"
                                placeholder="Search brand or model..."
                                value={search}
                                onChange={e => setSearch(e.target.value)}
                                className="w-full pl-9 pr-8 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                                autoFocus
                            />
                            {search && (
                                <button onClick={() => setSearch('')} className="absolute right-2 top-1/2 -translate-y-1/2">
                                    <X size={14} className="text-gray-400" />
                                </button>
                            )}
                        </div>
                    </div>
                    <div className="overflow-y-auto max-h-60">
                        {filtered.map(brand => (
                            <div key={brand.slug}>
                                <div className="px-4 py-1.5 text-xs font-bold text-gray-400 uppercase tracking-wider bg-gray-50">
                                    {brand.name}
                                </div>
                                {brand.models.map(model => (
                                    <button
                                        key={`${brand.slug}-${model.slug}`}
                                        onClick={() => {
                                            onChange(brand.slug, model.slug);
                                            setOpen(false);
                                            setSearch('');
                                        }}
                                        className={`w-full text-left px-6 py-2.5 text-sm hover:bg-indigo-50 transition-colors ${selected.brand === brand.slug && selected.model === model.slug
                                                ? 'bg-indigo-100 text-indigo-700 font-bold'
                                                : 'text-gray-700'
                                            }`}
                                    >
                                        {brand.name} {model.name}
                                    </button>
                                ))}
                            </div>
                        ))}
                        {filtered.length === 0 && (
                            <div className="p-6 text-center text-gray-400 text-sm">No cars match your search</div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

// ---------- Main Compare Page ----------
export default function ComparePage() {
    const searchParams = useSearchParams();
    const router = useRouter();

    const [brands, setBrands] = useState<PickerBrand[]>([]);
    const [car1, setCar1] = useState({ brand: '', model: '' });
    const [car2, setCar2] = useState({ brand: '', model: '' });
    const [data, setData] = useState<CompareData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // Load picker data
    useEffect(() => {
        fetch(`${getApi()}/cars/picker/`)
            .then(r => r.json())
            .then(d => setBrands(d))
            .catch(() => { });
    }, []);

    // Parse URL params on load
    useEffect(() => {
        const c1 = searchParams.get('car1');
        const c2 = searchParams.get('car2');
        if (c1) {
            const [b, m] = c1.split('/');
            if (b && m) setCar1({ brand: b, model: m });
        }
        if (c2) {
            const [b, m] = c2.split('/');
            if (b && m) setCar2({ brand: b, model: m });
        }
    }, [searchParams]);

    // Fetch comparison when both cars selected
    useEffect(() => {
        if (!car1.brand || !car1.model || !car2.brand || !car2.model) return;

        // Update URL
        const params = new URLSearchParams();
        params.set('car1', `${car1.brand}/${car1.model}`);
        params.set('car2', `${car2.brand}/${car2.model}`);
        router.replace(`/compare?${params.toString()}`, { scroll: false });

        setLoading(true);
        setError('');

        fetch(`${getApi()}/cars/compare/?car1=${car1.brand}/${car1.model}&car2=${car2.brand}/${car2.model}`)
            .then(r => {
                if (!r.ok) throw new Error('Cars not found');
                return r.json();
            })
            .then(d => { setData(d); setLoading(false); })
            .catch(e => { setError(e.message); setLoading(false); });
    }, [car1, car2]);

    // Swap cars
    const swap = () => {
        setCar1(car2);
        setCar2(car1);
    };

    const getWinnerClass = (field: string, car: 'car1' | 'car2') => {
        if (!data?.winners[field]) return '';
        if (data.winners[field] === car) return 'bg-emerald-50 text-emerald-700 font-bold';
        if (data.winners[field] === 'tie') return 'bg-gray-50';
        return '';
    };

    const formatVal = (val: any, row: typeof SPEC_SECTIONS[0]['rows'][0]) => {
        if (val === null || val === undefined || val === '') return '—';
        if (row.format) return row.format(val);
        return row.unit ? `${val} ${row.unit}` : String(val);
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-indigo-50/30">
            {/* Hero */}
            <div className="bg-gradient-to-r from-indigo-600 via-purple-600 to-indigo-700 text-white">
                <div className="max-w-6xl mx-auto px-4 py-12 sm:py-16 text-center">
                    <h1 className="text-3xl sm:text-5xl font-extrabold mb-3">
                        <ArrowLeftRight className="inline-block mr-3 mb-1" size={36} />
                        Compare Cars
                    </h1>
                    <p className="text-indigo-200 text-lg max-w-xl mx-auto">
                        Side-by-side comparison of specifications, performance, and pricing
                    </p>
                </div>
            </div>

            <div className="max-w-6xl mx-auto px-4 -mt-8">
                {/* Picker Card */}
                <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-6 sm:p-8 mb-8">
                    <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-4 items-end">
                        <CarPicker brands={brands} selected={car1} onChange={(b, m) => setCar1({ brand: b, model: m })} label="Car 1" />
                        <button
                            onClick={swap}
                            disabled={!car1.model || !car2.model}
                            className="self-end p-3 rounded-xl bg-indigo-50 text-indigo-600 hover:bg-indigo-100 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                            title="Swap cars"
                        >
                            <ArrowLeftRight size={22} />
                        </button>
                        <CarPicker brands={brands} selected={car2} onChange={(b, m) => setCar2({ brand: b, model: m })} label="Car 2" />
                    </div>
                </div>

                {/* Loading */}
                {loading && (
                    <div className="text-center py-16">
                        <div className="inline-block animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600" />
                        <p className="mt-4 text-gray-500">Loading comparison...</p>
                    </div>
                )}

                {/* Error */}
                {error && <div className="text-center py-12 text-red-500 font-semibold">{error}</div>}

                {/* Empty state */}
                {!data && !loading && !error && (
                    <div className="text-center py-16">
                        <div className="text-7xl mb-4">🏎️</div>
                        <h2 className="text-xl font-bold text-gray-700 mb-2">Select two cars to compare</h2>
                        <p className="text-gray-400">Choose from the dropdowns above to see a detailed spec-by-spec comparison</p>
                    </div>
                )}

                {/* Comparison Table */}
                {data && !loading && (
                    <div className="mb-12">
                        {/* Car Headers */}
                        <div className="grid grid-cols-[1fr_1fr] gap-4 mb-6">
                            {[data.car1, data.car2].map((car, i) => (
                                <div key={i} className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
                                    {car.image && (
                                        <div className="relative h-48 sm:h-56">
                                            <Image src={car.image} alt={car.full_name} fill className="object-cover" unoptimized />
                                        </div>
                                    )}
                                    <div className="p-4 sm:p-5">
                                        <h2 className="text-lg sm:text-xl font-extrabold text-gray-900">{car.full_name}</h2>
                                        <div className="flex flex-wrap gap-2 mt-2">
                                            {car.fuel_type && (
                                                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-700">
                                                    {car.fuel_type}
                                                </span>
                                            )}
                                            {car.body_type && (
                                                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-100 text-blue-700">
                                                    {car.body_type}
                                                </span>
                                            )}
                                            {car.year && (
                                                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-gray-100 text-gray-600">
                                                    {car.year}
                                                </span>
                                            )}
                                        </div>
                                        {car.article_slug && (
                                            <Link
                                                href={`/articles/${car.article_slug}`}
                                                className="inline-flex items-center gap-1 mt-3 text-sm font-bold text-indigo-600 hover:text-indigo-800 transition-colors"
                                            >
                                                Read Review <ArrowRight size={14} />
                                            </Link>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Score Summary */}
                        {Object.keys(data.winners).length > 0 && (() => {
                            const car1Wins = Object.values(data.winners).filter(w => w === 'car1').length;
                            const car2Wins = Object.values(data.winners).filter(w => w === 'car2').length;
                            const ties = Object.values(data.winners).filter(w => w === 'tie').length;
                            return (
                                <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-2xl border border-indigo-100 p-5 mb-6 flex items-center justify-center gap-6 sm:gap-12">
                                    <div className="text-center">
                                        <div className={`text-3xl font-black ${car1Wins > car2Wins ? 'text-emerald-600' : 'text-gray-700'}`}>
                                            {car1Wins > car2Wins && <Trophy size={18} className="inline mb-1 mr-1" />}
                                            {car1Wins}
                                        </div>
                                        <div className="text-xs font-bold text-gray-500 mt-1">{data.car1.make}</div>
                                    </div>
                                    <div className="text-center">
                                        <div className="text-lg font-bold text-gray-400">{ties} ties</div>
                                    </div>
                                    <div className="text-center">
                                        <div className={`text-3xl font-black ${car2Wins > car1Wins ? 'text-emerald-600' : 'text-gray-700'}`}>
                                            {car2Wins > car1Wins && <Trophy size={18} className="inline mb-1 mr-1" />}
                                            {car2Wins}
                                        </div>
                                        <div className="text-xs font-bold text-gray-500 mt-1">{data.car2.make}</div>
                                    </div>
                                </div>
                            );
                        })()}

                        {/* Spec Sections */}
                        {SPEC_SECTIONS.map((section) => {
                            // Only show section if at least one row has data
                            const hasData = section.rows.some(
                                row => (data.car1[row.key] != null && data.car1[row.key] !== '') ||
                                    (data.car2[row.key] != null && data.car2[row.key] !== '')
                            );
                            if (!hasData) return null;

                            return (
                                <div key={section.title} className="bg-white rounded-2xl shadow-md border border-gray-100 mb-4 overflow-hidden">
                                    <div className="flex items-center gap-2 px-5 py-3.5 bg-gray-50 border-b border-gray-100">
                                        {section.icon}
                                        <h3 className="text-base font-extrabold text-gray-800">{section.title}</h3>
                                    </div>
                                    <div className="divide-y divide-gray-50">
                                        {section.rows.map(row => {
                                            const v1 = data.car1[row.key];
                                            const v2 = data.car2[row.key];
                                            if ((v1 == null || v1 === '') && (v2 == null || v2 === '')) return null;

                                            return (
                                                <div key={row.key} className="grid grid-cols-[1fr_auto_1fr] items-center">
                                                    <div className={`px-5 py-3 text-sm text-right ${getWinnerClass(row.key, 'car1')}`}>
                                                        {formatVal(v1, row)}
                                                    </div>
                                                    <div className="px-3 py-3 text-xs font-bold text-gray-400 text-center whitespace-nowrap min-w-[100px] sm:min-w-[140px]">
                                                        {row.label}
                                                        {data.winners[row.key] && data.winners[row.key] !== 'tie' && (
                                                            <Trophy size={12} className="inline ml-1 text-emerald-500 mb-0.5" />
                                                        )}
                                                    </div>
                                                    <div className={`px-5 py-3 text-sm text-left ${getWinnerClass(row.key, 'car2')}`}>
                                                        {formatVal(v2, row)}
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            );
                        })}

                        {/* Share URL */}
                        <div className="text-center mt-8">
                            <button
                                onClick={() => {
                                    navigator.clipboard.writeText(window.location.href);
                                    alert('Comparison URL copied!');
                                }}
                                className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-bold hover:bg-indigo-700 transition-all shadow-lg hover:shadow-xl"
                            >
                                📋 Copy Comparison Link
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

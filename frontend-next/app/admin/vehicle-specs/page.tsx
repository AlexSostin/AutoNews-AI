'use client';

import React, { useState, useEffect } from 'react';
import { Edit, Trash2, X, Search, ChevronLeft, ChevronRight, ChevronDown, Sparkles, Save, ExternalLink, Loader2, Plus, Copy } from 'lucide-react';
import api from '@/lib/api';
import Link from 'next/link';

interface ArticleOption {
    id: number;
    title: string;
    slug: string;
}

interface VehicleSpec {
    id: number;
    article: number | null;
    article_title?: string;
    make: string;
    model_name: string;
    trim_name: string;
    drivetrain: string | null;
    motor_count: number | null;
    motor_placement: string | null;
    power_hp: number | null;
    power_kw: number | null;
    torque_nm: number | null;
    acceleration_0_100: number | null;
    top_speed_kmh: number | null;
    battery_kwh: number | null;
    range_km: number | null;
    range_wltp: number | null;
    range_epa: number | null;
    range_cltc: number | null;
    charging_time_fast: string | null;
    charging_time_slow: string | null;
    charging_power_max_kw: number | null;
    transmission: string | null;
    transmission_gears: number | null;
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
    year: number | null;
    model_year: number | null;
    country_of_origin: string | null;
    platform: string | null;
    voltage_architecture: number | null;
    suspension_type: string | null;
    extra_specs: Record<string, unknown>;
    extracted_at: string;
    confidence_score: number;
}

const PAGE_SIZE = 20;

function FieldInput({ label, value, onChange, type = 'text', placeholder, required }: {
    label: string; value: string | number | null; onChange: (v: string) => void; type?: string; placeholder?: string; required?: boolean;
}) {
    return (
        <div>
            <label className="block text-xs font-semibold text-gray-900 mb-1">
                {label}{required && <span className="text-red-500 ml-0.5">*</span>}
            </label>
            <input
                type={type}
                value={value ?? ''}
                onChange={e => onChange(e.target.value)}
                placeholder={placeholder}
                className={`w-full px-3 py-2 border rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 ${required && !value ? 'border-red-300 bg-red-50/30' : 'border-gray-200'
                    }`}
            />
        </div>
    );
}

function SelectInput({ label, value, onChange, options }: {
    label: string; value: string | null; onChange: (v: string) => void; options: { value: string; label: string }[];
}) {
    return (
        <div>
            <label className="block text-xs font-semibold text-gray-900 mb-1">{label}</label>
            <select
                value={value ?? ''}
                onChange={e => onChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
            >
                <option value="">—</option>
                {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
        </div>
    );
}

export default function VehicleSpecsPage() {
    const [specs, setSpecs] = useState<VehicleSpec[]>([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editingSpec, setEditingSpec] = useState<VehicleSpec | null>(null);
    const [isCreateMode, setIsCreateMode] = useState(false);
    const [form, setForm] = useState<Record<string, unknown>>({});
    const [search, setSearch] = useState('');
    const [page, setPage] = useState(0);
    const [saving, setSaving] = useState(false);
    const [aiText, setAiText] = useState('');
    const [aiLoading, setAiLoading] = useState(false);
    const [aiResult, setAiResult] = useState<string | null>(null);
    const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

    // Create new: article search
    const [articleSearch, setArticleSearch] = useState('');
    const [articleResults, setArticleResults] = useState<ArticleOption[]>([]);
    const [selectedArticle, setSelectedArticle] = useState<ArticleOption | null>(null);
    const [articleSearching, setArticleSearching] = useState(false);

    const fetchSpecs = async () => {
        setLoading(true);
        try {
            const { data } = await api.get('/vehicle-specs/');
            // Enrich with article titles
            const enriched = await Promise.all(
                (data.results || data).map(async (spec: VehicleSpec) => {
                    if (!spec.article_title && spec.article) {
                        try {
                            const { data: article } = await api.get(`/articles/${spec.article}/`);
                            return { ...spec, article_title: article.title };
                        } catch { return spec; }
                    }
                    return spec;
                })
            );
            setSpecs(enriched);
        } catch (err) {
            console.error('Failed to fetch vehicle specs:', err);
        }
        setLoading(false);
    };

    useEffect(() => { fetchSpecs(); }, []);

    const filtered = specs.filter(s => {
        const q = search.toLowerCase();
        return !q || (s.make || '').toLowerCase().includes(q)
            || (s.model_name || '').toLowerCase().includes(q)
            || (s.trim_name || '').toLowerCase().includes(q)
            || (s.article_title || '').toLowerCase().includes(q)
            || (s.platform || '').toLowerCase().includes(q);
    });

    // Group filtered specs by make+model
    const grouped = filtered.reduce<Record<string, VehicleSpec[]>>((acc, spec) => {
        const key = (spec.make && spec.model_name) ? `${spec.make} ${spec.model_name}` : spec.article_title || `#${spec.id}`;
        if (!acc[key]) acc[key] = [];
        acc[key].push(spec);
        return acc;
    }, {});
    const groupKeys = Object.keys(grouped);
    const totalPages = Math.ceil(groupKeys.length / PAGE_SIZE);
    const pageGroupKeys = groupKeys.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

    const toggleGroup = (key: string) => {
        setExpandedGroups(prev => {
            const next = new Set(prev);
            if (next.has(key)) next.delete(key);
            else next.add(key);
            return next;
        });
    };

    const openEdit = (spec: VehicleSpec) => {
        setIsCreateMode(false);
        setEditingSpec(spec);
        setForm({ ...spec });
        setAiText('');
        setAiResult(null);
        setShowModal(true);
    };

    const openCreate = () => {
        setIsCreateMode(true);
        setEditingSpec(null);
        setSelectedArticle(null);
        setArticleSearch('');
        setArticleResults([]);
        setForm({
            make: '', model_name: '', trim_name: '',
            drivetrain: null, motor_count: null, motor_placement: null,
            power_hp: null, power_kw: null, torque_nm: null,
            acceleration_0_100: null, top_speed_kmh: null,
            battery_kwh: null, range_km: null, range_wltp: null, range_epa: null, range_cltc: null,
            charging_time_fast: null, charging_time_slow: null, charging_power_max_kw: null,
            transmission: null, transmission_gears: null,
            body_type: null, fuel_type: null, seats: null,
            length_mm: null, width_mm: null, height_mm: null, wheelbase_mm: null,
            weight_kg: null, cargo_liters: null, cargo_liters_max: null,
            ground_clearance_mm: null, towing_capacity_kg: null,
            price_from: null, price_to: null, currency: 'USD',
            year: null, model_year: null, country_of_origin: null,
            platform: null, voltage_architecture: null, suspension_type: null,
            extra_specs: {},
        });
        setAiText('');
        setAiResult(null);
        setShowModal(true);
    };

    const searchArticles = async (q: string) => {
        setArticleSearch(q);
        if (q.length < 2) { setArticleResults([]); return; }
        setArticleSearching(true);
        try {
            const { data } = await api.get(`/articles/?search=${encodeURIComponent(q)}&page_size=10`);
            const articles = (data.results || data).map((a: { id: number; title: string; slug: string }) => ({
                id: a.id, title: a.title, slug: a.slug,
            }));
            setArticleResults(articles);
        } catch { setArticleResults([]); }
        setArticleSearching(false);
    };

    const selectArticle = (article: ArticleOption) => {
        setSelectedArticle(article);
        setArticleSearch(article.title);
        setArticleResults([]);
    };

    const updateField = (key: string, value: string) => {
        const numFields = ['motor_count', 'power_hp', 'power_kw', 'torque_nm', 'top_speed_kmh',
            'range_km', 'range_wltp', 'range_epa', 'range_cltc', 'charging_power_max_kw',
            'transmission_gears', 'seats', 'length_mm', 'width_mm', 'height_mm', 'wheelbase_mm',
            'weight_kg', 'cargo_liters', 'cargo_liters_max', 'ground_clearance_mm', 'towing_capacity_kg',
            'price_from', 'price_to', 'year', 'model_year', 'voltage_architecture'];
        const floatFields = ['acceleration_0_100', 'battery_kwh', 'confidence_score'];

        if (numFields.includes(key)) {
            setForm(f => ({ ...f, [key]: value === '' ? null : parseInt(value) }));
        } else if (floatFields.includes(key)) {
            setForm(f => ({ ...f, [key]: value === '' ? null : parseFloat(value) }));
        } else {
            setForm(f => ({ ...f, [key]: value === '' ? null : value }));
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            if (isCreateMode) {
                const hasMakeModel = form.make && form.model_name;
                if (!selectedArticle && !hasMakeModel) {
                    alert('Please select an article or fill in Make and Model.');
                    setSaving(false);
                    return;
                }
                await api.post('/vehicle-specs/', { ...form, ...(selectedArticle ? { article: selectedArticle.id } : {}) });
            } else {
                if (!editingSpec) return;
                await api.patch(`/vehicle-specs/${editingSpec.id}/`, form);
            }
            setShowModal(false);
            fetchSpecs();
        } catch (err: unknown) {
            console.error('Save failed:', err);
            const errDetail = (err as { response?: { data?: { detail?: string; article?: string[] } } })?.response?.data;
            const msg = errDetail?.detail || errDetail?.article?.[0] || 'Save failed. Check console.';
            alert(msg);
        }
        setSaving(false);
    };

    const handleDelete = async (id: number) => {
        if (!confirm('Delete this vehicle spec?')) return;
        try {
            await api.delete(`/vehicle-specs/${id}/`);
            fetchSpecs();
        } catch (err) {
            console.error('Delete failed:', err);
        }
    };

    const handleAiFill = async () => {
        if (!aiText.trim()) return;
        setAiLoading(true);
        setAiResult(null);
        try {
            const articleId = isCreateMode ? selectedArticle?.id : editingSpec?.article;
            const { data } = await api.post('/vehicle-specs/ai_fill/', {
                text: aiText,
                article_id: articleId,
            });
            if (data.success && data.extracted) {
                const extractedList: Record<string, unknown>[] = Array.isArray(data.extracted) ? data.extracted : [data.extracted];
                const trimCount = extractedList.length;

                if (trimCount > 1 && articleId && data.saved) {
                    // Multiple trims saved to DB — refresh list and close modal
                    setAiResult(`✅ Extracted & saved ${trimCount} trims`);
                    fetchSpecs();
                    setTimeout(() => { setShowModal(false); }, 1200);
                } else {
                    // Single trim or preview — merge first into form
                    const extracted = extractedList[0];
                    const merged = { ...form };
                    Object.entries(extracted).forEach(([key, value]) => {
                        if (value !== null && value !== undefined) {
                            merged[key] = value;
                        }
                    });
                    setForm(merged);
                    const fieldCount = Object.values(extracted).filter(v => v !== null).length;
                    setAiResult(`✅ Extracted ${fieldCount} fields${trimCount > 1 ? ` (showing trim 1 of ${trimCount})` : ''}`);
                }
            } else {
                setAiResult(`❌ ${data.message || 'Extraction failed'}`);
            }
        } catch (err: unknown) {
            const errMsg = err instanceof Error ? err.message : 'Unknown error';
            setAiResult(`❌ Error: ${errMsg}`);
        }
        setAiLoading(false);
    };

    // Format display values
    const fmtPower = (s: VehicleSpec) => {
        if (s.power_hp && s.power_kw) return `${s.power_hp} HP / ${s.power_kw} kW`;
        if (s.power_hp) return `${s.power_hp} HP`;
        if (s.power_kw) return `${s.power_kw} kW`;
        return '—';
    };
    const fmtRange = (s: VehicleSpec) => {
        if (s.range_wltp) return `${s.range_wltp} km (WLTP)`;
        if (s.range_epa) return `${s.range_epa} km (EPA)`;
        if (s.range_cltc) return `${s.range_cltc} km (CLTC)`;
        if (s.range_km) return `${s.range_km} km`;
        return '—';
    };
    const fmtBattery = (s: VehicleSpec) => s.battery_kwh ? `${s.battery_kwh} kWh` : '—';

    const drivetrainOptions = [
        { value: 'FWD', label: 'Front-Wheel Drive' },
        { value: 'RWD', label: 'Rear-Wheel Drive' },
        { value: 'AWD', label: 'All-Wheel Drive' },
        { value: '4WD', label: 'Four-Wheel Drive' },
    ];
    const transmissionOptions = [
        { value: 'automatic', label: 'Automatic' },
        { value: 'manual', label: 'Manual' },
        { value: 'CVT', label: 'CVT' },
        { value: 'single-speed', label: 'Single-Speed' },
        { value: 'dual-clutch', label: 'Dual-Clutch' },
    ];
    const bodyOptions = [
        { value: 'sedan', label: 'Sedan' }, { value: 'SUV', label: 'SUV' },
        { value: 'hatchback', label: 'Hatchback' }, { value: 'coupe', label: 'Coupe' },
        { value: 'truck', label: 'Truck' }, { value: 'crossover', label: 'Crossover' },
        { value: 'wagon', label: 'Wagon' }, { value: 'shooting_brake', label: 'Shooting Brake' },
        { value: 'van', label: 'Van' }, { value: 'convertible', label: 'Convertible' },
        { value: 'pickup', label: 'Pickup' },
    ];
    const fuelOptions = [
        { value: 'EV', label: 'Electric' }, { value: 'Hybrid', label: 'Hybrid' },
        { value: 'PHEV', label: 'Plug-in Hybrid' }, { value: 'Gas', label: 'Gasoline' },
        { value: 'Diesel', label: 'Diesel' }, { value: 'Hydrogen', label: 'Hydrogen' },
    ];
    const currencyOptions = [
        { value: 'USD', label: 'USD' }, { value: 'EUR', label: 'EUR' },
        { value: 'CNY', label: 'CNY' }, { value: 'RUB', label: 'RUB' },
        { value: 'GBP', label: 'GBP' }, { value: 'JPY', label: 'JPY' },
    ];

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">🔧 Vehicle Specs</h1>
                    <p className="text-sm text-gray-500 mt-1">
                        Detailed vehicle specifications with AI extraction
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <button onClick={openCreate}
                        className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 transition-colors shadow-sm">
                        <Plus size={16} /> New Spec
                    </button>
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                            type="text"
                            value={search}
                            onChange={e => { setSearch(e.target.value); setPage(0); }}
                            placeholder="Search..."
                            className="pl-10 pr-4 py-2 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 w-64"
                        />
                    </div>
                    <span className="text-sm text-gray-500 font-medium">{filtered.length} specs · {groupKeys.length} models</span>
                </div>
            </div>

            {/* Table */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="text-left px-4 py-3 font-semibold text-gray-600">Make / Model</th>
                                <th className="text-left px-3 py-3 font-semibold text-gray-600">Trim</th>
                                <th className="text-left px-3 py-3 font-semibold text-gray-600">Type</th>
                                <th className="text-left px-3 py-3 font-semibold text-gray-600">Power</th>
                                <th className="text-left px-3 py-3 font-semibold text-gray-600">Battery</th>
                                <th className="text-left px-3 py-3 font-semibold text-gray-600">Range</th>
                                <th className="text-center px-3 py-3 font-semibold text-gray-600">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading ? (
                                <tr><td colSpan={7} className="text-center py-12 text-gray-400">Loading...</td></tr>
                            ) : pageGroupKeys.length === 0 ? (
                                <tr><td colSpan={7} className="text-center py-12 text-gray-400">No vehicle specs found</td></tr>
                            ) : pageGroupKeys.map(groupKey => {
                                const groupSpecs = grouped[groupKey];
                                const isMulti = groupSpecs.length > 1;
                                const isExpanded = expandedGroups.has(groupKey) || !isMulti;
                                return (
                                    <React.Fragment key={groupKey}>
                                        {/* Group header row */}
                                        {isMulti && (
                                            <tr
                                                className="bg-gradient-to-r from-indigo-50/80 to-purple-50/50 border-b border-indigo-100 cursor-pointer hover:from-indigo-100/80 transition-colors"
                                                onClick={() => toggleGroup(groupKey)}
                                            >
                                                <td colSpan={7} className="px-4 py-2.5">
                                                    <div className="flex items-center gap-2">
                                                        <ChevronDown size={16} className={`text-indigo-500 transition-transform ${isExpanded ? '' : '-rotate-90'}`} />
                                                        <span className="font-bold text-gray-900">{groupKey}</span>
                                                        <span className="inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-bold bg-indigo-100 text-indigo-700">
                                                            {groupSpecs.length} trims
                                                        </span>
                                                        {groupSpecs[0].article_title && (
                                                            <span className="text-xs text-gray-400 ml-2">📎 {groupSpecs[0].article_title}</span>
                                                        )}
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                        {/* Trim rows */}
                                        {isExpanded && groupSpecs.map(spec => (
                                            <tr key={spec.id} className={`border-b border-gray-100 hover:bg-indigo-50/30 transition-colors ${isMulti ? 'bg-white' : ''}`}>
                                                <td className="px-4 py-3 max-w-xs">
                                                    {isMulti ? (
                                                        <div className="pl-6 text-gray-500 text-sm">└─</div>
                                                    ) : (
                                                        <div>
                                                            <div className="font-medium text-gray-900 truncate" title={groupKey}>{groupKey}</div>
                                                            {spec.article_title && spec.make && (
                                                                <div className="text-xs text-gray-400 mt-0.5">📎 {spec.article_title}</div>
                                                            )}
                                                        </div>
                                                    )}
                                                </td>
                                                <td className="px-3 py-3 text-gray-700 whitespace-nowrap font-medium">
                                                    {spec.trim_name || <span className="text-gray-300">—</span>}
                                                </td>
                                                <td className="px-3 py-3">
                                                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${spec.fuel_type === 'EV' ? 'bg-green-100 text-green-700' :
                                                        spec.fuel_type === 'Hybrid' || spec.fuel_type === 'PHEV' ? 'bg-blue-100 text-blue-700' :
                                                            'bg-gray-100 text-gray-600'
                                                        }`}>
                                                        {spec.fuel_type || '—'}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-3 text-gray-700 whitespace-nowrap">{fmtPower(spec)}</td>
                                                <td className="px-3 py-3 text-gray-700 whitespace-nowrap">{fmtBattery(spec)}</td>
                                                <td className="px-3 py-3 text-gray-700 whitespace-nowrap">{fmtRange(spec)}</td>
                                                <td className="px-3 py-3 text-center">
                                                    <div className="flex items-center justify-center gap-1">
                                                        <button onClick={() => openEdit(spec)} className="p-1.5 text-indigo-600 hover:bg-indigo-100 rounded-lg" title="Edit">
                                                            <Edit size={16} />
                                                        </button>
                                                        <button onClick={() => handleDelete(spec.id)} className="p-1.5 text-red-500 hover:bg-red-100 rounded-lg" title="Delete">
                                                            <Trash2 size={16} />
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </React.Fragment>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex items-center justify-between">
                    <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
                        className="flex items-center gap-1 px-4 py-2 bg-white border rounded-lg text-sm disabled:opacity-40">
                        <ChevronLeft size={16} /> Prev
                    </button>
                    <span className="text-sm text-gray-500">{page + 1} / {totalPages}</span>
                    <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
                        className="flex items-center gap-1 px-4 py-2 bg-white border rounded-lg text-sm disabled:opacity-40">
                        Next <ChevronRight size={16} />
                    </button>
                </div>
            )}

            {/* Edit Modal */}
            {showModal && (editingSpec || isCreateMode) && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center overflow-y-auto py-8">
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl mx-4">
                        {/* Modal Header */}
                        <div className="flex items-center justify-between px-6 py-4 border-b bg-gradient-to-r from-indigo-600 to-purple-600 rounded-t-2xl">
                            <div>
                                <h2 className="text-lg font-bold text-white">
                                    {isCreateMode ? '✨ Create Vehicle Specs' : 'Edit Vehicle Specs'}
                                </h2>
                                <p className="text-sm text-indigo-200 truncate max-w-lg">
                                    {isCreateMode
                                        ? (selectedArticle ? selectedArticle.title : 'Select an article below')
                                        : (editingSpec?.article_title || `Article #${editingSpec?.article}`)}
                                </p>
                            </div>
                            <div className="flex items-center gap-2">
                                {!isCreateMode && editingSpec && (
                                    <Link href={`/articles/${editingSpec.article}`} target="_blank"
                                        className="p-2 text-white/70 hover:text-white hover:bg-white/10 rounded-lg">
                                        <ExternalLink size={18} />
                                    </Link>
                                )}
                                <button onClick={() => setShowModal(false)} className="p-2 text-white/70 hover:text-white hover:bg-white/10 rounded-lg">
                                    <X size={20} />
                                </button>
                            </div>
                        </div>

                        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
                            {/* Article Selector (Create mode only) */}
                            {isCreateMode && (
                                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                                    <h3 className="text-sm font-bold text-blue-900 mb-2 flex items-center gap-2">
                                        <Search size={16} /> Select Article
                                    </h3>
                                    <div className="relative">
                                        <input
                                            type="text"
                                            value={articleSearch}
                                            onChange={e => searchArticles(e.target.value)}
                                            placeholder="Search articles by title..."
                                            className="w-full px-3 py-2 border border-blue-200 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-blue-500 bg-white"
                                        />
                                        {articleSearching && (
                                            <Loader2 size={14} className="animate-spin absolute right-3 top-1/2 -translate-y-1/2 text-blue-400" />
                                        )}
                                        {articleResults.length > 0 && (
                                            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                                                {articleResults.map(a => (
                                                    <button key={a.id} onClick={() => selectArticle(a)}
                                                        className="w-full text-left px-3 py-2 text-sm hover:bg-indigo-50 transition-colors border-b border-gray-50 last:border-0">
                                                        <span className="font-medium text-gray-900">{a.title}</span>
                                                        <span className="text-xs text-gray-400 ml-2">#{a.id}</span>
                                                    </button>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                    {selectedArticle && (
                                        <div className="mt-2 flex items-center gap-2 text-sm text-blue-900">
                                            <span className="bg-blue-100 px-2 py-0.5 rounded-full font-medium">✓ {selectedArticle.title}</span>
                                            <button onClick={() => { setSelectedArticle(null); setArticleSearch(''); }}
                                                className="text-blue-400 hover:text-blue-600"><X size={14} /></button>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* AI Fill Section */}
                            <div className="bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 rounded-xl p-4">
                                <h3 className="text-sm font-bold text-purple-900 mb-2 flex items-center gap-2">
                                    <Sparkles size={16} /> AI Fill from Text
                                </h3>
                                <p className="text-xs text-purple-900 mb-3">
                                    Paste car specs text below and AI will extract and fill all fields automatically.
                                </p>
                                <textarea
                                    value={aiText}
                                    onChange={e => setAiText(e.target.value)}
                                    placeholder="Paste vehicle specs text here (e.g. from press release, review, or spec sheet)..."
                                    className="w-full h-28 px-3 py-2 border border-purple-200 rounded-lg text-sm text-gray-900 resize-y focus:ring-2 focus:ring-purple-500 bg-white"
                                />
                                <div className="flex items-center justify-between mt-2">
                                    <button
                                        onClick={handleAiFill}
                                        disabled={aiLoading || !aiText.trim()}
                                        className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                    >
                                        {aiLoading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                                        {aiLoading ? 'Extracting...' : '🤖 AI Extract'}
                                    </button>
                                    {aiResult && (
                                        <span className={`text-sm font-medium ${aiResult.startsWith('✅') ? 'text-green-600' : 'text-red-600'}`}>
                                            {aiResult}
                                        </span>
                                    )}
                                </div>
                            </div>

                            {/* Identity */}
                            <div>
                                <h3 className="text-sm font-bold text-gray-900 mb-3 border-b pb-1">🏷️ Car Identity</h3>
                                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                                    <FieldInput label="Make (Brand)" value={form.make as string} onChange={v => updateField('make', v)} placeholder="Zeekr, BMW, Tesla..." required />
                                    <FieldInput label="Model" value={form.model_name as string} onChange={v => updateField('model_name', v)} placeholder="007 GT, iX3..." required />
                                    <FieldInput label="Trim / Variant" value={form.trim_name as string} onChange={v => updateField('trim_name', v)} placeholder="AWD 100 kWh, Long Range..." />
                                </div>
                            </div>

                            {/* General */}
                            <div>
                                <h3 className="text-sm font-bold text-gray-900 mb-3 border-b pb-1">🚗 General</h3>
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                    <SelectInput label="Body Type" value={form.body_type as string} onChange={v => updateField('body_type', v)} options={bodyOptions} />
                                    <SelectInput label="Fuel Type" value={form.fuel_type as string} onChange={v => updateField('fuel_type', v)} options={fuelOptions} />
                                    <FieldInput label="Seats" value={form.seats as number} onChange={v => updateField('seats', v)} type="number" />
                                    <FieldInput label="Year" value={form.year as number} onChange={v => updateField('year', v)} type="number" />
                                    <FieldInput label="Model Year" value={form.model_year as number} onChange={v => updateField('model_year', v)} type="number" />
                                    <FieldInput label="Country" value={form.country_of_origin as string} onChange={v => updateField('country_of_origin', v)} placeholder="China" />
                                    <FieldInput label="Platform" value={form.platform as string} onChange={v => updateField('platform', v)} placeholder="SEA, MEB..." />
                                    <FieldInput label="Voltage (V)" value={form.voltage_architecture as number} onChange={v => updateField('voltage_architecture', v)} type="number" placeholder="800" />
                                </div>
                            </div>

                            {/* Drivetrain & Performance */}
                            <div>
                                <h3 className="text-sm font-bold text-gray-900 mb-3 border-b pb-1">⚡ Drivetrain & Performance</h3>
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                    <SelectInput label="Drivetrain" value={form.drivetrain as string} onChange={v => updateField('drivetrain', v)} options={drivetrainOptions} />
                                    <FieldInput label="Motors" value={form.motor_count as number} onChange={v => updateField('motor_count', v)} type="number" />
                                    <FieldInput label="Motor Placement" value={form.motor_placement as string} onChange={v => updateField('motor_placement', v)} placeholder="front+rear" />
                                    <SelectInput label="Transmission" value={form.transmission as string} onChange={v => updateField('transmission', v)} options={transmissionOptions} />
                                    <FieldInput label="Power (HP)" value={form.power_hp as number} onChange={v => updateField('power_hp', v)} type="number" />
                                    <FieldInput label="Power (kW)" value={form.power_kw as number} onChange={v => updateField('power_kw', v)} type="number" />
                                    <FieldInput label="Torque (Nm)" value={form.torque_nm as number} onChange={v => updateField('torque_nm', v)} type="number" />
                                    <FieldInput label="0-100 km/h (s)" value={form.acceleration_0_100 as number} onChange={v => updateField('acceleration_0_100', v)} type="number" />
                                    <FieldInput label="Top Speed (km/h)" value={form.top_speed_kmh as number} onChange={v => updateField('top_speed_kmh', v)} type="number" />
                                    <FieldInput label="Suspension" value={form.suspension_type as string} onChange={v => updateField('suspension_type', v)} placeholder="Air suspension" />
                                </div>
                            </div>

                            {/* EV & Battery */}
                            <div>
                                <h3 className="text-sm font-bold text-gray-900 mb-3 border-b pb-1">🔋 EV & Battery</h3>
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                    <FieldInput label="Battery (kWh)" value={form.battery_kwh as number} onChange={v => updateField('battery_kwh', v)} type="number" />
                                    <FieldInput label="Range (km)" value={form.range_km as number} onChange={v => updateField('range_km', v)} type="number" />
                                    <FieldInput label="Range WLTP (km)" value={form.range_wltp as number} onChange={v => updateField('range_wltp', v)} type="number" />
                                    <FieldInput label="Range EPA (km)" value={form.range_epa as number} onChange={v => updateField('range_epa', v)} type="number" />
                                    <FieldInput label="Range CLTC (km)" value={form.range_cltc as number} onChange={v => updateField('range_cltc', v)} type="number" />
                                    <FieldInput label="Fast Charge" value={form.charging_time_fast as string} onChange={v => updateField('charging_time_fast', v)} placeholder="30 min to 80%" />
                                    <FieldInput label="Slow Charge" value={form.charging_time_slow as string} onChange={v => updateField('charging_time_slow', v)} placeholder="8h (AC)" />
                                    <FieldInput label="Max Charge (kW)" value={form.charging_power_max_kw as number} onChange={v => updateField('charging_power_max_kw', v)} type="number" />
                                </div>
                            </div>

                            {/* Dimensions */}
                            <div>
                                <h3 className="text-sm font-bold text-gray-900 mb-3 border-b pb-1">📐 Dimensions</h3>
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                    <FieldInput label="Length (mm)" value={form.length_mm as number} onChange={v => updateField('length_mm', v)} type="number" />
                                    <FieldInput label="Width (mm)" value={form.width_mm as number} onChange={v => updateField('width_mm', v)} type="number" />
                                    <FieldInput label="Height (mm)" value={form.height_mm as number} onChange={v => updateField('height_mm', v)} type="number" />
                                    <FieldInput label="Wheelbase (mm)" value={form.wheelbase_mm as number} onChange={v => updateField('wheelbase_mm', v)} type="number" />
                                    <FieldInput label="Weight (kg)" value={form.weight_kg as number} onChange={v => updateField('weight_kg', v)} type="number" />
                                    <FieldInput label="Cargo (L)" value={form.cargo_liters as number} onChange={v => updateField('cargo_liters', v)} type="number" />
                                    <FieldInput label="Cargo Max (L)" value={form.cargo_liters_max as number} onChange={v => updateField('cargo_liters_max', v)} type="number" />
                                    <FieldInput label="Clearance (mm)" value={form.ground_clearance_mm as number} onChange={v => updateField('ground_clearance_mm', v)} type="number" />
                                    <FieldInput label="Towing (kg)" value={form.towing_capacity_kg as number} onChange={v => updateField('towing_capacity_kg', v)} type="number" />
                                </div>
                            </div>

                            {/* Pricing */}
                            <div>
                                <h3 className="text-sm font-bold text-gray-900 mb-3 border-b pb-1">💰 Pricing</h3>
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                    <FieldInput label="Price From" value={form.price_from as number} onChange={v => updateField('price_from', v)} type="number" />
                                    <FieldInput label="Price To" value={form.price_to as number} onChange={v => updateField('price_to', v)} type="number" />
                                    <SelectInput label="Currency" value={form.currency as string} onChange={v => updateField('currency', v)} options={currencyOptions} />
                                </div>
                            </div>
                        </div>

                        {/* Modal Footer */}
                        <div className="flex items-center justify-between px-6 py-4 border-t bg-gray-50 rounded-b-2xl">
                            <div>
                                {!isCreateMode && editingSpec && (
                                    <button
                                        onClick={() => {
                                            // Duplicate current spec as a new trim
                                            setIsCreateMode(true);
                                            setEditingSpec(null);
                                            setForm(f => ({ ...f, trim_name: '', id: undefined }));
                                            setSelectedArticle(editingSpec.article ? { id: editingSpec.article, title: editingSpec.article_title || '', slug: '' } : null);
                                            setArticleSearch(editingSpec.article_title || '');
                                        }}
                                        className="flex items-center gap-1.5 px-3 py-2 text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-lg text-sm font-medium transition-colors"
                                    >
                                        <Copy size={14} />
                                        + Duplicate as Trim
                                    </button>
                                )}
                            </div>
                            <div className="flex items-center gap-3">
                                <button onClick={() => setShowModal(false)}
                                    className="px-4 py-2 text-gray-600 hover:text-gray-800 text-sm font-medium">
                                    Cancel
                                </button>
                                <button onClick={handleSave} disabled={saving || (isCreateMode && !selectedArticle && !(form.make && form.model_name))}
                                    className="flex items-center gap-2 px-5 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors">
                                    {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                                    {saving ? 'Saving...' : (isCreateMode ? 'Create Spec' : 'Save Changes')}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

'use client';

import { useState, useEffect, useMemo } from 'react';
import { Edit, Trash2, X, Search, ChevronLeft, ChevronRight, Filter, CheckCircle, Circle, ShieldCheck, RefreshCw } from 'lucide-react';
import api from '@/lib/api';
import Link from 'next/link';

interface CarSpec {
    id: number;
    article: number;
    article_title: string;
    model_name: string;
    make: string;
    model: string;
    trim: string;
    engine: string;
    horsepower: string;
    torque: string;
    zero_to_sixty: string;
    top_speed: string;
    drivetrain: string;
    price: string;
    release_date: string;
    is_verified: boolean;
    verified_at: string | null;
}

const EMPTY_FORM = {
    make: '',
    model: '',
    trim: '',
    engine: '',
    horsepower: '',
    torque: '',
    zero_to_sixty: '',
    top_speed: '',
    drivetrain: '',
    price: '',
    release_date: '',
};

const PAGE_SIZE = 20;

export default function CarSpecsPage() {
    const [specs, setSpecs] = useState<CarSpec[]>([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editingSpec, setEditingSpec] = useState<CarSpec | null>(null);
    const [search, setSearch] = useState('');
    const [selectedBrand, setSelectedBrand] = useState('all');
    const [verifiedFilter, setVerifiedFilter] = useState<'all' | 'verified' | 'unverified'>('all');
    const [page, setPage] = useState(1);
    const [formData, setFormData] = useState(EMPTY_FORM);
    const [saving, setSaving] = useState(false);
    const [extractingId, setExtractingId] = useState<number | null>(null);

    useEffect(() => {
        fetchSpecs();
    }, []);

    const fetchSpecs = async () => {
        try {
            setLoading(true);
            const response = await api.get('/car-specifications/?page_size=1000');
            const data = Array.isArray(response.data) ? response.data : response.data.results || [];
            setSpecs(data);
        } catch (error) {
            console.error('Failed to fetch car specs:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleEdit = (spec: CarSpec) => {
        setEditingSpec(spec);
        setFormData({
            make: spec.make || '',
            model: spec.model || '',
            trim: spec.trim || '',
            engine: spec.engine || '',
            horsepower: spec.horsepower || '',
            torque: spec.torque || '',
            zero_to_sixty: spec.zero_to_sixty || '',
            top_speed: spec.top_speed || '',
            drivetrain: spec.drivetrain || '',
            price: spec.price || '',
            release_date: spec.release_date || '',
        });
        setShowModal(true);
    };

    const handleDelete = async (id: number) => {
        if (!confirm('Are you sure you want to delete this car specification?')) return;

        try {
            await api.delete(`/car-specifications/${id}/`);
            setSpecs(specs.filter(s => s.id !== id));
        } catch (error) {
            console.error('Failed to delete car spec:', error);
            alert('Failed to delete car specification');
        }
    };

    const handleReExtract = async (spec: CarSpec) => {
        if (!confirm(`Re-extract specs for "${spec.article_title}"?\nThis will overwrite current values with AI/regex extraction.`)) return;
        setExtractingId(spec.id);
        try {
            const response = await api.post(`/car-specifications/${spec.id}/re_extract/`);
            if (response.data.success) {
                setSpecs(specs.map(s => s.id === spec.id ? response.data.spec : s));
                alert(`✅ ${response.data.message}`);
            } else {
                alert(`⚠️ ${response.data.message}`);
            }
        } catch (error: any) {
            console.error('Re-extract failed:', error);
            alert('Failed to re-extract: ' + (error.response?.data?.message || error.message));
        } finally {
            setExtractingId(null);
        }
    };

    const handleToggleVerified = async (spec: CarSpec) => {
        try {
            const newVerified = !spec.is_verified;
            const response = await api.patch(`/car-specifications/${spec.id}/`, {
                is_verified: newVerified,
                verified_at: newVerified ? new Date().toISOString() : null,
            });
            setSpecs(specs.map(s => s.id === spec.id ? response.data : s));
        } catch (error) {
            console.error('Failed to toggle verified:', error);
            alert('Failed to update verification status');
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);

        try {
            if (editingSpec) {
                const response = await api.patch(`/car-specifications/${editingSpec.id}/`, formData);
                setSpecs(specs.map(s => s.id === editingSpec.id ? response.data : s));
            }
            setShowModal(false);
        } catch (error: any) {
            console.error('Failed to save car spec:', error);
            alert('Failed to save: ' + (error.response?.data?.detail || error.message));
        } finally {
            setSaving(false);
        }
    };

    // All unique brands for the filter
    const allBrands = useMemo(() => {
        const brandCounts: Record<string, number> = {};
        specs.forEach(s => {
            const b = s.make || 'Unknown';
            brandCounts[b] = (brandCounts[b] || 0) + 1;
        });
        return Object.entries(brandCounts)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([name, count]) => ({ name, count }));
    }, [specs]);

    // Stats
    const verifiedCount = specs.filter(s => s.is_verified).length;
    const unverifiedCount = specs.length - verifiedCount;

    // Filtered specs
    const filteredSpecs = useMemo(() => {
        return specs.filter(spec => {
            if (selectedBrand !== 'all' && (spec.make || 'Unknown') !== selectedBrand) return false;
            if (verifiedFilter === 'verified' && !spec.is_verified) return false;
            if (verifiedFilter === 'unverified' && spec.is_verified) return false;
            if (!search) return true;
            const q = search.toLowerCase();
            return (
                spec.make?.toLowerCase().includes(q) ||
                spec.model?.toLowerCase().includes(q) ||
                spec.trim?.toLowerCase().includes(q) ||
                spec.engine?.toLowerCase().includes(q) ||
                spec.article_title?.toLowerCase().includes(q) ||
                spec.model_name?.toLowerCase().includes(q)
            );
        });
    }, [specs, selectedBrand, verifiedFilter, search]);

    // Pagination
    const totalPages = Math.max(1, Math.ceil(filteredSpecs.length / PAGE_SIZE));
    const currentPage = Math.min(page, totalPages);
    const paginatedSpecs = filteredSpecs.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

    useEffect(() => {
        setPage(1);
    }, [search, selectedBrand, verifiedFilter]);

    return (
        <div>
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
                <div>
                    <h1 className="text-2xl sm:text-3xl font-black text-gray-950">Car Specifications</h1>
                    <p className="text-sm text-gray-500 mt-1">
                        {filteredSpecs.length} of {specs.length} specs
                        {selectedBrand !== 'all' && <span className="text-indigo-600 font-semibold"> • {selectedBrand}</span>}
                    </p>
                </div>

                {/* Verified stats */}
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5 bg-green-50 text-green-700 px-3 py-1.5 rounded-lg text-sm font-semibold border border-green-200">
                        <ShieldCheck size={16} />
                        {verifiedCount} verified
                    </div>
                    <div className="flex items-center gap-1.5 bg-amber-50 text-amber-700 px-3 py-1.5 rounded-lg text-sm font-semibold border border-amber-200">
                        <Circle size={16} />
                        {unverifiedCount} unverified
                    </div>
                </div>
            </div>

            {/* Filters bar */}
            <div className="flex flex-col sm:flex-row gap-3 mb-6">
                {/* Search */}
                <div className="relative flex-1">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                    <input
                        type="text"
                        placeholder="Search model, engine, article..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-full pl-11 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-gray-900 font-medium text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                    />
                </div>

                {/* Brand filter */}
                <div className="relative">
                    <Filter className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
                    <select
                        value={selectedBrand}
                        onChange={(e) => setSelectedBrand(e.target.value)}
                        className="pl-9 pr-8 py-2.5 bg-white border border-gray-200 rounded-xl text-gray-900 font-medium text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none appearance-none cursor-pointer min-w-[180px]"
                    >
                        <option value="all">All Brands ({specs.length})</option>
                        {allBrands.map(b => (
                            <option key={b.name} value={b.name}>
                                {b.name} ({b.count})
                            </option>
                        ))}
                    </select>
                    <ChevronRight className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none rotate-90" size={14} />
                </div>

                {/* Verified filter */}
                <div className="flex rounded-xl border border-gray-200 overflow-hidden">
                    {(['all', 'verified', 'unverified'] as const).map(f => (
                        <button
                            key={f}
                            onClick={() => setVerifiedFilter(f)}
                            className={`px-4 py-2.5 text-sm font-medium transition-colors ${verifiedFilter === f
                                ? 'bg-indigo-600 text-white'
                                : 'bg-white text-gray-600 hover:bg-gray-50'
                                } ${f !== 'all' ? 'border-l border-gray-200' : ''}`}
                        >
                            {f === 'all' ? 'All' : f === 'verified' ? '✓ Verified' : '○ Unverified'}
                        </button>
                    ))}
                </div>
            </div>

            <div className="bg-white rounded-xl shadow-md overflow-hidden">
                {loading ? (
                    <div className="p-12 text-center">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
                        <p className="text-gray-600 mt-4 font-medium">Loading car specifications...</p>
                    </div>
                ) : filteredSpecs.length === 0 ? (
                    <div className="p-12 text-center">
                        <div className="text-6xl mb-4">🚗</div>
                        <p className="text-gray-700 font-semibold text-lg">
                            {search || selectedBrand !== 'all' || verifiedFilter !== 'all' ? 'No specs match filters' : 'No car specifications found'}
                        </p>
                        <p className="text-gray-500 mt-2">
                            {search || selectedBrand !== 'all' || verifiedFilter !== 'all'
                                ? 'Try changing your search or filters'
                                : 'Specs are auto-created when articles are generated with car data'}
                        </p>
                    </div>
                ) : (
                    <>
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-gray-50 border-b border-gray-200">
                                    <tr>
                                        <th className="px-3 py-3 text-center text-xs font-bold text-gray-900 uppercase tracking-wider w-12">✓</th>
                                        <th className="px-4 py-3 text-left text-xs font-bold text-gray-900 uppercase tracking-wider">Brand / Model</th>
                                        <th className="px-4 py-3 text-left text-xs font-bold text-gray-900 uppercase tracking-wider hidden md:table-cell">Engine</th>
                                        <th className="px-4 py-3 text-left text-xs font-bold text-gray-900 uppercase tracking-wider hidden lg:table-cell">Power</th>
                                        <th className="px-4 py-3 text-left text-xs font-bold text-gray-900 uppercase tracking-wider hidden lg:table-cell">Price</th>
                                        <th className="px-4 py-3 text-left text-xs font-bold text-gray-900 uppercase tracking-wider hidden xl:table-cell">Article</th>
                                        <th className="px-4 py-3 text-right text-xs font-bold text-gray-900 uppercase tracking-wider">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-100">
                                    {paginatedSpecs.map((spec) => (
                                        <tr key={spec.id} className={`hover:bg-indigo-50/50 transition-colors ${spec.is_verified ? 'bg-green-50/30' : ''}`}>
                                            <td className="px-3 py-3 text-center">
                                                <button
                                                    onClick={() => handleToggleVerified(spec)}
                                                    className={`p-1 rounded-lg transition-all ${spec.is_verified
                                                        ? 'text-green-600 hover:text-green-700 hover:bg-green-100'
                                                        : 'text-gray-300 hover:text-amber-500 hover:bg-amber-50'
                                                        }`}
                                                    title={spec.is_verified ? `Verified${spec.verified_at ? ` on ${new Date(spec.verified_at).toLocaleDateString()}` : ''}` : 'Click to mark as verified'}
                                                >
                                                    {spec.is_verified ? <CheckCircle size={20} /> : <Circle size={20} />}
                                                </button>
                                            </td>
                                            <td className="px-4 py-3">
                                                <div className="font-bold text-gray-900">{spec.make || '—'} {spec.model || '—'}</div>
                                                {spec.trim && spec.trim !== 'Not specified' && (
                                                    <div className="text-xs text-gray-500 mt-0.5">{spec.trim}</div>
                                                )}
                                            </td>
                                            <td className="px-4 py-3 hidden md:table-cell">
                                                <span className="text-sm text-gray-700">{spec.engine || '—'}</span>
                                            </td>
                                            <td className="px-4 py-3 hidden lg:table-cell">
                                                <span className="text-sm font-semibold text-gray-800">{spec.horsepower ? `${spec.horsepower} hp` : '—'}</span>
                                                {spec.torque && <div className="text-xs text-gray-400">{spec.torque}</div>}
                                            </td>
                                            <td className="px-4 py-3 hidden lg:table-cell">
                                                <span className="text-sm font-semibold text-indigo-700">{spec.price || '—'}</span>
                                            </td>
                                            <td className="px-4 py-3 hidden xl:table-cell">
                                                <Link
                                                    href={`/admin/articles/${spec.article}/edit`}
                                                    className="text-sm text-indigo-600 hover:text-indigo-800 hover:underline line-clamp-1"
                                                    title={spec.article_title}
                                                >
                                                    {spec.article_title?.slice(0, 40)}{spec.article_title?.length > 40 ? '...' : ''}
                                                </Link>
                                            </td>
                                            <td className="px-4 py-3 text-right">
                                                <div className="flex items-center justify-end gap-1">
                                                    <button
                                                        onClick={() => handleReExtract(spec)}
                                                        disabled={extractingId === spec.id}
                                                        className="p-2 text-gray-500 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors disabled:opacity-50"
                                                        title="Re-extract specs from article (AI + regex)"
                                                    >
                                                        <RefreshCw size={16} className={extractingId === spec.id ? 'animate-spin' : ''} />
                                                    </button>
                                                    <button
                                                        onClick={() => handleEdit(spec)}
                                                        className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                                        title="Edit"
                                                    >
                                                        <Edit size={16} />
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(spec.id)}
                                                        className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                                        title="Delete"
                                                    >
                                                        <Trash2 size={16} />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        {/* Pagination */}
                        {totalPages > 1 && (
                            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 bg-gray-50/50">
                                <span className="text-sm text-gray-500">
                                    {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, filteredSpecs.length)} of {filteredSpecs.length}
                                </span>
                                <div className="flex items-center gap-1">
                                    <button
                                        onClick={() => setPage(p => Math.max(1, p - 1))}
                                        disabled={currentPage <= 1}
                                        className="p-2 rounded-lg text-gray-600 hover:bg-gray-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                                    >
                                        <ChevronLeft size={18} />
                                    </button>
                                    {Array.from({ length: totalPages }, (_, i) => i + 1)
                                        .filter(p => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 1)
                                        .reduce<(number | string)[]>((acc, p, i, arr) => {
                                            if (i > 0 && p - (arr[i - 1] as number) > 1) acc.push('...');
                                            acc.push(p);
                                            return acc;
                                        }, [])
                                        .map((p, i) =>
                                            typeof p === 'string' ? (
                                                <span key={`dots-${i}`} className="px-2 text-gray-400">…</span>
                                            ) : (
                                                <button
                                                    key={p}
                                                    onClick={() => setPage(p)}
                                                    className={`w-9 h-9 rounded-lg text-sm font-bold transition-colors ${p === currentPage
                                                        ? 'bg-indigo-600 text-white'
                                                        : 'text-gray-600 hover:bg-gray-200'
                                                        }`}
                                                >
                                                    {p}
                                                </button>
                                            )
                                        )}
                                    <button
                                        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                        disabled={currentPage >= totalPages}
                                        className="p-2 rounded-lg text-gray-600 hover:bg-gray-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                                    >
                                        <ChevronRight size={18} />
                                    </button>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </div>

            {/* Edit Modal */}
            {showModal && editingSpec && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between p-6 border-b border-gray-100 sticky top-0 bg-white z-10">
                            <div>
                                <h2 className="text-xl font-black text-gray-950">Edit Specification</h2>
                                <p className="text-sm text-gray-500 mt-1">{editingSpec.article_title}</p>
                            </div>
                            <button
                                onClick={() => setShowModal(false)}
                                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                            >
                                <X size={24} />
                            </button>
                        </div>

                        <form onSubmit={handleSubmit} className="p-6 space-y-5">
                            {/* Brand & Model Row */}
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                <div>
                                    <label className="block text-sm font-bold text-gray-900 mb-1.5">Brand *</label>
                                    <input
                                        type="text"
                                        value={formData.make}
                                        onChange={(e) => setFormData({ ...formData, make: e.target.value })}
                                        className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
                                        placeholder="e.g. BYD"
                                        required
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-gray-900 mb-1.5">Model *</label>
                                    <input
                                        type="text"
                                        value={formData.model}
                                        onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                                        className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
                                        placeholder="e.g. Qin L"
                                        required
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-gray-900 mb-1.5">Trim</label>
                                    <input
                                        type="text"
                                        value={formData.trim}
                                        onChange={(e) => setFormData({ ...formData, trim: e.target.value })}
                                        className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
                                        placeholder="e.g. DM-i"
                                    />
                                </div>
                            </div>

                            {/* Engine */}
                            <div>
                                <label className="block text-sm font-bold text-gray-900 mb-1.5">Engine</label>
                                <input
                                    type="text"
                                    value={formData.engine}
                                    onChange={(e) => setFormData({ ...formData, engine: e.target.value })}
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
                                    placeholder="e.g. 1.5L Turbocharged PHEV"
                                />
                            </div>

                            {/* Performance Row */}
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                                <div>
                                    <label className="block text-sm font-bold text-gray-900 mb-1.5">Horsepower</label>
                                    <input
                                        type="text"
                                        value={formData.horsepower}
                                        onChange={(e) => setFormData({ ...formData, horsepower: e.target.value })}
                                        className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
                                        placeholder="e.g. 305 hp"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-gray-900 mb-1.5">Torque</label>
                                    <input
                                        type="text"
                                        value={formData.torque}
                                        onChange={(e) => setFormData({ ...formData, torque: e.target.value })}
                                        className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
                                        placeholder="e.g. 400 Nm"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-gray-900 mb-1.5">0-60 mph</label>
                                    <input
                                        type="text"
                                        value={formData.zero_to_sixty}
                                        onChange={(e) => setFormData({ ...formData, zero_to_sixty: e.target.value })}
                                        className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
                                        placeholder="e.g. 5.9s"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-gray-900 mb-1.5">Top Speed</label>
                                    <input
                                        type="text"
                                        value={formData.top_speed}
                                        onChange={(e) => setFormData({ ...formData, top_speed: e.target.value })}
                                        className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
                                        placeholder="e.g. 250 km/h"
                                    />
                                </div>
                            </div>

                            {/* Drivetrain */}
                            <div>
                                <label className="block text-sm font-bold text-gray-900 mb-1.5">Drivetrain</label>
                                <select
                                    value={formData.drivetrain}
                                    onChange={(e) => setFormData({ ...formData, drivetrain: e.target.value })}
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium bg-white"
                                >
                                    <option value="">— Select —</option>
                                    <option value="AWD">AWD (All-Wheel Drive)</option>
                                    <option value="FWD">FWD (Front-Wheel Drive)</option>
                                    <option value="RWD">RWD (Rear-Wheel Drive)</option>
                                    <option value="4WD">4WD (Four-Wheel Drive)</option>
                                </select>
                            </div>

                            {/* Price & Release */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-bold text-gray-900 mb-1.5">Price</label>
                                    <input
                                        type="text"
                                        value={formData.price}
                                        onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                                        className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
                                        placeholder="e.g. $35,990"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-gray-900 mb-1.5">Release Date</label>
                                    <input
                                        type="text"
                                        value={formData.release_date}
                                        onChange={(e) => setFormData({ ...formData, release_date: e.target.value })}
                                        className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
                                        placeholder="e.g. Q2 2026"
                                    />
                                </div>
                            </div>

                            <div className="flex gap-4 pt-2">
                                <button
                                    type="submit"
                                    disabled={saving}
                                    className="flex-1 bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-3 rounded-lg font-bold hover:from-indigo-700 hover:to-purple-700 transition-all shadow-md disabled:opacity-50"
                                >
                                    {saving ? 'Saving...' : 'Save Changes'}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setShowModal(false)}
                                    className="px-6 py-3 bg-gray-200 text-gray-800 rounded-lg font-bold hover:bg-gray-300 transition-colors"
                                >
                                    Cancel
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

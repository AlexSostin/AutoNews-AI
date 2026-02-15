'use client';

import { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, X, ArrowRightLeft, AlertCircle } from 'lucide-react';
import api from '@/lib/api';

interface BrandAlias {
    id: number;
    alias: string;
    canonical_name: string;
    created_at: string;
}

export default function BrandAliasesPage() {
    const [aliases, setAliases] = useState<BrandAlias[]>([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editing, setEditing] = useState<BrandAlias | null>(null);
    const [formData, setFormData] = useState({ alias: '', canonical_name: '' });
    const [error, setError] = useState('');

    useEffect(() => {
        fetchAliases();
    }, []);

    const fetchAliases = async () => {
        try {
            setLoading(true);
            const res = await api.get('/brand-aliases/', { params: { _t: Date.now() } });
            const data = Array.isArray(res.data) ? res.data : res.data.results || [];
            setAliases(data);
        } catch (err) {
            console.error('Failed to fetch brand aliases:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = () => {
        setEditing(null);
        setFormData({ alias: '', canonical_name: '' });
        setError('');
        setShowModal(true);
    };

    const handleEdit = (alias: BrandAlias) => {
        setEditing(alias);
        setFormData({ alias: alias.alias, canonical_name: alias.canonical_name });
        setError('');
        setShowModal(true);
    };

    const handleDelete = async (id: number) => {
        if (!confirm('Are you sure you want to delete this alias?')) return;
        try {
            await api.delete(`/brand-aliases/${id}/`);
            setAliases(aliases.filter(a => a.id !== id));
        } catch {
            alert('Failed to delete alias');
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (!formData.alias.trim() || !formData.canonical_name.trim()) {
            setError('Both fields are required');
            return;
        }

        try {
            if (editing) {
                const res = await api.put(`/brand-aliases/${editing.id}/`, formData);
                setAliases(aliases.map(a => a.id === editing.id ? res.data : a));
            } else {
                const res = await api.post('/brand-aliases/', formData);
                setAliases([...aliases, res.data]);
            }
            setShowModal(false);
        } catch (err: any) {
            const detail = err.response?.data?.alias?.[0] || err.response?.data?.detail || err.message;
            setError(`Failed to save: ${detail}`);
        }
    };

    // Group aliases by canonical_name
    const grouped = aliases.reduce((acc, alias) => {
        if (!acc[alias.canonical_name]) {
            acc[alias.canonical_name] = [];
        }
        acc[alias.canonical_name].push(alias);
        return acc;
    }, {} as Record<string, BrandAlias[]>);

    const sortedBrands = Object.keys(grouped).sort();

    return (
        <div className="p-6 max-w-4xl mx-auto min-h-screen bg-gray-50">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                <div>
                    <h1 className="text-2xl sm:text-3xl font-black text-gray-950">Brand Aliases</h1>
                    <p className="text-gray-500 text-sm mt-1">
                        Map brand name variations to canonical names. Applied automatically during data sync.
                    </p>
                </div>
                <button
                    onClick={handleCreate}
                    className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-4 py-2.5 rounded-lg font-bold hover:from-indigo-700 hover:to-purple-700 transition-all flex items-center justify-center gap-2 shadow-md"
                >
                    <Plus size={20} />
                    <span>Add Alias</span>
                </button>
            </div>

            {/* How it works */}
            <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 mb-6">
                <div className="flex items-start gap-3">
                    <AlertCircle size={20} className="text-indigo-600 mt-0.5 flex-shrink-0" />
                    <div className="text-sm text-indigo-800">
                        <strong>How it works:</strong> When AI extracts a brand name, the system checks this table.
                        If the extracted name matches an alias, it&apos;s automatically replaced with the canonical name.
                        <br />
                        <span className="text-indigo-600">Example: AI extracts &quot;DongFeng VOYAH&quot; → stored as &quot;VOYAH&quot;</span>
                    </div>
                </div>
            </div>

            {loading ? (
                <div className="bg-white rounded-lg shadow-md p-12 text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
                    <p className="text-gray-600 mt-4 font-medium">Loading aliases...</p>
                </div>
            ) : aliases.length === 0 ? (
                <div className="bg-white rounded-lg shadow-md p-12 text-center">
                    <ArrowRightLeft size={48} className="mx-auto text-gray-300 mb-4" />
                    <p className="text-gray-600 font-medium">No brand aliases configured yet.</p>
                    <p className="text-sm text-gray-400 mt-1">Add aliases to automatically normalize brand names during extraction.</p>
                </div>
            ) : (
                <div className="space-y-4">
                    {sortedBrands.map(brand => (
                        <div key={brand} className="bg-white rounded-xl shadow-md overflow-hidden">
                            <div className="bg-gradient-to-r from-gray-50 to-white px-6 py-4 border-b border-gray-100">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center">
                                        <ArrowRightLeft size={16} className="text-indigo-600" />
                                    </div>
                                    <h2 className="text-lg font-black text-gray-900">{brand}</h2>
                                    <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-bold">
                                        {grouped[brand].length} alias{grouped[brand].length !== 1 ? 'es' : ''}
                                    </span>
                                </div>
                            </div>
                            <div className="divide-y divide-gray-50">
                                {grouped[brand].map(alias => (
                                    <div key={alias.id} className="px-6 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors group">
                                        <div className="flex items-center gap-3">
                                            <code className="text-sm font-semibold text-red-600 bg-red-50 px-2 py-1 rounded">
                                                {alias.alias}
                                            </code>
                                            <span className="text-gray-400">→</span>
                                            <code className="text-sm font-semibold text-green-700 bg-green-50 px-2 py-1 rounded">
                                                {alias.canonical_name}
                                            </code>
                                        </div>
                                        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <button
                                                onClick={() => handleEdit(alias)}
                                                className="p-1.5 text-gray-600 hover:text-blue-600 hover:bg-blue-100 rounded-lg transition-colors"
                                            >
                                                <Edit size={14} />
                                            </button>
                                            <button
                                                onClick={() => handleDelete(alias.id)}
                                                className="p-1.5 text-gray-600 hover:text-red-600 hover:bg-red-100 rounded-lg transition-colors"
                                            >
                                                <Trash2 size={14} />
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full p-6">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-2xl font-black text-gray-950">
                                {editing ? 'Edit Alias' : 'New Alias'}
                            </h2>
                            <button onClick={() => setShowModal(false)} className="p-2 hover:bg-gray-100 rounded-lg">
                                <X size={24} />
                            </button>
                        </div>

                        {error && (
                            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">
                                {error}
                            </div>
                        )}

                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <label className="block text-sm font-bold text-gray-900 mb-2">
                                    Alias (what AI produces) *
                                </label>
                                <input
                                    type="text"
                                    value={formData.alias}
                                    onChange={(e) => setFormData({ ...formData, alias: e.target.value })}
                                    placeholder="e.g. DongFeng VOYAH"
                                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-950"
                                    required
                                />
                                <p className="text-xs text-gray-400 mt-1">The brand name as AI might extract it</p>
                            </div>

                            <div className="flex items-center justify-center py-2">
                                <div className="flex items-center gap-2 text-gray-400">
                                    <div className="h-px w-12 bg-gray-200"></div>
                                    <ArrowRightLeft size={16} />
                                    <span className="text-xs font-bold uppercase tracking-wider">maps to</span>
                                    <div className="h-px w-12 bg-gray-200"></div>
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-bold text-gray-900 mb-2">
                                    Canonical Name (correct brand) *
                                </label>
                                <input
                                    type="text"
                                    value={formData.canonical_name}
                                    onChange={(e) => setFormData({ ...formData, canonical_name: e.target.value })}
                                    placeholder="e.g. VOYAH"
                                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-950"
                                    required
                                />
                                <p className="text-xs text-gray-400 mt-1">The correct brand name that will be stored</p>
                            </div>

                            <div className="flex gap-4 pt-4">
                                <button
                                    type="submit"
                                    className="flex-1 bg-indigo-600 text-white py-3 rounded-lg font-bold hover:bg-indigo-700 transition-colors"
                                >
                                    {editing ? 'Save Changes' : 'Create Alias'}
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

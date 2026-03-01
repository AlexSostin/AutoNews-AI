'use client';

import { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, X, Merge, Eye, EyeOff, Search, RefreshCw, ChevronDown, Globe } from 'lucide-react';
import api from '@/lib/api';

interface Brand {
    id: number;
    name: string;
    slug: string;
    logo: string | null;
    country: string;
    description: string;
    sort_order: number;
    is_visible: boolean;
    parent: number | null;
    parent_name: string | null;
    sub_brands: { id: number; name: string; slug: string }[];
    article_count: number;
    model_count: number;
    image: string | null;
    created_at: string;
    updated_at: string;
}

export default function BrandsPage() {
    const [brands, setBrands] = useState<Brand[]>([]);
    const [loading, setLoading] = useState(true);
    const [showEditModal, setShowEditModal] = useState(false);
    const [showMergeModal, setShowMergeModal] = useState(false);
    const [editing, setEditing] = useState<Brand | null>(null);
    const [mergeTarget, setMergeTarget] = useState<Brand | null>(null);
    const [mergeSourceId, setMergeSourceId] = useState<number | null>(null);
    const [search, setSearch] = useState('');
    const [error, setError] = useState('');
    const [syncing, setSyncing] = useState(false);
    const [formData, setFormData] = useState({
        name: '',
        country: '',
        description: '',
        sort_order: 0,
        is_visible: true,
        parent: null as number | null,
    });

    useEffect(() => {
        fetchBrands();
    }, []);

    const fetchBrands = async () => {
        try {
            setLoading(true);
            const res = await api.get('/admin/brands/', { params: { _t: Date.now() } });
            const data = Array.isArray(res.data) ? res.data : res.data.results || [];
            setBrands(data);
        } catch (err) {
            console.error('Failed to fetch brands:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = () => {
        setEditing(null);
        setFormData({ name: '', country: '', description: '', sort_order: 0, is_visible: true, parent: null });
        setError('');
        setShowEditModal(true);
    };

    const handleEdit = (brand: Brand) => {
        setEditing(brand);
        setFormData({
            name: brand.name,
            country: brand.country,
            description: brand.description,
            sort_order: brand.sort_order,
            is_visible: brand.is_visible,
            parent: brand.parent,
        });
        setError('');
        setShowEditModal(true);
    };

    const handleDelete = async (brand: Brand) => {
        if (!confirm(`Delete brand "${brand.name}"? This won't delete articles, but they'll no longer appear under this brand in the catalog.`)) return;
        try {
            await api.delete(`/admin/brands/${brand.id}/`);
            setBrands(brands.filter(b => b.id !== brand.id));
        } catch {
            alert('Failed to delete brand');
        }
    };

    const handleToggleVisibility = async (brand: Brand) => {
        try {
            const res = await api.patch(`/admin/brands/${brand.id}/`, { is_visible: !brand.is_visible });
            setBrands(brands.map(b => b.id === brand.id ? { ...b, ...res.data } : b));
        } catch {
            alert('Failed to toggle visibility');
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (!formData.name.trim()) {
            setError('Brand name is required');
            return;
        }

        try {
            if (editing) {
                const res = await api.patch(`/admin/brands/${editing.id}/`, formData);
                setBrands(brands.map(b => b.id === editing.id ? { ...b, ...res.data } : b));
            } else {
                const res = await api.post('/admin/brands/', formData);
                setBrands([...brands, res.data]);
            }
            setShowEditModal(false);
        } catch (err: any) {
            const data = err.response?.data;
            let detail = '';
            if (data) {
                // DRF returns field-level errors as { field: ["error"] }
                const fieldErrors = Object.entries(data)
                    .filter(([, v]) => Array.isArray(v))
                    .map(([k, v]) => `${k}: ${(v as string[]).join(', ')}`)
                    .join('; ');
                detail = fieldErrors || data.detail || data.error || JSON.stringify(data);
            } else {
                detail = err.message;
            }
            setError(`Failed to save: ${detail}`);
        }
    };

    const handleMergeStart = (target: Brand) => {
        setMergeTarget(target);
        setMergeSourceId(null);
        setError('');
        setShowMergeModal(true);
    };

    const handleMerge = async () => {
        if (!mergeTarget || !mergeSourceId) return;
        const source = brands.find(b => b.id === mergeSourceId);
        if (!source) return;

        if (!confirm(`Merge "${source.name}" into "${mergeTarget.name}"?\n\nThis will:\n• Move all articles from "${source.name}" to "${mergeTarget.name}"\n• Create a brand alias\n• Delete "${source.name}"\n\nThis action cannot be undone.`)) return;

        try {
            await api.post(`/admin/brands/${mergeTarget.id}/merge/`, { source_brand_id: mergeSourceId });
            setShowMergeModal(false);
            fetchBrands(); // Reload to get updated counts
        } catch (err: any) {
            const detail = err.response?.data?.error || err.message;
            setError(`Merge failed: ${detail}`);
        }
    };

    const handleSync = async () => {
        setSyncing(true);
        try {
            const res = await api.post('/admin/brands/sync/');
            if (res.data.total_created > 0) {
                alert(`Created ${res.data.total_created} new brand(s): ${res.data.created_brands.join(', ')}`);
                fetchBrands();
            } else {
                alert('All brands are already synced!');
            }
        } catch (err) {
            alert('Sync failed');
        } finally {
            setSyncing(false);
        }
    };

    // Filter brands by search
    const filteredBrands = brands.filter(b =>
        b.name.toLowerCase().includes(search.toLowerCase()) ||
        b.country.toLowerCase().includes(search.toLowerCase())
    );

    // Group: parents first, then sub-brands underneath
    const topBrands = filteredBrands.filter(b => b.parent === null);
    const subBrands = filteredBrands.filter(b => b.parent !== null);

    return (
        <div className="p-4 sm:p-6 max-w-6xl mx-auto min-h-screen bg-gray-50">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                <div>
                    <h1 className="text-2xl sm:text-3xl font-black text-gray-950">Brand Management</h1>
                    <p className="text-gray-500 text-sm mt-1">
                        Manage car brands in the catalog. Edit, merge, and control visibility.
                    </p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={handleSync}
                        disabled={syncing}
                        className="bg-white border border-gray-300 text-gray-700 px-3 py-2.5 rounded-lg font-bold hover:bg-gray-50 transition-all flex items-center gap-2 text-sm"
                    >
                        <RefreshCw size={16} className={syncing ? 'animate-spin' : ''} />
                        <span>Sync</span>
                    </button>
                    <button
                        onClick={handleCreate}
                        className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-4 py-2.5 rounded-lg font-bold hover:from-indigo-700 hover:to-purple-700 transition-all flex items-center gap-2 shadow-md"
                    >
                        <Plus size={20} />
                        <span>Add Brand</span>
                    </button>
                </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
                <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
                    <div className="text-2xl font-black text-gray-900">{brands.length}</div>
                    <div className="text-xs text-gray-500 font-medium">Total Brands</div>
                </div>
                <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
                    <div className="text-2xl font-black text-green-600">{brands.filter(b => b.is_visible).length}</div>
                    <div className="text-xs text-gray-500 font-medium">Visible</div>
                </div>
                <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
                    <div className="text-2xl font-black text-indigo-600">{brands.reduce((s, b) => s + b.model_count, 0)}</div>
                    <div className="text-xs text-gray-500 font-medium">Total Models</div>
                </div>
                <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
                    <div className="text-2xl font-black text-purple-600">{brands.reduce((s, b) => s + b.article_count, 0)}</div>
                    <div className="text-xs text-gray-500 font-medium">Total Articles</div>
                </div>
            </div>

            {/* Search */}
            <div className="relative mb-6">
                <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                    type="text"
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    placeholder="Search brands..."
                    className="w-full pl-10 pr-4 py-3 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-gray-900"
                />
            </div>

            {/* Brands Table */}
            {loading ? (
                <div className="bg-white rounded-xl shadow-md p-12 text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
                    <p className="text-gray-600 mt-4 font-medium">Loading brands...</p>
                </div>
            ) : filteredBrands.length === 0 ? (
                <div className="bg-white rounded-xl shadow-md p-12 text-center">
                    <Globe size={48} className="mx-auto text-gray-300 mb-4" />
                    <p className="text-gray-600 font-medium">No brands found.</p>
                    <p className="text-sm text-gray-400 mt-1">Click &quot;Sync&quot; to import brands from articles, or add one manually.</p>
                </div>
            ) : (
                <div className="bg-white rounded-xl shadow-md overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="bg-gray-50 border-b border-gray-200">
                                    <th className="text-left px-4 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Brand</th>
                                    <th className="text-left px-4 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider hidden sm:table-cell">Country</th>
                                    <th className="text-center px-4 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Models</th>
                                    <th className="text-center px-4 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Articles</th>
                                    <th className="text-center px-4 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Status</th>
                                    <th className="text-center px-4 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider hidden md:table-cell">Parent</th>
                                    <th className="text-right px-4 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {topBrands.map(brand => (
                                    <BrandRow
                                        key={brand.id}
                                        brand={brand}
                                        allBrands={brands}
                                        onEdit={handleEdit}
                                        onDelete={handleDelete}
                                        onToggleVisibility={handleToggleVisibility}
                                        onMerge={handleMergeStart}
                                        isSubBrand={false}
                                    />
                                ))}
                                {subBrands.map(brand => (
                                    <BrandRow
                                        key={brand.id}
                                        brand={brand}
                                        allBrands={brands}
                                        onEdit={handleEdit}
                                        onDelete={handleDelete}
                                        onToggleVisibility={handleToggleVisibility}
                                        onMerge={handleMergeStart}
                                        isSubBrand={true}
                                    />
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Edit Modal */}
            {showEditModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-2xl font-black text-gray-950">
                                {editing ? `Edit: ${editing.name}` : 'New Brand'}
                            </h2>
                            <button onClick={() => setShowEditModal(false)} className="p-2 hover:bg-gray-100 rounded-lg">
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
                                <label className="block text-sm font-bold text-gray-900 mb-2">Name *</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                                    placeholder="e.g. BMW"
                                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-950"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-bold text-gray-900 mb-2">Country</label>
                                <input
                                    type="text"
                                    value={formData.country}
                                    onChange={e => setFormData({ ...formData, country: e.target.value })}
                                    placeholder="e.g. Germany"
                                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-950"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-bold text-gray-900 mb-2">Description</label>
                                <textarea
                                    value={formData.description}
                                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                                    placeholder="Brief brand description..."
                                    rows={3}
                                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-950 resize-none"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-bold text-gray-900 mb-2">Sort Order</label>
                                    <input
                                        type="number"
                                        value={formData.sort_order}
                                        onChange={e => setFormData({ ...formData, sort_order: parseInt(e.target.value) || 0 })}
                                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-950"
                                    />
                                    <p className="text-xs text-gray-400 mt-1">Higher = shown first (0 = auto)</p>
                                </div>

                                <div>
                                    <label className="block text-sm font-bold text-gray-900 mb-2">Parent Brand</label>
                                    <select
                                        value={formData.parent ?? ''}
                                        onChange={e => setFormData({ ...formData, parent: e.target.value ? parseInt(e.target.value) : null })}
                                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-950 bg-white"
                                    >
                                        <option value="">None (top-level)</option>
                                        {brands.filter(b => b.id !== editing?.id).map(b => (
                                            <option key={b.id} value={b.id}>{b.name}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <div className="flex items-center gap-3 py-2">
                                <label className="relative inline-flex items-center cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={formData.is_visible}
                                        onChange={e => setFormData({ ...formData, is_visible: e.target.checked })}
                                        className="sr-only peer"
                                    />
                                    <div className="w-11 h-6 bg-gray-300 rounded-full peer peer-checked:bg-green-500 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
                                </label>
                                <span className="text-sm font-bold text-gray-900">Visible in catalog</span>
                            </div>

                            <div className="flex gap-4 pt-4">
                                <button
                                    type="submit"
                                    className="flex-1 bg-indigo-600 text-white py-3 rounded-lg font-bold hover:bg-indigo-700 transition-colors"
                                >
                                    {editing ? 'Save Changes' : 'Create Brand'}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setShowEditModal(false)}
                                    className="px-6 py-3 bg-gray-200 text-gray-800 rounded-lg font-bold hover:bg-gray-300 transition-colors"
                                >
                                    Cancel
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Merge Modal */}
            {showMergeModal && mergeTarget && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full p-6">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-2xl font-black text-gray-950">Merge into {mergeTarget.name}</h2>
                            <button onClick={() => setShowMergeModal(false)} className="p-2 hover:bg-gray-100 rounded-lg">
                                <X size={24} />
                            </button>
                        </div>

                        {error && (
                            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">
                                {error}
                            </div>
                        )}

                        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6 text-sm text-amber-800">
                            <strong>⚠️ This action cannot be undone.</strong> All articles from the selected brand will be moved to <strong>{mergeTarget.name}</strong>, and the source brand will be deleted.
                        </div>

                        <div>
                            <label className="block text-sm font-bold text-gray-900 mb-2">
                                Select brand to merge INTO {mergeTarget.name}:
                            </label>
                            <select
                                value={mergeSourceId ?? ''}
                                onChange={e => setMergeSourceId(e.target.value ? parseInt(e.target.value) : null)}
                                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-950 bg-white"
                            >
                                <option value="">Select a brand...</option>
                                {brands.filter(b => b.id !== mergeTarget.id).map(b => (
                                    <option key={b.id} value={b.id}>
                                        {b.name} ({b.article_count} articles, {b.model_count} models)
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="flex gap-4 pt-6">
                            <button
                                onClick={handleMerge}
                                disabled={!mergeSourceId}
                                className="flex-1 bg-red-600 text-white py-3 rounded-lg font-bold hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Merge Now
                            </button>
                            <button
                                onClick={() => setShowMergeModal(false)}
                                className="px-6 py-3 bg-gray-200 text-gray-800 rounded-lg font-bold hover:bg-gray-300 transition-colors"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// Separate BrandRow component for clean table rows
function BrandRow({
    brand,
    allBrands,
    onEdit,
    onDelete,
    onToggleVisibility,
    onMerge,
    isSubBrand,
}: {
    brand: Brand;
    allBrands: Brand[];
    onEdit: (b: Brand) => void;
    onDelete: (b: Brand) => void;
    onToggleVisibility: (b: Brand) => void;
    onMerge: (b: Brand) => void;
    isSubBrand: boolean;
}) {
    return (
        <tr className={`hover:bg-gray-50 transition-colors ${!brand.is_visible ? 'opacity-50' : ''}`}>
            {/* Brand name + image */}
            <td className="px-4 py-3">
                <div className="flex items-center gap-3">
                    {isSubBrand && (
                        <span className="text-gray-300 text-lg pl-2">↳</span>
                    )}
                    <div className="w-10 h-10 rounded-lg overflow-hidden bg-gray-100 flex-shrink-0">
                        {brand.image ? (
                            <img src={brand.image} alt={brand.name} className="w-full h-full object-cover" />
                        ) : (
                            <div className="w-full h-full flex items-center justify-center text-gray-400 text-lg">🚗</div>
                        )}
                    </div>
                    <div>
                        <div className="font-bold text-gray-900">{brand.name}</div>
                        <div className="text-xs text-gray-400">/{brand.slug}</div>
                    </div>
                </div>
            </td>

            {/* Country */}
            <td className="px-4 py-3 hidden sm:table-cell">
                <span className="text-sm text-gray-600">{brand.country || '—'}</span>
            </td>

            {/* Models */}
            <td className="px-4 py-3 text-center">
                <span className="inline-flex items-center justify-center min-w-[2rem] px-2 py-0.5 bg-indigo-50 text-indigo-700 text-sm font-bold rounded-full">
                    {brand.model_count}
                </span>
            </td>

            {/* Articles */}
            <td className="px-4 py-3 text-center">
                <span className="inline-flex items-center justify-center min-w-[2rem] px-2 py-0.5 bg-purple-50 text-purple-700 text-sm font-bold rounded-full">
                    {brand.article_count}
                </span>
            </td>

            {/* Visibility toggle */}
            <td className="px-4 py-3 text-center">
                <button
                    onClick={() => onToggleVisibility(brand)}
                    className={`p-1.5 rounded-lg transition-colors ${brand.is_visible ? 'text-green-600 hover:bg-green-50' : 'text-gray-400 hover:bg-gray-100'}`}
                    title={brand.is_visible ? 'Visible — click to hide' : 'Hidden — click to show'}
                >
                    {brand.is_visible ? <Eye size={18} /> : <EyeOff size={18} />}
                </button>
            </td>

            {/* Parent */}
            <td className="px-4 py-3 text-center hidden md:table-cell">
                {brand.parent_name ? (
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full font-medium">
                        {brand.parent_name}
                    </span>
                ) : (
                    <span className="text-gray-300">—</span>
                )}
            </td>

            {/* Actions */}
            <td className="px-4 py-3 text-right">
                <div className="flex items-center justify-end gap-1">
                    <button
                        onClick={() => onEdit(brand)}
                        className="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="Edit"
                    >
                        <Edit size={16} />
                    </button>
                    <button
                        onClick={() => onMerge(brand)}
                        className="p-1.5 text-gray-500 hover:text-orange-600 hover:bg-orange-50 rounded-lg transition-colors"
                        title="Merge another brand into this one"
                    >
                        <Merge size={16} />
                    </button>
                    <button
                        onClick={() => onDelete(brand)}
                        className="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Delete"
                    >
                        <Trash2 size={16} />
                    </button>
                </div>
            </td>
        </tr>
    );
}

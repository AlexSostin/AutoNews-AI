'use client';

import { useState, useEffect } from 'react';
import {
    Megaphone,
    Plus,
    Trash2,
    Edit3,
    Loader2,
    Eye,
    EyeOff,
    MousePointerClick,
    BarChart3,
    X,
    Image as ImageIcon,
    Code,
    FileText,
    Calendar,
    ExternalLink,
    Info
} from 'lucide-react';
import { authenticatedFetch } from '@/lib/authenticatedFetch';
import { getApiUrl } from '@/lib/api';

interface AdPlacement {
    id: number;
    name: string;
    position: string;
    ad_type: string;
    image: string | null;
    link: string;
    alt_text: string;
    html_code: string;
    sponsor_name: string;
    sponsor_text: string;
    is_active: boolean;
    start_date: string | null;
    end_date: string | null;
    duration_preset: string;
    priority: number;
    target_pages: string;
    impressions: number;
    clicks: number;
    ctr: number;
    is_currently_active: boolean;
    created_at: string;
    updated_at: string;
}

const POSITION_OPTIONS = [
    { value: 'header', label: '🔝 Header Banner', size: '1200 × 200 px', hint: 'Full-width banner at top of page. Shown on Home, Articles list, and each article page.' },
    { value: 'sidebar', label: '📐 Sidebar', size: '300 × 250 px', hint: 'Right sidebar on Home (under Trending) and inside article pages. On mobile — moves below content.' },
    { value: 'between_articles', label: '📰 Between Articles', size: '728 × 90 px', hint: 'Full-width banner between every 6 article cards in the feed. Great for visibility.' },
    { value: 'after_content', label: '📄 After Content', size: '728 × 90 px', hint: 'Appears right after the article text, before YouTube video and comments.' },
    { value: 'footer', label: '🔻 Footer', size: '728 × 90 px', hint: 'Bottom of the page, before the footer. Shown on Home and Articles list.' },
];

const TYPE_OPTIONS = [
    { value: 'banner', label: 'Banner (Image + Link)', icon: ImageIcon },
    { value: 'html_code', label: 'HTML/JS Code (AdSense)', icon: Code },
    { value: 'sponsored', label: 'Sponsored Content', icon: FileText },
];

const DURATION_PRESETS = [
    { value: '1w', label: '1 Week', days: 7 },
    { value: '2w', label: '2 Weeks', days: 14 },
    { value: '1m', label: '1 Month', days: 30 },
    { value: '3m', label: '3 Months', days: 90 },
    { value: '6m', label: '6 Months', days: 180 },
    { value: '1y', label: '1 Year', days: 365 },
    { value: 'unlimited', label: '∞ Unlimited', days: 0 },
    { value: 'custom', label: '📅 Custom Dates', days: -1 },
];

const TARGET_OPTIONS = [
    { value: 'all', label: 'All Pages' },
    { value: 'home', label: 'Home Only' },
    { value: 'articles', label: 'Articles Only' },
    { value: 'cars', label: 'Cars Pages Only' },
];

const emptyForm: Omit<AdPlacement, 'id' | 'impressions' | 'clicks' | 'ctr' | 'is_currently_active' | 'created_at' | 'updated_at'> = {
    name: '',
    position: 'header',
    ad_type: 'banner',
    image: null,
    link: '',
    alt_text: '',
    html_code: '',
    sponsor_name: '',
    sponsor_text: '',
    is_active: true,
    start_date: null,
    end_date: null,
    duration_preset: 'unlimited',
    priority: 0,
    target_pages: 'all',
};

export default function AdsPage() {
    const [ads, setAds] = useState<AdPlacement[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [editingId, setEditingId] = useState<number | null>(null);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
    const [form, setForm] = useState(emptyForm);
    const [imageFile, setImageFile] = useState<File | null>(null);
    const [imagePreview, setImagePreview] = useState<string | null>(null);
    const [filterPosition, setFilterPosition] = useState<string>('all');

    useEffect(() => {
        fetchAds();
    }, []);

    const fetchAds = async () => {
        try {
            const response = await authenticatedFetch('/ads/');
            if (response.ok) {
                const data = await response.json();
                setAds(Array.isArray(data) ? data : data.results || []);
            }
        } catch (error) {
            console.error('Failed to fetch ads:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleDurationPreset = (preset: string) => {
        setForm(prev => ({ ...prev, duration_preset: preset }));

        if (preset === 'unlimited') {
            setForm(prev => ({ ...prev, start_date: null, end_date: null }));
        } else if (preset === 'custom') {
            // Keep existing dates or set defaults
            const now = new Date();
            const nextMonth = new Date(now);
            nextMonth.setMonth(nextMonth.getMonth() + 1);
            setForm(prev => ({
                ...prev,
                start_date: prev.start_date || now.toISOString().slice(0, 16),
                end_date: prev.end_date || nextMonth.toISOString().slice(0, 16),
            }));
        } else {
            const days = DURATION_PRESETS.find(p => p.value === preset)?.days || 30;
            const now = new Date();
            const end = new Date(now);
            end.setDate(end.getDate() + days);
            setForm(prev => ({
                ...prev,
                start_date: now.toISOString().slice(0, 16),
                end_date: end.toISOString().slice(0, 16),
            }));
        }
    };

    const handleEdit = (ad: AdPlacement) => {
        setEditingId(ad.id);
        setForm({
            name: ad.name,
            position: ad.position,
            ad_type: ad.ad_type,
            image: ad.image,
            link: ad.link,
            alt_text: ad.alt_text,
            html_code: ad.html_code,
            sponsor_name: ad.sponsor_name,
            sponsor_text: ad.sponsor_text,
            is_active: ad.is_active,
            start_date: ad.start_date ? ad.start_date.slice(0, 16) : null,
            end_date: ad.end_date ? ad.end_date.slice(0, 16) : null,
            duration_preset: ad.duration_preset || 'unlimited',
            priority: ad.priority,
            target_pages: ad.target_pages,
        });
        setImagePreview(ad.image);
        setShowForm(true);
    };

    const handleNewAd = () => {
        setEditingId(null);
        setForm({ ...emptyForm });
        setImageFile(null);
        setImagePreview(null);
        setShowForm(true);
    };

    const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setImageFile(file);
            setImagePreview(URL.createObjectURL(file));
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        setMessage(null);

        try {
            const formData = new FormData();
            formData.append('name', form.name);
            formData.append('position', form.position);
            formData.append('ad_type', form.ad_type);
            formData.append('link', form.link);
            formData.append('alt_text', form.alt_text);
            formData.append('html_code', form.html_code);
            formData.append('sponsor_name', form.sponsor_name);
            formData.append('sponsor_text', form.sponsor_text);
            formData.append('is_active', String(form.is_active));
            if (form.start_date) formData.append('start_date', new Date(form.start_date).toISOString());
            if (form.end_date) formData.append('end_date', new Date(form.end_date).toISOString());
            if (!form.start_date) formData.append('start_date', '');
            if (!form.end_date) formData.append('end_date', '');
            formData.append('duration_preset', form.duration_preset);
            formData.append('priority', String(form.priority));
            formData.append('target_pages', form.target_pages);

            if (imageFile) {
                formData.append('image', imageFile);
            }

            const url = editingId ? `/ads/${editingId}/` : '/ads/';
            const method = editingId ? 'PUT' : 'POST';

            const response = await authenticatedFetch(url, {
                method,
                body: formData,
                headers: {}, // Let browser set multipart boundary
            });

            if (response.ok) {
                setMessage({ type: 'success', text: editingId ? 'Ad updated!' : 'Ad created!' });
                setShowForm(false);
                setEditingId(null);
                setImageFile(null);
                setImagePreview(null);
                fetchAds();
            } else {
                const data = await response.json();
                setMessage({ type: 'error', text: JSON.stringify(data) });
            }
        } catch {
            setMessage({ type: 'error', text: 'An error occurred' });
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm('Are you sure you want to delete this ad placement?')) return;
        try {
            await authenticatedFetch(`/ads/${id}/`, { method: 'DELETE' });
            setAds(ads.filter(a => a.id !== id));
            setMessage({ type: 'success', text: 'Ad deleted' });
        } catch {
            setMessage({ type: 'error', text: 'Failed to delete' });
        }
    };

    const handleToggleActive = async (ad: AdPlacement) => {
        try {
            const response = await authenticatedFetch(`/ads/${ad.id}/`, {
                method: 'PATCH',
                body: JSON.stringify({ is_active: !ad.is_active }),
            });
            if (response.ok) {
                fetchAds();
            }
        } catch {
            setMessage({ type: 'error', text: 'Failed to toggle' });
        }
    };

    const filteredAds = filterPosition === 'all'
        ? ads
        : ads.filter(a => a.position === filterPosition);

    const totalImpressions = ads.reduce((sum, a) => sum + a.impressions, 0);
    const totalClicks = ads.reduce((sum, a) => sum + a.clicks, 0);
    const activeAds = ads.filter(a => a.is_currently_active).length;

    const getPositionLabel = (pos: string) => POSITION_OPTIONS.find(p => p.value === pos)?.label || pos;
    const getTypeIcon = (type: string) => {
        const opt = TYPE_OPTIONS.find(t => t.value === type);
        return opt ? opt.icon : ImageIcon;
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <Loader2 className="animate-spin text-orange-600" size={48} />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h1 className="text-2xl sm:text-3xl font-black text-gray-950 flex items-center gap-3">
                        <Megaphone className="text-orange-500" /> Ads / Sponsors
                    </h1>
                    <p className="text-gray-500 mt-1">Manage advertising placements across the site</p>
                </div>
                <button
                    onClick={handleNewAd}
                    className="flex items-center gap-2 px-5 py-2.5 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors font-medium"
                >
                    <Plus size={18} /> New Ad Placement
                </button>
            </div>

            {/* Message */}
            {message && (
                <div className={`p-4 rounded-lg flex items-center justify-between ${message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
                    }`}>
                    <span>{message.text}</span>
                    <button onClick={() => setMessage(null)} className="p-1 hover:opacity-70"><X size={16} /></button>
                </div>
            )}

            {/* Stats Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <div className="bg-white rounded-xl shadow-md p-5">
                    <div className="flex items-center gap-3">
                        <div className="bg-orange-100 p-3 rounded-lg">
                            <Megaphone className="text-orange-600" size={22} />
                        </div>
                        <div>
                            <p className="text-2xl font-black text-gray-900">{ads.length}</p>
                            <p className="text-gray-500 text-sm">Total Ads</p>
                        </div>
                    </div>
                </div>
                <div className="bg-white rounded-xl shadow-md p-5">
                    <div className="flex items-center gap-3">
                        <div className="bg-green-100 p-3 rounded-lg">
                            <Eye className="text-green-600" size={22} />
                        </div>
                        <div>
                            <p className="text-2xl font-black text-gray-900">{activeAds}</p>
                            <p className="text-gray-500 text-sm">Active Now</p>
                        </div>
                    </div>
                </div>
                <div className="bg-white rounded-xl shadow-md p-5">
                    <div className="flex items-center gap-3">
                        <div className="bg-blue-100 p-3 rounded-lg">
                            <BarChart3 className="text-blue-600" size={22} />
                        </div>
                        <div>
                            <p className="text-2xl font-black text-gray-900">{totalImpressions.toLocaleString()}</p>
                            <p className="text-gray-500 text-sm">Impressions</p>
                        </div>
                    </div>
                </div>
                <div className="bg-white rounded-xl shadow-md p-5">
                    <div className="flex items-center gap-3">
                        <div className="bg-purple-100 p-3 rounded-lg">
                            <MousePointerClick className="text-purple-600" size={22} />
                        </div>
                        <div>
                            <p className="text-2xl font-black text-gray-900">{totalClicks.toLocaleString()}</p>
                            <p className="text-gray-500 text-sm">Clicks</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Filter */}
            <div className="bg-white rounded-xl shadow-md p-4">
                <div className="flex flex-wrap gap-2">
                    <button
                        onClick={() => setFilterPosition('all')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filterPosition === 'all' ? 'bg-orange-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                            }`}
                    >
                        All Positions
                    </button>
                    {POSITION_OPTIONS.map(pos => (
                        <button
                            key={pos.value}
                            onClick={() => setFilterPosition(pos.value)}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filterPosition === pos.value ? 'bg-orange-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                }`}
                        >
                            {pos.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Ads List */}
            <div className="space-y-4">
                {filteredAds.length > 0 ? filteredAds.map(ad => {
                    const TypeIcon = getTypeIcon(ad.ad_type);
                    return (
                        <div key={ad.id} className={`bg-white rounded-xl shadow-md p-5 border-l-4 transition-all ${ad.is_currently_active ? 'border-green-500' : 'border-gray-300 opacity-75'
                            }`}>
                            <div className="flex flex-col lg:flex-row lg:items-center gap-4">
                                {/* Info */}
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-3 mb-2">
                                        <TypeIcon size={20} className="text-gray-400 flex-shrink-0" />
                                        <h3 className="font-bold text-gray-900 text-lg truncate">{ad.name}</h3>
                                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${ad.is_currently_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                                            }`}>
                                            {ad.is_currently_active ? '● Live' : '○ Inactive'}
                                        </span>
                                    </div>
                                    <div className="flex flex-wrap gap-3 text-sm text-gray-500">
                                        <span>{getPositionLabel(ad.position)}</span>
                                        <span>•</span>
                                        <span>Priority: {ad.priority}</span>
                                        <span>•</span>
                                        <span>Pages: {ad.target_pages}</span>
                                        {ad.end_date && (
                                            <>
                                                <span>•</span>
                                                <span className="flex items-center gap-1">
                                                    <Calendar size={14} />
                                                    Until {new Date(ad.end_date).toLocaleDateString()}
                                                </span>
                                            </>
                                        )}
                                        {!ad.end_date && <><span>•</span><span>∞ No expiry</span></>}
                                    </div>
                                    {ad.link && (
                                        <a href={ad.link} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-500 hover:underline flex items-center gap-1 mt-1">
                                            <ExternalLink size={12} /> {ad.link.slice(0, 60)}...
                                        </a>
                                    )}
                                </div>

                                {/* Preview */}
                                {ad.image && (
                                    <div className="w-32 h-20 bg-gray-100 rounded-lg overflow-hidden flex-shrink-0">
                                        <img src={ad.image.startsWith('http') ? ad.image : `${getApiUrl().replace('/api/v1', '')}/media/${ad.image}`} alt={ad.alt_text || ad.name} className="w-full h-full object-cover" />
                                    </div>
                                )}

                                {/* Stats */}
                                <div className="flex items-center gap-6 text-sm flex-shrink-0">
                                    <div className="text-center">
                                        <p className="font-bold text-gray-900">{ad.impressions.toLocaleString()}</p>
                                        <p className="text-gray-400 text-xs">views</p>
                                    </div>
                                    <div className="text-center">
                                        <p className="font-bold text-gray-900">{ad.clicks.toLocaleString()}</p>
                                        <p className="text-gray-400 text-xs">clicks</p>
                                    </div>
                                    <div className="text-center">
                                        <p className="font-bold text-purple-600">{ad.ctr}%</p>
                                        <p className="text-gray-400 text-xs">CTR</p>
                                    </div>
                                </div>

                                {/* Actions */}
                                <div className="flex items-center gap-2 flex-shrink-0">
                                    <button
                                        onClick={() => handleToggleActive(ad)}
                                        className={`p-2 rounded-lg transition-colors ${ad.is_active ? 'text-green-600 hover:bg-green-50' : 'text-gray-400 hover:bg-gray-100'
                                            }`}
                                        title={ad.is_active ? 'Deactivate' : 'Activate'}
                                    >
                                        {ad.is_active ? <Eye size={18} /> : <EyeOff size={18} />}
                                    </button>
                                    <button
                                        onClick={() => handleEdit(ad)}
                                        className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                        title="Edit"
                                    >
                                        <Edit3 size={18} />
                                    </button>
                                    <button
                                        onClick={() => handleDelete(ad.id)}
                                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                        title="Delete"
                                    >
                                        <Trash2 size={18} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    );
                }) : (
                    <div className="bg-white rounded-xl shadow-md p-12 text-center">
                        <Megaphone className="mx-auto text-gray-300 mb-4" size={48} />
                        <h3 className="text-lg font-semibold text-gray-600">No ad placements yet</h3>
                        <p className="text-gray-400 mt-1">Click &quot;New Ad Placement&quot; to create your first ad</p>
                    </div>
                )}
            </div>

            {/* Create/Edit Modal */}
            {showForm && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col">
                        <div className="p-6 border-b border-gray-200 flex items-center justify-between bg-white rounded-t-xl flex-shrink-0">
                            <h2 className="text-xl font-bold text-gray-900">
                                {editingId ? 'Edit Ad Placement' : 'New Ad Placement'}
                            </h2>
                            <button
                                onClick={() => { setShowForm(false); setEditingId(null); }}
                                className="p-2 hover:bg-gray-100 rounded-lg"
                            >
                                <X size={20} />
                            </button>
                        </div>

                        <form onSubmit={handleSubmit} className="p-6 space-y-6 overflow-y-auto flex-1">
                            {/* Name + Active Toggle */}
                            <div className="flex gap-4">
                                <div className="flex-1">
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Ad Name *</label>
                                    <input
                                        type="text"
                                        value={form.name}
                                        onChange={e => setForm({ ...form, name: e.target.value })}
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 text-gray-900"
                                        placeholder="e.g. BMW Campaign Header"
                                        required
                                    />
                                </div>
                                <div className="flex items-end">
                                    <button
                                        type="button"
                                        onClick={() => setForm({ ...form, is_active: !form.is_active })}
                                        className={`px-4 py-2 rounded-lg font-medium transition-colors ${form.is_active ? 'bg-green-100 text-green-700 hover:bg-green-200' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                                            }`}
                                    >
                                        {form.is_active ? '✅ Active' : '⏸️ Paused'}
                                    </button>
                                </div>
                            </div>

                            {/* Position + Priority */}
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Position *</label>
                                    <select
                                        value={form.position}
                                        onChange={e => setForm({ ...form, position: e.target.value })}
                                        className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 text-gray-900 bg-white cursor-pointer outline-none"
                                    >
                                        {POSITION_OPTIONS.map(pos => (
                                            <option key={pos.value} value={pos.value}>{pos.label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Priority (higher = first)</label>
                                    <input
                                        type="number"
                                        value={form.priority}
                                        onChange={e => setForm({ ...form, priority: parseInt(e.target.value) || 0 })}
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 text-gray-900"
                                    />
                                </div>
                            </div>

                            {/* Position Hint */}
                            {(() => {
                                const posInfo = POSITION_OPTIONS.find(p => p.value === form.position);
                                if (!posInfo) return null;
                                return (
                                    <div className="flex gap-3 bg-indigo-50 border border-indigo-200 rounded-lg p-3">
                                        <Info size={18} className="text-indigo-500 flex-shrink-0 mt-0.5" />
                                        <div className="text-sm">
                                            <p className="text-indigo-800 font-medium">{posInfo.hint}</p>
                                            <p className="text-indigo-600 mt-1">
                                                📐 Recommended image size: <strong>{posInfo.size}</strong>
                                            </p>
                                        </div>
                                    </div>
                                );
                            })()}

                            {/* Ad Type */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Ad Type *</label>
                                <div className="grid grid-cols-3 gap-3">
                                    {TYPE_OPTIONS.map(type => {
                                        const Icon = type.icon;
                                        return (
                                            <button
                                                key={type.value}
                                                type="button"
                                                onClick={() => setForm({ ...form, ad_type: type.value })}
                                                className={`p-3 rounded-lg border-2 transition-all text-sm font-medium flex flex-col items-center gap-2 ${form.ad_type === type.value
                                                    ? 'border-orange-500 bg-orange-50 text-orange-700'
                                                    : 'border-gray-200 hover:border-gray-300 text-gray-600'
                                                    }`}
                                            >
                                                <Icon size={20} />
                                                {type.label}
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* Banner fields */}
                            {form.ad_type === 'banner' && (
                                <div className="space-y-4 bg-blue-50 p-4 rounded-lg">
                                    <h3 className="font-semibold text-blue-800">🖼️ Banner Settings</h3>
                                    <div className="bg-blue-100/60 rounded-lg p-3 text-sm text-blue-700">
                                        <p className="font-medium mb-1">💡 Tips for best results:</p>
                                        <ul className="list-disc list-inside space-y-1 text-blue-600">
                                            <li>Use <strong>PNG</strong> or <strong>WebP</strong> for best quality</li>
                                            <li>Keep file size under <strong>200 KB</strong> for fast loading</li>
                                            <li>Header/Footer: horizontal banners (<strong>1200×200</strong> or <strong>728×90</strong>)</li>
                                            <li>Sidebar: square or tall (<strong>300×250</strong> or <strong>300×600</strong>)</li>
                                            <li>Use contrasting colors and a clear call-to-action</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Banner Image</label>
                                        <input type="file" accept="image/*" onChange={handleImageChange} className="w-full text-sm text-gray-900 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-100 file:text-blue-700 hover:file:bg-blue-200 file:cursor-pointer" />
                                        {imagePreview && (
                                            <div className="mt-2 relative w-full max-h-32 overflow-hidden rounded-lg border border-gray-200">
                                                <img src={imagePreview} alt="Preview" className="w-full object-contain max-h-32" />
                                            </div>
                                        )}
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Click-through URL</label>
                                        <input
                                            type="url"
                                            value={form.link}
                                            onChange={e => setForm({ ...form, link: e.target.value })}
                                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 text-gray-900"
                                            placeholder="https://example.com/campaign"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Alt Text</label>
                                        <input
                                            type="text"
                                            value={form.alt_text}
                                            onChange={e => setForm({ ...form, alt_text: e.target.value })}
                                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 text-gray-900"
                                            placeholder="BMW X5 promotion banner"
                                        />
                                    </div>
                                </div>
                            )}

                            {/* HTML code fields */}
                            {form.ad_type === 'html_code' && (
                                <div className="space-y-4 bg-green-50 p-4 rounded-lg">
                                    <h3 className="font-semibold text-green-800">💻 HTML/JS Code</h3>
                                    <div className="bg-green-100/60 rounded-lg p-3 text-sm text-green-700">
                                        <p className="font-medium mb-1">💡 Supported code types:</p>
                                        <ul className="list-disc list-inside space-y-1 text-green-600">
                                            <li><strong>Google AdSense</strong> — paste the full ad unit code</li>
                                            <li><strong>Affiliate banners</strong> — Amazon, CJ, etc.</li>
                                            <li><strong>Custom HTML</strong> — any iframe or embed code</li>
                                            <li>Use AdSense <strong>responsive units</strong> for mobile compatibility</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Paste your ad code (AdSense, affiliate, etc)
                                        </label>
                                        <textarea
                                            value={form.html_code}
                                            onChange={e => setForm({ ...form, html_code: e.target.value })}
                                            rows={6}
                                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 font-mono text-sm text-gray-900"
                                            placeholder={'<script async src="https://pagead2.googlesyndication.com/...">\n</script>\n<!-- Ad unit code -->'}
                                        />
                                    </div>
                                </div>
                            )}

                            {/* Sponsored content fields */}
                            {form.ad_type === 'sponsored' && (
                                <div className="space-y-4 bg-purple-50 p-4 rounded-lg">
                                    <h3 className="font-semibold text-purple-800">📝 Sponsored Content</h3>
                                    <div className="bg-purple-100/60 rounded-lg p-3 text-sm text-purple-700">
                                        <p className="font-medium mb-1">💡 Sponsored content tips:</p>
                                        <ul className="list-disc list-inside space-y-1 text-purple-600">
                                            <li>Displays as a native-looking card with “Sponsored” label</li>
                                            <li>Image is optional — <strong>80×80 px</strong> square works best</li>
                                            <li>Keep text short — <strong>1-2 sentences</strong> max for best CTR</li>
                                            <li>Users trust sponsored content more than banner ads</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Sponsor Name</label>
                                        <input
                                            type="text"
                                            value={form.sponsor_name}
                                            onChange={e => setForm({ ...form, sponsor_name: e.target.value })}
                                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 text-gray-900"
                                            placeholder="BMW"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Sponsor Image</label>
                                        <input type="file" accept="image/*" onChange={handleImageChange} className="w-full text-sm text-gray-900 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-100 file:text-blue-700 hover:file:bg-blue-200 file:cursor-pointer" />
                                        {imagePreview && (
                                            <div className="mt-2 relative w-full max-h-32 overflow-hidden rounded-lg border border-gray-200">
                                                <img src={imagePreview} alt="Preview" className="w-full object-contain max-h-32" />
                                            </div>
                                        )}
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Sponsored Text</label>
                                        <textarea
                                            value={form.sponsor_text}
                                            onChange={e => setForm({ ...form, sponsor_text: e.target.value })}
                                            rows={3}
                                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 text-gray-900"
                                            placeholder="Discover the new BMW iX3..."
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Link URL</label>
                                        <input
                                            type="url"
                                            value={form.link}
                                            onChange={e => setForm({ ...form, link: e.target.value })}
                                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 text-gray-900"
                                            placeholder="https://bmw.com"
                                        />
                                    </div>
                                </div>
                            )}

                            {/* Duration Presets */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    <Calendar size={14} className="inline mr-1" /> Duration
                                </label>
                                <div className="flex flex-wrap gap-2 mb-3">
                                    {DURATION_PRESETS.map(preset => (
                                        <button
                                            key={preset.value}
                                            type="button"
                                            onClick={() => handleDurationPreset(preset.value)}
                                            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${form.duration_preset === preset.value
                                                ? 'bg-orange-600 text-white shadow-md'
                                                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                                }`}
                                        >
                                            {preset.label}
                                        </button>
                                    ))}
                                </div>

                                {/* Date pickers shown for custom or any preset */}
                                {(form.duration_preset === 'custom' || (form.start_date && form.duration_preset !== 'unlimited')) && (
                                    <div className="grid grid-cols-2 gap-4 mt-3">
                                        <div>
                                            <label className="block text-xs font-medium text-gray-500 mb-1">Start Date</label>
                                            <input
                                                type="datetime-local"
                                                value={form.start_date || ''}
                                                onChange={e => setForm({ ...form, start_date: e.target.value || null })}
                                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 text-sm text-gray-900"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-medium text-gray-500 mb-1">End Date</label>
                                            <input
                                                type="datetime-local"
                                                value={form.end_date || ''}
                                                onChange={e => setForm({ ...form, end_date: e.target.value || null })}
                                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 text-sm text-gray-900"
                                            />
                                        </div>
                                    </div>
                                )}
                                {form.duration_preset === 'unlimited' && (
                                    <p className="text-sm text-gray-400 italic">Ad will run indefinitely until manually stopped</p>
                                )}
                            </div>

                            {/* Target Pages */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Show On Pages</label>
                                <select
                                    value={form.target_pages}
                                    onChange={e => setForm({ ...form, target_pages: e.target.value })}
                                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 text-gray-900 bg-white cursor-pointer outline-none"
                                >
                                    {TARGET_OPTIONS.map(opt => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>

                            {/* Spacer for scroll */}
                            <div className="h-4" />

                            {/* Actions */}
                            <div className="flex gap-3 pt-4 border-t border-gray-200">
                                <button
                                    type="button"
                                    onClick={() => { setShowForm(false); setEditingId(null); }}
                                    className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={saving}
                                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 font-medium"
                                >
                                    {saving ? <Loader2 className="animate-spin" size={18} /> : <Plus size={18} />}
                                    {editingId ? 'Update Ad' : 'Create Ad'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )
            }
        </div >
    );
}

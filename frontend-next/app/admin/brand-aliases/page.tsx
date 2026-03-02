'use client';

import { useState, useEffect } from 'react';
import {
    Plus, Edit, Trash2, X, ArrowRightLeft, AlertCircle,
    Building2, ChevronDown, ChevronRight, Globe, ExternalLink,
    Shield, Search, Car, Wrench, Check, Loader2
} from 'lucide-react';
import api from '@/lib/api';
import Link from 'next/link';

/* ─── Types ─────────────────────────────────────────────────── */
interface BrandAlias {
    id: number;
    alias: string;
    canonical_name: string;
    model_prefix: string;
    created_at: string;
}

interface BrandNode {
    id: number;
    name: string;
    slug: string;
    country: string;
    website: string;
    logo_url: string;
    description: string;
    is_parent?: boolean;
    children?: BrandNode[];
}

interface BrandTreeResponse {
    total_brands: number;
    total_groups: number;
    tree: BrandNode[];
}

interface AuditIssue {
    type: 'unknown_brand' | 'no_spec';
    article_id: number;
    article_title: string;
    current_make: string | null;
    suggestion: string | null;
}

interface AuditResponse {
    total_issues: number;
    issues: AuditIssue[];
}

/* ─── Country Flag Emoji ────────────────────────────────────── */
const countryFlags: Record<string, string> = {
    'China': '🇨🇳',
    'Japan': '🇯🇵',
    'Germany': '🇩🇪',
    'USA': '🇺🇸',
    'South Korea': '🇰🇷',
    'Sweden': '🇸🇪',
    'UK': '🇬🇧',
    'France': '🇫🇷',
    'Italy': '🇮🇹',
};

/* ─── Main Page ─────────────────────────────────────────────── */
export default function BrandIntelligencePage() {
    const [activeTab, setActiveTab] = useState<'tree' | 'aliases' | 'audit'>('tree');

    // Brand tree state
    const [tree, setTree] = useState<BrandTreeResponse | null>(null);
    const [treeLoading, setTreeLoading] = useState(true);
    const [expandedGroups, setExpandedGroups] = useState<Set<number>>(new Set());

    // Aliases state
    const [aliases, setAliases] = useState<BrandAlias[]>([]);
    const [aliasesLoading, setAliasesLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editing, setEditing] = useState<BrandAlias | null>(null);
    const [formData, setFormData] = useState({ alias: '', canonical_name: '', model_prefix: '' });
    const [error, setError] = useState('');

    // Audit state
    const [audit, setAudit] = useState<AuditResponse | null>(null);
    const [auditLoading, setAuditLoading] = useState(true);
    const [fixingIds, setFixingIds] = useState<Set<number>>(new Set());
    const [fixedIds, setFixedIds] = useState<Set<number>>(new Set());

    useEffect(() => {
        fetchTree();
        fetchAliases();
        fetchAudit();
    }, []);

    /* ─── Fetch functions ─── */
    const fetchTree = async () => {
        try {
            setTreeLoading(true);
            const res = await api.get('/brand-aliases/brand-tree/');
            setTree(res.data);
            // Auto-expand groups with children
            const groups = new Set<number>();
            res.data.tree?.forEach((b: BrandNode) => {
                if (b.is_parent) groups.add(b.id);
            });
            setExpandedGroups(groups);
        } catch (err) {
            console.error('Failed to fetch brand tree:', err);
        } finally {
            setTreeLoading(false);
        }
    };

    const fetchAliases = async () => {
        try {
            setAliasesLoading(true);
            const res = await api.get('/brand-aliases/', { params: { _t: Date.now() } });
            const data = Array.isArray(res.data) ? res.data : res.data.results || [];
            setAliases(data);
        } catch (err) {
            console.error('Failed to fetch aliases:', err);
        } finally {
            setAliasesLoading(false);
        }
    };

    const fetchAudit = async () => {
        try {
            setAuditLoading(true);
            const res = await api.get('/brand-aliases/brand-audit/');
            setAudit(res.data);
        } catch (err) {
            console.error('Failed to fetch audit:', err);
        } finally {
            setAuditLoading(false);
        }
    };

    /* ─── Alias CRUD ─── */
    const handleCreate = () => {
        setEditing(null);
        setFormData({ alias: '', canonical_name: '', model_prefix: '' });
        setError('');
        setShowModal(true);
    };

    const handleEdit = (alias: BrandAlias) => {
        setEditing(alias);
        setFormData({ alias: alias.alias, canonical_name: alias.canonical_name, model_prefix: alias.model_prefix || '' });
        setError('');
        setShowModal(true);
    };

    const handleDelete = async (id: number) => {
        if (!confirm('Delete this alias?')) return;
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
            setError('Both alias and canonical name are required');
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
            setError(`Failed: ${detail}`);
        }
    };

    const toggleGroup = (id: number) => {
        setExpandedGroups(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };

    const handleFixBrand = async (issue: AuditIssue) => {
        setFixingIds(prev => new Set(prev).add(issue.article_id));
        try {
            const payload: any = { article_id: issue.article_id };
            // Use suggestion if available, otherwise let backend resolve via alias
            if (issue.suggestion && issue.suggestion !== issue.current_make) {
                payload.new_make = issue.suggestion;
            }
            const res = await api.post('/brand-aliases/fix-brand/', payload);
            if (res.data.success) {
                setFixedIds(prev => new Set(prev).add(issue.article_id));
                // Remove from audit after 1.5s
                setTimeout(() => {
                    setAudit(prev => prev ? {
                        ...prev,
                        total_issues: prev.total_issues - 1,
                        issues: prev.issues.filter(i => i.article_id !== issue.article_id),
                    } : prev);
                }, 1500);
            } else {
                alert(res.data.message || 'Fix failed');
            }
        } catch (err: any) {
            alert(err.response?.data?.message || 'Fix failed');
        } finally {
            setFixingIds(prev => {
                const next = new Set(prev);
                next.delete(issue.article_id);
                return next;
            });
        }
    };

    /* ─── Group aliases by canonical ─── */
    const grouped = aliases.reduce((acc, alias) => {
        if (!acc[alias.canonical_name]) acc[alias.canonical_name] = [];
        acc[alias.canonical_name].push(alias);
        return acc;
    }, {} as Record<string, BrandAlias[]>);
    const sortedBrands = Object.keys(grouped).sort();

    const tabs = [
        { id: 'tree' as const, label: 'Ownership Tree', icon: Building2, count: tree?.total_brands },
        { id: 'aliases' as const, label: 'Brand Aliases', icon: ArrowRightLeft, count: aliases.length },
        { id: 'audit' as const, label: 'ML Monitor', icon: Shield, count: audit?.total_issues },
    ];

    return (
        <div className="p-6 max-w-6xl mx-auto min-h-screen bg-gray-50">
            {/* Header */}
            <div className="mb-6">
                <h1 className="text-2xl sm:text-3xl font-black text-gray-950 flex items-center gap-3">
                    <Building2 className="text-indigo-600" />
                    Brand Intelligence
                </h1>
                <p className="text-gray-500 text-sm mt-1">
                    Ownership hierarchy, brand aliases, and ML-powered data monitoring.
                </p>
            </div>

            {/* Stats Row */}
            {tree && (
                <div className="grid grid-cols-3 gap-4 mb-6">
                    <div className="bg-white rounded-xl shadow-sm p-4 border border-gray-100">
                        <div className="text-2xl font-black text-indigo-600">{tree.total_brands}</div>
                        <div className="text-xs text-gray-500 font-medium">Total Brands</div>
                    </div>
                    <div className="bg-white rounded-xl shadow-sm p-4 border border-gray-100">
                        <div className="text-2xl font-black text-purple-600">{tree.total_groups}</div>
                        <div className="text-xs text-gray-500 font-medium">Parent Groups</div>
                    </div>
                    <div className="bg-white rounded-xl shadow-sm p-4 border border-gray-100">
                        <div className="text-2xl font-black text-amber-600">{audit?.total_issues ?? '–'}</div>
                        <div className="text-xs text-gray-500 font-medium">Issues Found</div>
                    </div>
                </div>
            )}

            {/* Tab Switcher */}
            <div className="flex gap-1 bg-white rounded-xl shadow-sm p-1 mb-6 border border-gray-100">
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-bold transition-all ${activeTab === tab.id
                            ? 'bg-indigo-600 text-white shadow-md'
                            : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                            }`}
                    >
                        <tab.icon size={16} />
                        <span className="hidden sm:inline">{tab.label}</span>
                        {tab.count !== undefined && tab.count > 0 && (
                            <span className={`text-xs px-1.5 py-0.5 rounded-full font-black ${activeTab === tab.id ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-600'
                                }`}>
                                {tab.count}
                            </span>
                        )}
                    </button>
                ))}
            </div>

            {/* ═════ TAB 1: Ownership Tree ═════ */}
            {activeTab === 'tree' && (
                <div className="space-y-3">
                    {treeLoading ? (
                        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
                            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600 mx-auto" />
                            <p className="text-gray-500 mt-4 text-sm">Loading brand tree...</p>
                        </div>
                    ) : tree?.tree.map(brand => (
                        <div key={brand.id} className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                            {/* Brand Row */}
                            <div
                                className={`flex items-center gap-4 px-5 py-4 ${brand.is_parent ? 'cursor-pointer hover:bg-gray-50' : ''}`}
                                onClick={() => brand.is_parent && toggleGroup(brand.id)}
                            >
                                {/* Expand/collapse */}
                                {brand.is_parent ? (
                                    expandedGroups.has(brand.id) ?
                                        <ChevronDown size={18} className="text-indigo-500" /> :
                                        <ChevronRight size={18} className="text-gray-400" />
                                ) : (
                                    <Car size={18} className="text-gray-300" />
                                )}

                                {/* Flag + Name */}
                                <div className="flex items-center gap-2 flex-1 min-w-0">
                                    <span className="text-lg font-bold text-gray-700">{countryFlags[brand.country] || '🏁'}</span>
                                    <h3 className="font-black text-gray-900 truncate">{brand.name}</h3>
                                    {brand.is_parent && (
                                        <span className="text-xs bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full font-bold shrink-0">
                                            Group · {brand.children?.length} brand{(brand.children?.length || 0) !== 1 ? 's' : ''}
                                        </span>
                                    )}
                                </div>

                                {/* Country + Links */}
                                <div className="flex items-center gap-2 shrink-0">
                                    {brand.country && (
                                        <span className="text-xs text-gray-600 font-medium hidden sm:inline">{brand.country}</span>
                                    )}
                                    {brand.website && (
                                        <a
                                            href={brand.website}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            onClick={e => e.stopPropagation()}
                                            className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                                        >
                                            <ExternalLink size={14} />
                                        </a>
                                    )}
                                </div>
                            </div>

                            {/* Description */}
                            {brand.description && (
                                <div className="px-5 pb-3 -mt-2">
                                    <p className="text-xs text-gray-400 line-clamp-1 ml-8">{brand.description}</p>
                                </div>
                            )}

                            {/* Children */}
                            {brand.is_parent && expandedGroups.has(brand.id) && brand.children && (
                                <div className="border-t border-gray-100 bg-gray-50/50">
                                    {brand.children.map((child, i) => (
                                        <div
                                            key={child.id}
                                            className={`flex items-center gap-4 px-5 py-3 ml-6 ${i < brand.children!.length - 1 ? 'border-b border-gray-100' : ''
                                                }`}
                                        >
                                            <div className="w-5 h-5 border-l-2 border-b-2 border-indigo-200 rounded-bl-lg -mt-3 shrink-0" />
                                            <span className="text-sm font-bold text-gray-700">{countryFlags[child.country] || '🏁'}</span>
                                            <span className="font-bold text-gray-800 text-sm">{child.name}</span>
                                            {child.description && (
                                                <span className="text-xs text-gray-400 truncate hidden sm:inline">{child.description}</span>
                                            )}
                                            {child.website && (
                                                <a
                                                    href={child.website}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="ml-auto p-1 text-gray-300 hover:text-indigo-500 transition-colors"
                                                >
                                                    <ExternalLink size={12} />
                                                </a>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* ═════ TAB 2: Brand Aliases ═════ */}
            {activeTab === 'aliases' && (
                <div>
                    <div className="flex justify-between items-center mb-4">
                        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3 flex-1 mr-4">
                            <div className="flex items-start gap-2 text-sm text-indigo-700">
                                <AlertCircle size={16} className="mt-0.5 shrink-0" />
                                <span>
                                    When AI extracts a brand name matching an alias, it's automatically replaced with the canonical name.
                                </span>
                            </div>
                        </div>
                        <button
                            onClick={handleCreate}
                            className="bg-indigo-600 text-white px-4 py-2.5 rounded-lg font-bold hover:bg-indigo-700 transition-colors flex items-center gap-2 shadow-sm shrink-0"
                        >
                            <Plus size={18} />
                            Add
                        </button>
                    </div>

                    {aliasesLoading ? (
                        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
                            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600 mx-auto" />
                        </div>
                    ) : aliases.length === 0 ? (
                        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
                            <ArrowRightLeft size={40} className="mx-auto text-gray-300 mb-3" />
                            <p className="text-gray-500 text-sm">No aliases configured yet.</p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {sortedBrands.map(brand => (
                                <div key={brand} className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                                    <div className="bg-gray-50 px-5 py-3 border-b border-gray-100 flex items-center gap-3">
                                        <ArrowRightLeft size={14} className="text-indigo-500" />
                                        <h3 className="font-black text-gray-900 text-sm">{brand}</h3>
                                        <span className="text-xs bg-indigo-100 text-indigo-600 px-2 py-0.5 rounded-full font-bold">
                                            {grouped[brand].length}
                                        </span>
                                    </div>
                                    <div className="divide-y divide-gray-50">
                                        {grouped[brand].map(alias => (
                                            <div key={alias.id} className="px-5 py-2.5 flex items-center justify-between hover:bg-gray-50 group">
                                                <div className="flex items-center gap-2 text-sm flex-wrap">
                                                    <code className="font-semibold text-red-600 bg-red-50 px-2 py-0.5 rounded">{alias.alias}</code>
                                                    {alias.model_prefix && (
                                                        <span className="text-xs text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded">
                                                            model:{alias.model_prefix}*
                                                        </span>
                                                    )}
                                                    <span className="text-gray-400">→</span>
                                                    <code className="font-semibold text-green-700 bg-green-50 px-2 py-0.5 rounded">{alias.canonical_name}</code>
                                                </div>
                                                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <button
                                                        onClick={() => handleEdit(alias)}
                                                        className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                                                    >
                                                        <Edit size={13} />
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(alias.id)}
                                                        className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                                                    >
                                                        <Trash2 size={13} />
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* ═════ TAB 3: ML Brand Monitor ═════ */}
            {activeTab === 'audit' && (
                <div>
                    {auditLoading ? (
                        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
                            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600 mx-auto" />
                            <p className="text-gray-500 mt-4 text-sm">Scanning articles...</p>
                        </div>
                    ) : !audit || audit.total_issues === 0 ? (
                        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
                            <Shield size={48} className="mx-auto text-green-400 mb-3" />
                            <p className="text-green-700 font-bold">All Clear!</p>
                            <p className="text-gray-400 text-sm mt-1">No brand data issues detected.</p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {/* Summary */}
                            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center gap-3">
                                <AlertCircle size={20} className="text-amber-600 shrink-0" />
                                <span className="text-sm text-amber-800 font-medium">
                                    {audit.total_issues} issue{audit.total_issues !== 1 ? 's' : ''} found in published articles
                                </span>
                            </div>

                            {/* Issues List */}
                            {audit.issues.map((issue, i) => (
                                <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                                    <div className="flex items-start gap-3">
                                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${issue.type === 'unknown_brand'
                                            ? 'bg-amber-100 text-amber-600'
                                            : 'bg-red-100 text-red-600'
                                            }`}>
                                            {issue.type === 'unknown_brand' ? (
                                                <Search size={16} />
                                            ) : (
                                                <AlertCircle size={16} />
                                            )}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${issue.type === 'unknown_brand'
                                                    ? 'bg-amber-100 text-amber-700'
                                                    : 'bg-red-100 text-red-700'
                                                    }`}>
                                                    {issue.type === 'unknown_brand' ? 'Unknown Brand' : 'No Spec'}
                                                </span>
                                                {issue.current_make && (
                                                    <code className="text-xs text-gray-600 bg-gray-100 px-2 py-0.5 rounded">
                                                        make: {issue.current_make}
                                                    </code>
                                                )}
                                                {issue.suggestion && issue.suggestion !== issue.current_make && (
                                                    <span className="text-xs text-green-600">
                                                        → suggestion: <strong>{issue.suggestion}</strong>
                                                    </span>
                                                )}
                                            </div>
                                            <Link
                                                href={`/admin/articles/${issue.article_id}/edit`}
                                                className="text-sm text-gray-700 hover:text-indigo-600 mt-1 block truncate"
                                            >
                                                {issue.article_title}
                                            </Link>
                                        </div>
                                        {/* Quick Fix Button */}
                                        {issue.type === 'unknown_brand' && issue.current_make && (
                                            <div className="shrink-0 ml-2">
                                                {fixedIds.has(issue.article_id) ? (
                                                    <span className="flex items-center gap-1 text-xs text-green-600 font-bold px-3 py-1.5 bg-green-50 rounded-lg">
                                                        <Check size={14} /> Fixed
                                                    </span>
                                                ) : (
                                                    <button
                                                        onClick={() => handleFixBrand(issue)}
                                                        disabled={fixingIds.has(issue.article_id)}
                                                        className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 bg-indigo-50 text-indigo-600 hover:bg-indigo-100 rounded-lg transition-colors disabled:opacity-50"
                                                    >
                                                        {fixingIds.has(issue.article_id) ? (
                                                            <Loader2 size={14} className="animate-spin" />
                                                        ) : (
                                                            <Wrench size={14} />
                                                        )}
                                                        Fix
                                                    </button>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* ═════ Alias Modal ═════ */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full p-6">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-black text-gray-950">
                                {editing ? 'Edit Alias' : 'New Alias'}
                            </h2>
                            <button onClick={() => setShowModal(false)} className="p-2 hover:bg-gray-100 rounded-lg">
                                <X size={20} />
                            </button>
                        </div>

                        {error && (
                            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg mb-4 text-sm">
                                {error}
                            </div>
                        )}

                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <label className="block text-sm font-bold text-gray-900 mb-1">
                                    Alias (what AI produces) *
                                </label>
                                <input
                                    type="text"
                                    value={formData.alias}
                                    onChange={(e) => setFormData({ ...formData, alias: e.target.value })}
                                    placeholder="e.g. DongFeng VOYAH"
                                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-950"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-bold text-gray-900 mb-1">
                                    Model Prefix (optional)
                                </label>
                                <input
                                    type="text"
                                    value={formData.model_prefix}
                                    onChange={(e) => setFormData({ ...formData, model_prefix: e.target.value })}
                                    placeholder="e.g. Denza (matches BYD + model starts with Denza)"
                                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-950"
                                />
                                <p className="text-xs text-gray-400 mt-1">
                                    If set, alias only matches when model name starts with this prefix.
                                </p>
                            </div>

                            <div className="flex items-center justify-center py-1">
                                <div className="flex items-center gap-2 text-gray-400">
                                    <div className="h-px w-10 bg-gray-200" />
                                    <ArrowRightLeft size={14} />
                                    <span className="text-xs font-bold uppercase tracking-wider">maps to</span>
                                    <div className="h-px w-10 bg-gray-200" />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-bold text-gray-900 mb-1">
                                    Canonical Name (correct brand) *
                                </label>
                                <input
                                    type="text"
                                    value={formData.canonical_name}
                                    onChange={(e) => setFormData({ ...formData, canonical_name: e.target.value })}
                                    placeholder="e.g. VOYAH"
                                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-950"
                                    required
                                />
                            </div>

                            <div className="flex gap-3 pt-2">
                                <button
                                    type="submit"
                                    className="flex-1 bg-indigo-600 text-white py-2.5 rounded-lg font-bold hover:bg-indigo-700 transition-colors"
                                >
                                    {editing ? 'Save' : 'Create'}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setShowModal(false)}
                                    className="px-6 py-2.5 bg-gray-200 text-gray-700 rounded-lg font-bold hover:bg-gray-300 transition-colors"
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

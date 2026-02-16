'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
    Languages, Sparkles, Save, Eye, RefreshCw, ArrowLeft,
    FileText, Gauge, Pen, Search, CheckCircle, AlertCircle, Loader2
} from 'lucide-react';
import Link from 'next/link';
import api from '@/lib/api';

interface Category {
    id: number;
    name: string;
    slug: string;
}

interface TranslateResult {
    success: boolean;
    title: string;
    content: string;
    summary: string;
    meta_description: string;
    suggested_slug: string;
    suggested_categories: string[];
    seo_keywords: string[];
    reading_time: number;
    article_id?: number;
    article_slug?: string;
    saved?: boolean;
    error?: string;
}

export default function TranslateEnhancePage() {
    const router = useRouter();
    const [categories, setCategories] = useState<Category[]>([]);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<TranslateResult | null>(null);
    const [showPreview, setShowPreview] = useState(false);
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);

    // Form state
    const [russianText, setRussianText] = useState('');
    const [category, setCategory] = useState('News');
    const [targetLength, setTargetLength] = useState<'short' | 'medium' | 'long'>('medium');
    const [tone, setTone] = useState<'professional' | 'casual' | 'technical'>('professional');
    const [seoKeywords, setSeoKeywords] = useState('');
    const [provider, setProvider] = useState<'gemini' | 'groq'>('gemini');

    useEffect(() => {
        fetchCategories();
    }, []);

    const fetchCategories = async () => {
        try {
            const res = await api.get('/categories/');
            const data = Array.isArray(res.data) ? res.data : res.data.results || [];
            setCategories(data);
        } catch (error) {
            console.error('Failed to fetch categories:', error);
        }
    };

    const handleTranslate = async () => {
        if (!russianText.trim() || russianText.trim().length < 20) return;

        setLoading(true);
        setResult(null);
        setSaved(false);
        setShowPreview(false);

        try {
            const res = await api.post('/articles/translate-enhance/', {
                russian_text: russianText,
                category,
                target_length: targetLength,
                tone,
                seo_keywords: seoKeywords,
                provider,
            });

            setResult(res.data);
            setShowPreview(true);
        } catch (error: any) {
            const msg = error.response?.data?.error || error.message || 'Translation failed';
            setResult({
                success: false,
                title: '',
                content: '',
                summary: '',
                meta_description: '',
                suggested_slug: '',
                suggested_categories: [],
                seo_keywords: [],
                reading_time: 0,
                error: msg,
            });
        } finally {
            setLoading(false);
        }
    };

    const handleSaveDraft = async () => {
        if (!result?.title || !result?.content) return;

        setSaving(true);
        try {
            const res = await api.post('/articles/translate-enhance/', {
                russian_text: russianText,
                category,
                target_length: targetLength,
                tone,
                seo_keywords: seoKeywords,
                provider,
                save_as_draft: true,
            });

            if (res.data.saved) {
                setSaved(true);
                setResult(res.data);
            }
        } catch (error: any) {
            console.error('Save failed:', error);
        } finally {
            setSaving(false);
        }
    };

    const handleRegenerate = () => {
        handleTranslate();
    };

    const charCount = russianText.length;
    const wordCount = russianText.trim() ? russianText.trim().split(/\s+/).length : 0;

    return (
        <div className="max-w-7xl mx-auto">
            {/* Header */}
            <div className="mb-6 flex items-center justify-between flex-wrap gap-4">
                <div className="flex items-center gap-3">
                    <Link
                        href="/admin/articles"
                        className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
                    >
                        <ArrowLeft size={20} />
                    </Link>
                    <div>
                        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 flex items-center gap-2">
                            <Languages className="text-indigo-600" size={28} />
                            Translate & Enhance
                        </h1>
                        <p className="text-gray-500 text-sm mt-1">
                            Write in Russian → Get a professional English article
                        </p>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left Column: Input Form */}
                <div className="space-y-4">
                    {/* Russian Text Input */}
                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
                        <label className="block text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                            <Pen size={16} className="text-indigo-500" />
                            Russian Text
                        </label>
                        <textarea
                            value={russianText}
                            onChange={(e) => setRussianText(e.target.value)}
                            placeholder="Write your text in Russian here... For example: Новый BYD Seal 06 GT got a 530 HP electric motor. 0-100 in 3.2 seconds. 82 kWh battery provides 620 km range."
                            className="w-full h-48 px-4 py-3 border border-gray-300 rounded-lg resize-y focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-800 placeholder:text-gray-400 text-sm leading-relaxed"
                            disabled={loading}
                        />
                        <div className="flex justify-between mt-2 text-xs text-gray-400">
                            <span>{charCount} characters · {wordCount} words</span>
                            <span className={charCount < 20 ? 'text-red-400' : 'text-green-500'}>
                                {charCount < 20 ? 'Need at least 20 characters' : '✓ Ready'}
                            </span>
                        </div>
                    </div>

                    {/* Options */}
                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 space-y-4">
                        <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                            <Gauge size={16} className="text-indigo-500" />
                            Options
                        </h3>

                        {/* Category */}
                        <div>
                            <label className="block text-xs font-medium text-gray-500 mb-1">Category</label>
                            <select
                                value={category}
                                onChange={(e) => setCategory(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                disabled={loading}
                            >
                                {categories.length > 0 ? (
                                    categories.map((cat) => (
                                        <option key={cat.id} value={cat.name}>{cat.name}</option>
                                    ))
                                ) : (
                                    <>
                                        <option value="News">News</option>
                                        <option value="EVs">EVs</option>
                                        <option value="Reviews">Reviews</option>
                                        <option value="Technology">Technology</option>
                                        <option value="Luxury">Luxury</option>
                                        <option value="SUVs">SUVs</option>
                                    </>
                                )}
                            </select>
                        </div>

                        {/* Length */}
                        <div>
                            <label className="block text-xs font-medium text-gray-500 mb-2">Article Length</label>
                            <div className="grid grid-cols-3 gap-2">
                                {(['short', 'medium', 'long'] as const).map((len) => (
                                    <button
                                        key={len}
                                        onClick={() => setTargetLength(len)}
                                        disabled={loading}
                                        className={`py-2 px-3 rounded-lg text-sm font-medium transition-all border ${targetLength === len
                                            ? 'bg-indigo-600 text-white border-indigo-600 shadow-md'
                                            : 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100'
                                            }`}
                                    >
                                        {len === 'short' ? '📄 Short' : len === 'medium' ? '📑 Medium' : '📚 Long'}
                                        <div className="text-[10px] mt-0.5 opacity-70">
                                            {len === 'short' ? '400-600w' : len === 'medium' ? '800-1200w' : '1500-2000w'}
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Tone */}
                        <div>
                            <label className="block text-xs font-medium text-gray-500 mb-2">Writing Tone</label>
                            <div className="grid grid-cols-3 gap-2">
                                {(['professional', 'casual', 'technical'] as const).map((t) => (
                                    <button
                                        key={t}
                                        onClick={() => setTone(t)}
                                        disabled={loading}
                                        className={`py-2 px-3 rounded-lg text-sm font-medium transition-all border ${tone === t
                                            ? 'bg-indigo-600 text-white border-indigo-600 shadow-md'
                                            : 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100'
                                            }`}
                                    >
                                        {t === 'professional' ? '👔' : t === 'casual' ? '😊' : '🔧'} {t.charAt(0).toUpperCase() + t.slice(1)}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* SEO Keywords */}
                        <div>
                            <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                                <Search size={12} />
                                SEO Keywords <span className="text-gray-400">(optional)</span>
                            </label>
                            <input
                                type="text"
                                value={seoKeywords}
                                onChange={(e) => setSeoKeywords(e.target.value)}
                                placeholder="electric car, BYD, EV review, 2025"
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                disabled={loading}
                            />
                        </div>

                        {/* AI Provider */}
                        <div>
                            <label className="block text-xs font-medium text-gray-500 mb-1">AI Provider</label>
                            <div className="grid grid-cols-2 gap-2">
                                <button
                                    onClick={() => setProvider('gemini')}
                                    disabled={loading}
                                    className={`py-2 px-3 rounded-lg text-sm font-medium transition-all border ${provider === 'gemini'
                                        ? 'bg-blue-600 text-white border-blue-600 shadow-md'
                                        : 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100'
                                        }`}
                                >
                                    ✨ Gemini
                                </button>
                                <button
                                    onClick={() => setProvider('groq')}
                                    disabled={loading}
                                    className={`py-2 px-3 rounded-lg text-sm font-medium transition-all border ${provider === 'groq'
                                        ? 'bg-orange-600 text-white border-orange-600 shadow-md'
                                        : 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100'
                                        }`}
                                >
                                    ⚡ Groq
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Action Buttons */}
                    <button
                        onClick={handleTranslate}
                        disabled={loading || charCount < 20}
                        className={`w-full py-3 px-6 rounded-xl font-semibold text-white text-base transition-all flex items-center justify-center gap-2 shadow-lg ${loading || charCount < 20
                            ? 'bg-gray-400 cursor-not-allowed'
                            : 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 hover:shadow-xl active:scale-[0.98]'
                            }`}
                    >
                        {loading ? (
                            <>
                                <Loader2 size={20} className="animate-spin" />
                                Translating & Enhancing...
                            </>
                        ) : (
                            <>
                                <Sparkles size={20} />
                                Translate & Enhance
                            </>
                        )}
                    </button>
                </div>

                {/* Right Column: Preview */}
                <div className="space-y-4">
                    {/* Loading State */}
                    {loading && (
                        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
                            <p className="text-gray-600 font-medium">AI is translating & enhancing...</p>
                            <p className="text-gray-400 text-sm mt-1">This may take 10-20 seconds</p>
                        </div>
                    )}

                    {/* Error State */}
                    {result && !result.success && (
                        <div className="bg-red-50 rounded-xl border border-red-200 p-5">
                            <div className="flex items-center gap-2 text-red-600 font-semibold mb-2">
                                <AlertCircle size={20} />
                                Translation Failed
                            </div>
                            <p className="text-red-500 text-sm">{result.error}</p>
                        </div>
                    )}

                    {/* Success Result */}
                    {result?.success && (
                        <>
                            {/* Title & Meta */}
                            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
                                <div className="flex items-center justify-between mb-3">
                                    <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                                        <CheckCircle size={16} className="text-green-500" />
                                        Generated Article
                                    </h3>
                                    <span className="text-xs text-gray-400">
                                        📖 {result.reading_time} min read
                                    </span>
                                </div>

                                <h2 className="text-lg font-bold text-gray-900 mb-2">{result.title}</h2>
                                <p className="text-sm text-gray-600 mb-3">{result.summary}</p>

                                {/* Meta info */}
                                <div className="flex flex-wrap gap-2 mb-3">
                                    {result.seo_keywords?.map((kw, i) => (
                                        <span key={i} className="px-2 py-0.5 bg-indigo-50 text-indigo-600 text-xs rounded-full border border-indigo-200">
                                            {kw}
                                        </span>
                                    ))}
                                </div>

                                {result.suggested_categories?.length > 0 && (
                                    <div className="flex items-center gap-1 text-xs text-gray-500">
                                        <span>Suggested categories:</span>
                                        {result.suggested_categories.map((cat, i) => (
                                            <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full">
                                                {cat}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* HTML Preview */}
                            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                                <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100 bg-gray-50">
                                    <button
                                        onClick={() => setShowPreview(!showPreview)}
                                        className="text-sm font-medium text-gray-600 flex items-center gap-2 hover:text-indigo-600 transition-colors"
                                    >
                                        <Eye size={16} />
                                        {showPreview ? 'Hide Preview' : 'Show Preview'}
                                    </button>
                                    <span className="text-xs text-gray-400">
                                        {result.content.length} chars
                                    </span>
                                </div>

                                {showPreview && (
                                    <div
                                        className="p-5 prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-li:text-gray-700 prose-strong:text-gray-900"
                                        dangerouslySetInnerHTML={{ __html: result.content }}
                                    />
                                )}
                            </div>

                            {/* Action buttons */}
                            <div className="flex gap-3">
                                <button
                                    onClick={handleRegenerate}
                                    disabled={loading}
                                    className="flex-1 py-2.5 px-4 rounded-lg font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 transition-all flex items-center justify-center gap-2 text-sm"
                                >
                                    <RefreshCw size={16} />
                                    Regenerate
                                </button>

                                {saved ? (
                                    <button
                                        onClick={() => router.push(`/admin/articles`)}
                                        className="flex-1 py-2.5 px-4 rounded-lg font-medium text-white bg-green-600 hover:bg-green-700 transition-all flex items-center justify-center gap-2 text-sm shadow-md"
                                    >
                                        <CheckCircle size={16} />
                                        Saved! View Articles
                                    </button>
                                ) : (
                                    <button
                                        onClick={handleSaveDraft}
                                        disabled={saving}
                                        className="flex-1 py-2.5 px-4 rounded-lg font-medium text-white bg-indigo-600 hover:bg-indigo-700 transition-all flex items-center justify-center gap-2 text-sm shadow-md"
                                    >
                                        {saving ? (
                                            <>
                                                <Loader2 size={16} className="animate-spin" />
                                                Saving...
                                            </>
                                        ) : (
                                            <>
                                                <Save size={16} />
                                                Save as Draft
                                            </>
                                        )}
                                    </button>
                                )}
                            </div>
                        </>
                    )}

                    {/* Empty state */}
                    {!loading && !result && (
                        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
                            <Languages size={48} className="mx-auto text-gray-300 mb-4" />
                            <h3 className="text-lg font-semibold text-gray-500 mb-2">Preview will appear here</h3>
                            <p className="text-gray-400 text-sm max-w-sm mx-auto">
                                Write your text in Russian on the left, configure options, and click
                                &ldquo;Translate & Enhance&rdquo; to generate a professional English article.
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

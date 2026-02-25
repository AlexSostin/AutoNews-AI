/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unused-vars */
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Youtube, Sparkles, Save, Languages, Eye, X } from 'lucide-react';
import Link from 'next/link';
import api from '@/lib/api';
import GenerationProgress from '@/components/admin/GenerationProgress';
import { TagSelector } from '../[id]/edit/components/TagSelector';

interface Category {
  id: number;
  name: string;
  slug: string;
}

interface Tag {
  id: number;
  name: string;
  slug: string;
  group_name?: string;
}

export default function NewArticlePage() {
  const router = useRouter();
  const [categories, setCategories] = useState<Category[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [taskId, setTaskId] = useState<string>('');
  const [provider, setProvider] = useState('groq'); // Default to groq
  const [activeTab, setActiveTab] = useState<'youtube' | 'translate'>('youtube');

  // Translate tab state
  const [translateText, setTranslateText] = useState('');
  const [translateLength, setTranslateLength] = useState<'short' | 'medium' | 'long'>('medium');
  const [translateTone, setTranslateTone] = useState<'professional' | 'casual' | 'technical'>('professional');
  const [translateCategory, setTranslateCategory] = useState('News');
  const [translateProvider, setTranslateProvider] = useState<'gemini' | 'groq'>('gemini');
  const [translating, setTranslating] = useState(false);
  const [translateResult, setTranslateResult] = useState<any>(null);
  const [showTranslatePreview, setShowTranslatePreview] = useState(false);
  const [savingTranslation, setSavingTranslation] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);

  const [formData, setFormData] = useState({
    title: '',
    slug: '',
    summary: '',
    content: '',
    category_ids: [] as number[],
    tags: [] as number[],
    published: false,
    is_hero: false,
    youtube_url: '',
    author_name: '',
    author_channel_url: '',
    image: null as File | null,
    image_2: null as File | null,
    image_3: null as File | null,
  });

  useEffect(() => {
    fetchCategoriesAndTags();
  }, []);

  const fetchCategoriesAndTags = async () => {
    try {
      const [categoriesRes, tagsRes] = await Promise.all([
        api.get('/categories/'),
        api.get('/tags/')
      ]);
      // Handle both array and paginated response
      setCategories(Array.isArray(categoriesRes.data) ? categoriesRes.data : categoriesRes.data.results || []);
      setTags(Array.isArray(tagsRes.data) ? tagsRes.data : tagsRes.data.results || []);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    }
  };

  const generateSlug = (title: string) => {
    return title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '');
  };

  const handleTitleChange = (title: string) => {
    setFormData({
      ...formData,
      title,
      slug: generateSlug(title),
    });
  };

  const handleGenerateFromYoutube = async () => {
    if (!formData.youtube_url) {
      alert('Please enter a YouTube URL');
      return;
    }

    // Generate unique task ID for WebSocket tracking
    const newTaskId = `gen_${Date.now()}_${Math.random().toString(36).substring(7)}`;
    setTaskId(newTaskId);
    setGenerating(true);

    try {
      const response = await api.post('/articles/generate_from_youtube/', {
        youtube_url: formData.youtube_url,
        task_id: newTaskId,
        provider: provider
      });

      if (response.data.success) {
        // Progress component will handle completion, just redirect
        router.push(`/admin/articles/${response.data.article.id}/edit`);
      } else {
        alert('Failed to generate article: ' + response.data.error);
        setGenerating(false);
        setTaskId('');
      }
    } catch (error: any) {
      console.error('Generation error:', error);
      alert('Failed to generate article: ' + (error.response?.data?.error || error.message));
      setGenerating(false);
      setTaskId('');
    }
  };

  const handleGenerationComplete = (success: boolean, articleId?: number) => {
    setGenerating(false);
    setTaskId('');
    if (success && articleId) {
      router.push(`/admin/articles/${articleId}/edit`);
    }
  };

  const handleTranslate = async () => {
    if (!translateText.trim() || translateText.length < 20) return;

    setTranslating(true);
    setTranslateResult(null);
    setShowTranslatePreview(false);

    try {
      const res = await api.post('/articles/translate-enhance/', {
        russian_text: translateText,
        category: translateCategory,
        target_length: translateLength,
        tone: translateTone,
        provider: translateProvider,
      });

      setTranslateResult(res.data);
      setShowTranslatePreview(true);

      // Auto-fill the manual form below with translated content
      if (res.data.success) {
        setFormData({
          ...formData,
          title: res.data.title || '',
          slug: res.data.suggested_slug || '',
          summary: res.data.summary || '',
          content: res.data.content || '',
          // Auto-select matching categories
          category_ids: categories
            .filter(cat => res.data.suggested_categories?.includes(cat.name))
            .map(cat => cat.id),
        });

        // Scroll to form so user sees it's filled
        setTimeout(() => {
          const formElement = document.querySelector('form');
          if (formElement) {
            formElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        }, 500);
      }
    } catch (error: any) {
      const msg = error.response?.data?.error || error.message || 'Translation failed';
      setTranslateResult({
        success: false,
        error: msg,
      });
    } finally {
      setTranslating(false);
    }
  };

  const handleSaveTranslation = async () => {
    if (!translateResult?.title || !translateResult?.content) return;

    setSavingTranslation(true);
    try {
      const res = await api.post('/articles/translate-enhance/', {
        russian_text: translateText,
        category: translateCategory,
        target_length: translateLength,
        tone: translateTone,
        provider: translateProvider,
        save_as_draft: true,
      });

      if (res.data.saved) {
        alert('Article saved as draft!');
        router.push('/admin/articles');
      }
    } catch (error: any) {
      console.error('Save failed:', error);
      alert('Failed to save: ' + (error.response?.data?.error || error.message));
    } finally {
      setSavingTranslation(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Use FormData to handle file uploads
      const formDataToSend = new FormData();
      formDataToSend.append('title', formData.title);
      formDataToSend.append('summary', formData.summary);
      formDataToSend.append('content', formData.content);
      formData.category_ids.forEach(id => formDataToSend.append('category_ids', id.toString()));
      formData.tags.forEach(id => formDataToSend.append('tag_ids', id.toString()));
      formDataToSend.append('is_published', formData.published.toString());
      formDataToSend.append('is_hero', formData.is_hero.toString());

      if (formData.youtube_url) {
        formDataToSend.append('youtube_url', formData.youtube_url);
      }
      if (formData.author_name) {
        formDataToSend.append('author_name', formData.author_name);
      }
      if (formData.author_channel_url) {
        formDataToSend.append('author_channel_url', formData.author_channel_url);
      }

      // Add images if selected
      if (formData.image) {
        formDataToSend.append('image', formData.image);
      }
      if (formData.image_2) {
        formDataToSend.append('image_2', formData.image_2);
      }
      if (formData.image_3) {
        formDataToSend.append('image_3', formData.image_3);
      }

      const response = await api.post('/articles/', formDataToSend, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      alert('Article created successfully!');
      router.push('/admin/articles');
    } catch (error: any) {
      console.error('Failed to create article:', error);
      alert('Failed to create article: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleTagToggle = (tagId: number) => {
    setFormData({
      ...formData,
      tags: formData.tags.includes(tagId)
        ? formData.tags.filter(id => id !== tagId)
        : [...formData.tags, tagId],
    });
  };

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <Link
          href="/admin/articles"
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft size={24} />
        </Link>
        <h1 className="text-3xl font-black text-gray-950">Create New Article</h1>
      </div>

      {/* AI Generation Section with Tabs */}
      <div className="bg-gradient-to-r from-indigo-50 to-purple-50 border-2 border-indigo-200 rounded-xl p-6 mb-6">
        <div className="flex items-start gap-4 mb-4">
          <div className="bg-indigo-600 p-3 rounded-lg">
            <Sparkles className="text-white" size={24} />
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-black text-gray-900 mb-2">AI-Powered Article Generation</h3>
            <p className="text-gray-700 font-medium">
              Generate a complete automotive article using AI from YouTube videos or Russian text.
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-4 border-b border-indigo-200">
          <button
            type="button"
            onClick={() => setActiveTab('youtube')}
            className={`px-4 py-2 font-bold transition-all border-b-2 ${activeTab === 'youtube'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
          >
            <Youtube className="inline mr-2" size={18} />
            YouTube
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('translate')}
            className={`px-4 py-2 font-bold transition-all border-b-2 ${activeTab === 'translate'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
          >
            <Languages className="inline mr-2" size={18} />
            Translate
          </button>
        </div>

        {/* YouTube Tab */}
        {activeTab === 'youtube' && (
          <div>
            {/* Provider Selection */}
            <div className="flex items-center gap-4 mb-4">
              <label className="text-sm font-bold text-gray-700">AI Provider:</label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="provider"
                    value="groq"
                    checked={provider === 'groq'}
                    onChange={(e) => setProvider(e.target.value)}
                    className="text-indigo-600 focus:ring-indigo-500"
                  />
                  <span className="text-sm font-bold text-gray-900">Groq (Fast)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="provider"
                    value="gemini"
                    checked={provider === 'gemini'}
                    onChange={(e) => setProvider(e.target.value)}
                    className="text-indigo-600 focus:ring-indigo-500"
                  />
                  <span className="text-sm font-bold text-gray-900">Google Gemini (High Quality)</span>
                </label>
              </div>
            </div>

            <div className="flex flex-wrap sm:flex-nowrap gap-3">
              <div className="flex-1 min-w-[200px] relative">
                <Youtube className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <input
                  type="url"
                  placeholder="https://youtube.com/watch?v=..."
                  value={formData.youtube_url}
                  onChange={(e) => setFormData({ ...formData, youtube_url: e.target.value })}
                  className="w-full pl-10 pr-4 py-3 border-2 border-indigo-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
                  disabled={generating}
                />
              </div>

              <button
                type="button"
                onClick={handleGenerateFromYoutube}
                disabled={generating || !formData.youtube_url}
                className="px-4 sm:px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-bold hover:from-indigo-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md flex items-center gap-2 whitespace-nowrap w-full sm:w-auto justify-center"
              >
                {generating ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles size={20} />
                    Generate with AI
                  </>
                )}
              </button>
            </div>

            {/* Progress Component */}
            {generating && taskId && (
              <div className="mt-4">
                <GenerationProgress
                  taskId={taskId}
                  isGenerating={generating}
                  onComplete={handleGenerationComplete}
                />
              </div>
            )}
          </div>
        )}

        {/* Translate Tab */}
        {activeTab === 'translate' && (
          <div className="space-y-4">
            <textarea
              value={translateText}
              onChange={(e) => setTranslateText(e.target.value)}
              placeholder="Write text in Russian... For example: Новый BYD Seal 06 GT получил мощный электромотор на 530 л.с. (The AI will translate and enhance it into a full English article)"
              className="w-full h-32 px-4 py-3 border-2 border-indigo-300 rounded-lg resize-y focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900 placeholder:text-gray-400 text-sm leading-relaxed"
              disabled={translating}
            />
            <div className="text-xs text-gray-500">
              {translateText.length} characters · {translateText.trim() ? translateText.trim().split(/\s+/).length : 0} words
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Length</label>
                <select
                  value={translateLength}
                  onChange={(e) => setTranslateLength(e.target.value as any)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500"
                  disabled={translating}
                >
                  <option value="short">Short</option>
                  <option value="medium">Medium</option>
                  <option value="long">Long</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Tone</label>
                <select
                  value={translateTone}
                  onChange={(e) => setTranslateTone(e.target.value as any)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500"
                  disabled={translating}
                >
                  <option value="professional">Professional</option>
                  <option value="casual">Casual</option>
                  <option value="technical">Technical</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Category</label>
                <select
                  value={translateCategory}
                  onChange={(e) => setTranslateCategory(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500"
                  disabled={translating}
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
                    </>
                  )}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Provider</label>
                <select
                  value={translateProvider}
                  onChange={(e) => setTranslateProvider(e.target.value as any)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500"
                  disabled={translating}
                >
                  <option value="gemini">Gemini</option>
                  <option value="groq">Groq</option>
                </select>
              </div>
            </div>

            <button
              type="button"
              onClick={handleTranslate}
              disabled={translating || translateText.length < 20}
              className="w-full py-3 px-6 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-bold hover:from-indigo-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md flex items-center justify-center gap-2"
            >
              {translating ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  Translating...
                </>
              ) : (
                <>
                  <Languages size={20} />
                  Translate & Enhance
                </>
              )}
            </button>

            {/* Translation Result */}
            {translateResult && translateResult.success && (
              <div className="mt-4 p-4 bg-white rounded-lg border border-green-200">
                <div className="flex items-center gap-2 text-green-600 font-bold mb-2">
                  <Save size={18} />
                  Translation Complete!
                </div>
                <h4 className="font-bold text-gray-900 mb-1">{translateResult.title}</h4>
                <p className="text-sm text-gray-600 mb-2">{translateResult.summary}</p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setShowTranslatePreview(!showTranslatePreview)}
                    className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
                  >
                    {showTranslatePreview ? 'Hide' : 'Show'} Preview
                  </button>
                  <button
                    type="button"
                    onClick={handleSaveTranslation}
                    disabled={savingTranslation}
                    className="ml-auto px-4 py-1.5 bg-indigo-600 text-white rounded-lg text-sm font-bold hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {savingTranslation ? 'Saving...' : 'Save as Draft'}
                  </button>
                </div>
                {showTranslatePreview && (
                  <div
                    className="mt-3 p-3 bg-gray-50 rounded text-sm prose prose-sm max-w-none text-gray-900"
                    dangerouslySetInnerHTML={{ __html: translateResult.content }}
                  />
                )}
              </div>
            )}

            {translateResult && !translateResult.success && (
              <div className="mt-4 p-4 bg-red-50 rounded-lg border border-red-200">
                <p className="text-red-600 text-sm font-medium">{translateResult.error}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Manual Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-md p-6">
        {/* Autofill Success Banner */}
        {translateResult?.success && formData.title && (
          <div className="mb-6 p-4 bg-green-50 border-2 border-green-200 rounded-lg">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2 text-green-700 font-bold">
                <Save size={18} />
                Form Auto-Filled from Translation!
              </div>
              <button
                type="button"
                onClick={() => setShowPreviewModal(true)}
                className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-sm font-bold hover:bg-indigo-700 transition-colors flex items-center gap-1.5"
              >
                <Eye size={16} />
                Preview
              </button>
            </div>
            <p className="text-sm text-green-600">
              Title, content, summary, and categories have been filled. You can now add images and publish directly.
            </p>
          </div>
        )}

        <div className="space-y-6">
          {/* Title */}
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Title *</label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => handleTitleChange(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
              required
            />
          </div>

          {/* Slug */}
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Slug *</label>
            <input
              type="text"
              value={formData.slug}
              onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
              required
            />
          </div>

          {/* YouTube URL */}
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">YouTube URL</label>
            <input
              type="url"
              value={formData.youtube_url}
              onChange={(e) => setFormData({ ...formData, youtube_url: e.target.value })}
              placeholder="https://youtube.com/watch?v=..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
            />
          </div>

          {/* Content Source Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Content Source</label>
              <input
                type="text"
                value={formData.author_name}
                onChange={(e) => setFormData({ ...formData, author_name: e.target.value })}
                placeholder="e.g., Toyota Global, Doug DeMuro, Carwow"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
              />
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Source URL</label>
              <input
                type="url"
                value={formData.author_channel_url}
                onChange={(e) => setFormData({ ...formData, author_channel_url: e.target.value })}
                placeholder="https://global.toyota/... or YouTube channel"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
              />
            </div>
          </div>

          {/* Summary */}
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Summary *</label>
            <textarea
              value={formData.summary}
              onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
              rows={3}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
              required
            />
          </div>

          {/* Content */}
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Content (HTML) *</label>
            <textarea
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
              rows={12}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-mono text-sm"
              required
            />
          </div>

          {/* Images Section */}
          <div className="border-t pt-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Images (Optional)</h3>
            <p className="text-sm text-gray-600 mb-4">Upload up to 3 images or they will be auto-extracted from YouTube during AI generation</p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Image 1 */}
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Image 1 (Main)</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setFormData({ ...formData, image: e.target.files?.[0] || null })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm text-gray-900 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 transition-all"
                />
                {formData.image && (
                  <p className="text-xs text-green-600 mt-1">✓ {formData.image.name}</p>
                )}
              </div>

              {/* Image 2 */}
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Image 2</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setFormData({ ...formData, image_2: e.target.files?.[0] || null })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm text-gray-900 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 transition-all"
                />
                {formData.image_2 && (
                  <p className="text-xs text-green-600 mt-1">✓ {formData.image_2.name}</p>
                )}
              </div>

              {/* Image 3 */}
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Image 3</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setFormData({ ...formData, image_3: e.target.files?.[0] || null })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm text-gray-900 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 transition-all"
                />
                {formData.image_3 && (
                  <p className="text-xs text-green-600 mt-1">✓ {formData.image_3.name}</p>
                )}
              </div>
            </div>
          </div>

          {/* onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
              rows={3}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
              required
            />
          </div>

          {/* Content */}
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Content (HTML) *</label>
            <textarea
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
              rows={12}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-mono text-sm"
              required
            />
          </div>

          <TagSelector
            categories={categories}
            tags={tags}
            setTags={setTags}
            formData={formData}
            setFormData={setFormData}
            handleTagToggle={handleTagToggle}
          />

          {/* Published Status & Hero */}
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="published"
                checked={formData.published}
                onChange={(e) => setFormData({ ...formData, published: e.target.checked })}
                className="w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="published" className="text-sm font-bold text-gray-900">
                Publish immediately
              </label>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="is_hero"
                checked={formData.is_hero}
                onChange={(e) => setFormData({ ...formData, is_hero: e.target.checked })}
                className="w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="is_hero" className="text-sm font-bold text-gray-900 cursor-pointer">
                ⭐ Show in Hero Section
              </label>
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex gap-4 pt-4">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-3 rounded-lg font-bold hover:from-indigo-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  Creating...
                </>
              ) : (
                <>
                  <Save size={20} />
                  Create Article
                </>
              )}
            </button>
            <Link
              href="/admin/articles"
              className="px-6 py-3 bg-gray-200 text-gray-800 rounded-lg font-bold hover:bg-gray-300 transition-colors"
            >
              Cancel
            </Link>
          </div>
        </div>
      </form>

      {/* Preview Modal */}
      {showPreviewModal && formData.title && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
              <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <Eye size={20} className="text-indigo-600" />
                Article Preview
              </h3>
              <button
                onClick={() => setShowPreviewModal(false)}
                className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
              >
                <X size={20} className="text-gray-600" />
              </button>
            </div>

            {/* Modal Content - Scrollable */}
            <div className="flex-1 overflow-y-auto p-8">
              {/* Article Header */}
              <div className="mb-6">
                <h1 className="text-3xl sm:text-4xl font-black text-gray-900 mb-3">
                  {formData.title}
                </h1>

                {formData.summary && (
                  <p className="text-lg text-gray-600 mb-4 leading-relaxed">
                    {formData.summary}
                  </p>
                )}

                <div className="flex flex-wrap items-center gap-3 text-sm text-gray-500">
                  {translateResult?.reading_time && (
                    <span className="flex items-center gap-1">
                      📖 {translateResult.reading_time} min read
                    </span>
                  )}
                  {categories.filter(cat => formData.category_ids.includes(cat.id)).map(cat => (
                    <span key={cat.id} className="px-2 py-1 bg-indigo-100 text-indigo-700 rounded-full text-xs font-medium">
                      {cat.name}
                    </span>
                  ))}
                </div>
              </div>

              {/* Article Content */}
              <div
                className="prose prose-lg max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-li:text-gray-700 prose-strong:text-gray-900 prose-a:text-indigo-600 hover:prose-a:text-indigo-700"
                dangerouslySetInnerHTML={{ __html: formData.content }}
              />
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-gray-200 bg-gray-50 flex justify-end">
              <button
                onClick={() => setShowPreviewModal(false)}
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg font-medium hover:bg-gray-300 transition-colors"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* eslint-disable @typescript-eslint/no-explicit-any */
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Youtube, Sparkles, Save, Languages, Eye, X, Search, Image as ImageIcon, Loader2, RefreshCw, Zap } from 'lucide-react';
import Link from 'next/link';
import api from '@/lib/api';
import GenerationProgress from '@/components/admin/GenerationProgress';
import { TagSelector } from '../[id]/edit/components/TagSelector';
import { PhotoSearchModal } from '../[id]/edit/components/PhotoSearchModal';
import { PageHeader } from '@/app/admin/components/ui/PageHeader';
import { ArticleBasicInfo } from '@/app/admin/articles/components/ArticleBasicInfo';
import { ArticleContentEditor } from '@/app/admin/articles/components/ArticleContentEditor';
import { ArticleSeoMeta } from '@/app/admin/articles/components/ArticleSeoMeta';
import { ArticlePublishSettings } from '@/app/admin/articles/components/ArticlePublishSettings';
import { ArticleImageManager } from '@/app/admin/articles/components/ArticleImageManager';

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

  // Photo Search State
  const [photoSearchOpen, setPhotoSearchOpen] = useState(false);
  const [photoSearchSlot, setPhotoSearchSlot] = useState<number>(1);
  const [photoSearchQuery, setPhotoSearchQuery] = useState('');
  const [photoSearchLoading, setPhotoSearchLoading] = useState(false);
  const [photoSearchResults, setPhotoSearchResults] = useState<any[]>([]);
  const [savingPhoto, setSavingPhoto] = useState<string | null>(null);
  const [imageSource, setImageSource] = useState<string>('unknown');
  const [generatingAI, setGeneratingAI] = useState<number | null>(null);
  const [previewImage, setPreviewImage] = useState<string | null>(null);

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
    current_image: '',
    current_image_2: '',
    current_image_3: '',
    delete_image: false,
    delete_image_2: false,
    delete_image_3: false,
    show_source: true,
    show_youtube: true,
    show_price: true,
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
      formDataToSend.append('show_source', formData.show_source.toString());
      formDataToSend.append('show_youtube', formData.show_youtube.toString());
      formDataToSend.append('show_price', formData.show_price.toString());
      formDataToSend.append('image_source', imageSource);

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

  const searchPhotosCustom = async () => {
    if (!photoSearchQuery.trim()) return;
    setPhotoSearchLoading(true);
    setPhotoSearchResults([]);
    try {
      const { data } = await api.get('/articles/search_photos/', {
        params: { query: photoSearchQuery, max_results: 30 }
      });
      setPhotoSearchResults(data.results || []);
    } catch (err: any) {
      alert('Failed to search photos: ' + (err.response?.data?.detail || err.message));
    } finally {
      setPhotoSearchLoading(false);
    }
  };

  const handlePhotoSelect = async (url: string) => {
    setSavingPhoto(url);
    try {
      // Create a Blob from the image URL to simulate a file upload in the formData
      const response = await fetch(url);
      const blob = await response.blob();
      const filename = `press_photo_${Date.now()}.jpg`;
      const file = new File([blob], filename, { type: blob.type });

      if (photoSearchSlot === 1) {
        setFormData({ ...formData, image: file });
        setImageSource('pexels');
      }
      if (photoSearchSlot === 2) setFormData({ ...formData, image_2: file });
      if (photoSearchSlot === 3) setFormData({ ...formData, image_3: file });

      setPhotoSearchOpen(false);
    } catch (err: any) {
      alert('Failed to process image: ' + err.message);
    } finally {
      setSavingPhoto(null);
    }
  };

  return (
    <div>
      <PhotoSearchModal
        photoSearchOpen={photoSearchOpen}
        setPhotoSearchOpen={setPhotoSearchOpen}
        photoSearchSlot={photoSearchSlot}
        photoSearchQuery={photoSearchQuery}
        setPhotoSearchQuery={setPhotoSearchQuery}
        searchPhotosCustom={searchPhotosCustom}
        photoSearchLoading={photoSearchLoading}
        photoSearchResults={photoSearchResults}
        savingPhoto={savingPhoto}
        selectPhoto={handlePhotoSelect}
      />

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
      <form onSubmit={handleSubmit} className="space-y-6">
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

        {/* 1. Basic Info: Title, Slug, Summary */}
        <ArticleBasicInfo
          title={formData.title}
          slug={formData.slug}
          summary={formData.summary}
          onTitleChange={handleTitleChange}
          onSlugChange={(v) => setFormData({ ...formData, slug: v })}
          onSummaryChange={(v) => setFormData({ ...formData, summary: v })}
        />

        {/* 2. Article Content (WYSIWYG Editor) */}
        <ArticleContentEditor
          content={formData.content}
          onContentChange={(newContent) => setFormData({ ...formData, content: newContent })}
          onReformat={() => alert('Save the article first to use AI Reformat')}
          onEnrich={() => alert('Save the article first to use AI Enrich')}
          onRegenerate={() => alert('Save the article first to use AI Regenerate')}
          isReformatting={false}
          isEnriching={false}
          isRegenerating={false}
          hasYoutubeUrl={!!formData.youtube_url}
        />

        {/* 3. Categories, Tags & YouTube */}
        <ArticleSeoMeta
          youtubeUrl={formData.youtube_url}
          onYoutubeUrlChange={(v: string) => setFormData({ ...formData, youtube_url: v })}
          showYoutube={formData.show_youtube}
          onShowYoutubeChange={(v: boolean) => setFormData({ ...formData, show_youtube: v })}
          categorySelector={
            <TagSelector
              categories={categories}
              tags={[]}
              setTags={() => { }}
              formData={formData}
              setFormData={setFormData}
              handleTagToggle={() => { }}
            />
          }
          tagSelector={
            <TagSelector
              categories={[]}
              tags={tags}
              setTags={setTags}
              formData={formData}
              setFormData={setFormData}
              handleTagToggle={handleTagToggle}
            />
          }
        />

        {/* 4. Images */}
        <ArticleImageManager
          formData={formData}
          setFormData={setFormData}
          imageSource={imageSource}
          setImageSource={setImageSource}
          setPreviewImage={setPreviewImage}
          openPhotoSearch={(slot: number) => {
            setPhotoSearchSlot(slot);
            setPhotoSearchQuery(formData.title || formData.slug || '');
            setPhotoSearchOpen(true);
            setPhotoSearchResults([]);
          }}
          photoSearchLoading={photoSearchLoading}
          generateAIImage={async () => {
            alert('Please save the article first before generating AI images.');
          }}
          generatingAI={generatingAI}
        />

        {/* 5. Publish Settings */}
        <ArticlePublishSettings
          isPublished={formData.published}
          isHero={formData.is_hero}
          onPublishedChange={(v: boolean) => setFormData({ ...formData, published: v })}
          onHeroChange={(v: boolean) => setFormData({ ...formData, is_hero: v })}
        />

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-4 rounded-xl font-bold text-lg hover:from-indigo-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 size={22} className="animate-spin" />
              Creating...
            </>
          ) : (
            <>
              <Save size={22} />
              Create Article
            </>
          )}
        </button>
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

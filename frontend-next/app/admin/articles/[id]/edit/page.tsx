/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @next/next/no-img-element */
/* eslint-disable react-hooks/exhaustive-deps */
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Eye, Languages, Save, Sparkles, Youtube, ArrowLeft, Plus, X, Loader2, Search, ChevronDown, Zap, Lock, Unlock, Wand2, Maximize2, Download, EyeOff, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import api from '@/lib/api';
import { PhotoSearchModal } from './components/PhotoSearchModal';
import { TagSelector, Category, Tag } from './components/TagSelector';

interface ArticleData {
  id: number;
  title: string;
  slug: string;
  summary: string;
  content: string;
  categories: { id: number; name: string; slug: string }[];
  tags: number[];
  published: boolean;
  is_hero: boolean;
  youtube_url: string;
}

import { GallerySection, GalleryImage } from './components/GallerySection';

export default function EditArticlePage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const [articleId, setArticleId] = useState<string | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [galleryImages, setGalleryImages] = useState<GalleryImage[]>([]);
  const [newGalleryImages, setNewGalleryImages] = useState<File[]>([]);
  const [uploadingGallery, setUploadingGallery] = useState(false);
  const [reformatting, setReformatting] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [slugEditable, setSlugEditable] = useState(false);
  const [generatingAI, setGeneratingAI] = useState<number | null>(null);
  const [aiStyle, setAiStyle] = useState('scenic_road');
  const [aiCustomPrompt, setAiCustomPrompt] = useState('');
  const [aiMode, setAiMode] = useState<'auto' | 'custom'>('auto');
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  // Find Photo state
  const [photoSearchOpen, setPhotoSearchOpen] = useState(false);
  const [photoSearchSlot, setPhotoSearchSlot] = useState(1);
  const [photoSearchResults, setPhotoSearchResults] = useState<any[]>([]);
  const [photoSearchLoading, setPhotoSearchLoading] = useState(false);
  const [photoSearchQuery, setPhotoSearchQuery] = useState('');
  const [savingPhoto, setSavingPhoto] = useState<string | null>(null);
  const [imageSource, setImageSource] = useState<string>('unknown');

  const aiStyles = [
    { key: 'scenic_road', label: '🏔️ Scenic Road' },
    { key: 'desert_sunset', label: '🌅 Desert Sunset' },
    { key: 'urban_city', label: '🌃 Urban City' },
    { key: 'mountain_pass', label: '⛰️ Mountain Pass' },
    { key: 'studio', label: '📸 Studio' },
    { key: 'coastal', label: '🌊 Coastal' },
    { key: 'forest', label: '🌲 Forest' },
    { key: 'showroom', label: '✨ Showroom' },
  ];

  const generateAIImage = async (slot: number) => {
    if (!articleId || generatingAI) return;
    setGeneratingAI(slot);
    try {
      const response = await api.post(`/articles/${articleId}/generate-ai-image/`, {
        style: aiStyle,
        image_slot: slot,
        custom_prompt: aiMode === 'custom' ? aiCustomPrompt : '',
      });
      if (response.data.success) {
        const url = response.data.image_url;
        if (slot === 1) {
          setFormData(prev => ({ ...prev, current_image: url, delete_image: false, image: null }));
          setImageSource('ai_generated');
        }
        if (slot === 2) setFormData(prev => ({ ...prev, current_image_2: url, delete_image_2: false, image_2: null }));
        if (slot === 3) setFormData(prev => ({ ...prev, current_image_3: url, delete_image_3: false, image_3: null }));
        alert('✅ AI image generated and saved!');
      }
    } catch (error: any) {
      const msg = error?.response?.data?.error || 'Failed to generate AI image';
      alert(`❌ ${msg}`);
    } finally {
      setGeneratingAI(null);
    }
  };

  // Find Photo functions
  const openPhotoSearch = async (slot: number) => {
    setPhotoSearchSlot(slot);
    setPhotoSearchOpen(true);
    setPhotoSearchResults([]);
    setPhotoSearchQuery('');
    setPhotoSearchLoading(true);
    try {
      const response = await api.get(`/articles/${articleId}/search-photos/`);
      setPhotoSearchResults(response.data.results || []);
      setPhotoSearchQuery(response.data.query || '');
    } catch (error: any) {
      alert(`❌ Failed to search photos: ${error?.response?.data?.error || error.message}`);
    } finally {
      setPhotoSearchLoading(false);
    }
  };

  const searchPhotosCustom = async () => {
    if (!photoSearchQuery.trim()) return;
    setPhotoSearchLoading(true);
    try {
      const response = await api.get(`/articles/${articleId}/search-photos/`, {
        params: { q: photoSearchQuery }
      });
      setPhotoSearchResults(response.data.results || []);
    } catch (error: any) {
      alert(`❌ ${error?.response?.data?.error || error.message}`);
    } finally {
      setPhotoSearchLoading(false);
    }
  };

  const selectPhoto = async (imageUrl: string) => {
    setSavingPhoto(imageUrl);
    try {
      const response = await api.post(`/articles/${articleId}/save-external-image/`, {
        image_url: imageUrl,
        image_slot: photoSearchSlot,
      });
      if (response.data.success) {
        const url = response.data.image_url;
        if (photoSearchSlot === 1) {
          setFormData(prev => ({ ...prev, current_image: url, delete_image: false, image: null }));
          setImageSource('pexels');
        }
        if (photoSearchSlot === 2) setFormData(prev => ({ ...prev, current_image_2: url, delete_image_2: false, image_2: null }));
        if (photoSearchSlot === 3) setFormData(prev => ({ ...prev, current_image_3: url, delete_image_3: false, image_3: null }));
        setPhotoSearchOpen(false);
        alert('✅ Photo saved! You can now use 🎨 AI Photo to enhance it.');
      }
    } catch (error: any) {
      alert(`❌ Failed to save photo: ${error?.response?.data?.error || error.message}`);
    } finally {
      setSavingPhoto(null);
    }
  };

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
    params.then(({ id }) => {
      setArticleId(id);
      fetchData(id);
    });
  }, [params]);

  const fetchData = async (id: string) => {
    try {
      const [articleRes, categoriesRes, tagsRes] = await Promise.all([
        api.get(`/articles/${id}/`),
        api.get('/categories/'),
        api.get('/tags/')
      ]);

      const article = articleRes.data;

      // Helper to build full image URL (runtime detection)
      const getMediaUrl = () => {
        if (typeof window !== 'undefined') {
          const host = window.location.hostname;
          if (host !== 'localhost' && host !== '127.0.0.1') {
            return 'https://heroic-healing-production-2365.up.railway.app';
          }
        }
        return 'http://localhost:8000';
      };

      const buildImageUrl = (path: string) => {
        if (!path) return '';
        if (path.startsWith('http://') || path.startsWith('https://')) return path;
        return `${getMediaUrl()}${path}`;
      };

      setFormData({
        title: article.title || '',
        slug: article.slug || '',
        summary: article.summary || '',
        content: article.content || '',
        category_ids: Array.isArray(article.categories) ? article.categories.map((cat: any) => cat.id) : [],
        tags: Array.isArray(article.tags) ? article.tags.map((tag: any) => tag.id) : [],
        published: article.is_published ?? false,
        is_hero: article.is_hero ?? false,
        youtube_url: article.youtube_url || '',
        author_name: article.author_name || '',
        author_channel_url: article.author_channel_url || '',
        image: null,
        image_2: null,
        image_3: null,
        current_image: buildImageUrl(article.thumbnail_url || article.image || ''),
        current_image_2: buildImageUrl(article.image_2_url || article.image_2 || ''),
        current_image_3: buildImageUrl(article.image_3_url || article.image_3 || ''),
        delete_image: false,
        delete_image_2: false,
        delete_image_3: false,
        show_source: article.show_source ?? true,
        show_youtube: article.show_youtube ?? true,
        show_price: article.show_price ?? true,
      });

      setImageSource(article.image_source || 'unknown');

      // Handle both array and paginated response
      setCategories(Array.isArray(categoriesRes.data) ? categoriesRes.data : categoriesRes.data.results || []);
      setTags(Array.isArray(tagsRes.data) ? tagsRes.data : tagsRes.data.results || []);

      // Fetch gallery images
      await fetchGalleryImages(id);
    } catch (error) {
      console.error('Failed to fetch data:', error);
      alert('Failed to load article');
    } finally {
      setLoading(false);
    }
  };

  const fetchGalleryImages = async (articleId: string) => {
    try {
      const response = await api.get(`/article-images/?article=${articleId}`);
      setGalleryImages(response.data.results || response.data || []);
    } catch (error) {
      console.error('Failed to fetch gallery images:', error);
    }
  };

  const handleGalleryImageUpload = async (files: FileList | null) => {
    if (!files || !articleId) return;

    const filesArray = Array.from(files);
    setNewGalleryImages(prev => [...prev, ...filesArray]);
  };

  const deleteGalleryImage = async (imageId: number) => {
    if (!confirm('Delete this gallery image?')) return;

    try {
      await api.delete(`/article-images/${imageId}/`);
      setGalleryImages(prev => prev.filter(img => img.id !== imageId));
    } catch (error) {
      console.error('Failed to delete gallery image:', error);
      alert('Failed to delete image');
    }
  };

  const uploadGalleryImages = async () => {
    if (newGalleryImages.length === 0 || !articleId) return;

    setUploadingGallery(true);
    try {
      // Upload all images in PARALLEL for 3x faster performance
      await Promise.all(
        newGalleryImages.map(file => {
          const formData = new FormData();
          formData.append('article', articleId);
          formData.append('image', file);
          formData.append('order', '0');

          return api.post('/article-images/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
        })
      );

      // Refresh gallery images
      await fetchGalleryImages(articleId);
      setNewGalleryImages([]);
    } catch (error) {
      console.error('Failed to upload gallery images:', error);
      alert('Failed to upload some images');
    } finally {
      setUploadingGallery(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!articleId) return;

    setSaving(true);
    try {
      // Use FormData if images are being uploaded or deleted
      if (formData.image || formData.image_2 || formData.image_3 || formData.delete_image || formData.delete_image_2 || formData.delete_image_3) {
        const formDataToSend = new FormData();
        formDataToSend.append('title', formData.title);
        if (slugEditable) formDataToSend.append('slug', formData.slug);
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

        if (formData.image) {
          formDataToSend.append('image', formData.image);
        }
        if (formData.image_2) {
          formDataToSend.append('image_2', formData.image_2);
        }
        if (formData.image_3) {
          formDataToSend.append('image_3', formData.image_3);
        }

        // Handle image deletion
        if (formData.delete_image) formDataToSend.append('delete_image', 'true');
        if (formData.delete_image_2) formDataToSend.append('delete_image_2', 'true');
        if (formData.delete_image_3) formDataToSend.append('delete_image_3', 'true');

        await api.put(`/articles/${articleId}/`, formDataToSend, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
      } else {
        // No images - use JSON
        const payload: Record<string, any> = {
          title: formData.title,
          summary: formData.summary,
          content: formData.content,
          category_ids: formData.category_ids,
          tag_ids: formData.tags,
          is_published: formData.published,
          is_hero: formData.is_hero,
          youtube_url: formData.youtube_url,
          author_name: formData.author_name,
          author_channel_url: formData.author_channel_url,
          show_source: formData.show_source,
          show_youtube: formData.show_youtube,
          show_price: formData.show_price,
          image_source: imageSource,
        };
        if (slugEditable) payload.slug = formData.slug;

        await api.put(`/articles/${articleId}/`, payload);
      }

      // Upload gallery images if any
      await uploadGalleryImages();

      alert('Article updated successfully!');
      router.push('/admin/articles');
    } catch (error: any) {
      console.error('Failed to update article:', error);
      alert('Failed to update article: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSaving(false);
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

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="text-gray-600 mt-4 font-medium">Loading article...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div>
        <div className="flex items-center gap-4 mb-6">
          <Link
            href="/admin/articles"
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft size={24} />
          </Link>
          <h1 className="text-3xl font-black text-gray-950">Edit Article</h1>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-md p-6">
          <div className="space-y-6">
            {/* Title */}
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Title *</label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
                required
              />
            </div>

            {/* Slug */}
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">
                Slug <span className="text-sm font-normal text-gray-600">{slugEditable ? '(editing — will change URL!)' : '(auto-generated from title)'}</span>
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={formData.slug}
                  onChange={(e) => slugEditable && setFormData({ ...formData, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-').replace(/-+/g, '-') })}
                  className={`flex-1 px-4 py-3 border rounded-lg font-medium ${slugEditable
                    ? 'border-amber-400 bg-amber-50 text-gray-900 focus:ring-2 focus:ring-amber-500 focus:border-transparent outline-none'
                    : 'border-gray-300 bg-gray-50 text-gray-700 cursor-not-allowed'
                    }`}
                  disabled={!slugEditable}
                />
                <button
                  type="button"
                  onClick={() => {
                    if (!slugEditable) {
                      if (confirm('⚠️ Changing the slug will change the article URL.\n\nThis can break existing links and hurt SEO if the article is already indexed.\n\nAre you sure you want to edit the slug?')) {
                        setSlugEditable(true);
                      }
                    } else {
                      setSlugEditable(false);
                    }
                  }}
                  className={`px-3 py-3 rounded-lg border transition-colors ${slugEditable
                    ? 'bg-amber-100 border-amber-400 text-amber-700 hover:bg-amber-200'
                    : 'bg-gray-100 border-gray-300 text-gray-500 hover:bg-gray-200'
                    }`}
                  title={slugEditable ? 'Lock slug' : 'Unlock slug for editing'}
                >
                  {slugEditable ? <Unlock size={18} /> : <Lock size={18} />}
                </button>
              </div>
            </div>

            {/* YouTube URL */}
            <div className={`transition-opacity ${!formData.show_youtube ? 'opacity-50' : ''}`}>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-bold text-gray-900">YouTube URL</label>
                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, show_youtube: !formData.show_youtube })}
                  className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium transition-all ${formData.show_youtube
                    ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                    : 'bg-gray-200 text-gray-500 hover:bg-gray-300'
                    }`}
                  title={formData.show_youtube ? 'Visible on public page' : 'Hidden from public page'}
                >
                  {formData.show_youtube ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                  {formData.show_youtube ? 'Visible' : 'Hidden'}
                </button>
              </div>
              <input
                type="url"
                value={formData.youtube_url}
                onChange={(e) => setFormData({ ...formData, youtube_url: e.target.value })}
                placeholder="https://youtube.com/watch?v=..."
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
              />
            </div>

            {/* Content Source Information */}
            <div className={`grid grid-cols-1 md:grid-cols-2 gap-4 transition-opacity ${!formData.show_source ? 'opacity-50' : ''}`}>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-bold text-gray-900">Content Source</label>
                  <button
                    type="button"
                    onClick={() => setFormData({ ...formData, show_source: !formData.show_source })}
                    className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium transition-all ${formData.show_source
                      ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                      : 'bg-gray-200 text-gray-500 hover:bg-gray-300'
                      }`}
                    title={formData.show_source ? 'Visible on public page' : 'Hidden from public page'}
                  >
                    {formData.show_source ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                    {formData.show_source ? 'Visible' : 'Hidden'}
                  </button>
                </div>
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

            {/* Price Visibility Toggle */}
            <div className="flex items-center justify-between py-2 px-4 bg-gray-50 rounded-lg border border-gray-200">
              <div>
                <span className="text-sm font-bold text-gray-900">💰 Price Display</span>
                <p className="text-xs text-gray-500">Show price (auto-extracted by AI) on public page</p>
              </div>
              <button
                type="button"
                onClick={() => setFormData({ ...formData, show_price: !formData.show_price })}
                className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium transition-all ${formData.show_price
                  ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                  : 'bg-gray-200 text-gray-500 hover:bg-gray-300'
                  }`}
                title={formData.show_price ? 'Visible on public page' : 'Hidden from public page'}
              >
                {formData.show_price ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                {formData.show_price ? 'Visible' : 'Hidden'}
              </button>
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
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-bold text-gray-900">Content (HTML) *</label>
                <button
                  type="button"
                  onClick={async () => {
                    if (!articleId || !formData.content.trim()) return;
                    setReformatting(true);
                    try {
                      const { data } = await api.post(`/articles/${articleId}/reformat-content/`, {
                        content: formData.content,
                      });
                      if (data.success && data.content) {
                        const diff = data.original_length - data.new_length;
                        const msg = diff > 0
                          ? `Reformatted! Reduced by ${diff} chars (${data.original_length} → ${data.new_length})`
                          : `Reformatted! (${data.original_length} → ${data.new_length} chars)`;
                        setFormData({ ...formData, content: data.content });
                        alert(`✅ ${msg}`);
                      } else {
                        alert(`❌ ${data.message || 'Reformat failed'}`);
                      }
                    } catch (err: any) {
                      alert(`❌ Error: ${err.response?.data?.message || err.message}`);
                    }
                    setReformatting(false);
                  }}
                  disabled={reformatting || !formData.content.trim()}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg text-xs font-bold hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
                >
                  {reformatting ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                  {reformatting ? 'Reformatting...' : '✨ Reformat with AI'}
                </button>
                <button
                  type="button"
                  onClick={async () => {
                    if (!articleId) return;
                    if (!confirm('Run AI enrichment? This will:\n\n• Generate VehicleSpecs card (Gemini)\n• Create A/B title variants\n• Web search for latest specs\n\nArticle content will NOT be changed.')) return;
                    setEnriching(true);
                    try {
                      const { data } = await api.post(`/articles/${articleId}/re-enrich/`);
                      let msg = `✅ ${data.message}\n\n`;
                      if (data.results?.deep_specs?.success) {
                        msg += `🚗 Specs: ${data.results.deep_specs.make} ${data.results.deep_specs.model} (${data.results.deep_specs.fields_filled} fields)\n`;
                      } else if (data.results?.deep_specs?.error) {
                        msg += `⚠️ Specs: ${data.results.deep_specs.error}\n`;
                      }
                      if (data.results?.ab_titles?.success) {
                        msg += data.results.ab_titles.skipped
                          ? `📝 A/B: ${data.results.ab_titles.existing_variants} variants already exist\n`
                          : `📝 A/B: ${data.results.ab_titles.variants_created} variants created\n`;
                      } else if (data.results?.ab_titles?.error) {
                        msg += `⚠️ A/B: ${data.results.ab_titles.error}\n`;
                      }
                      if (data.results?.web_search?.success) {
                        msg += `🔍 Web: ${data.results.web_search.context_length} chars of context found\n`;
                      } else if (data.results?.web_search?.error) {
                        msg += `⚠️ Web: ${data.results.web_search.error}\n`;
                      }
                      alert(msg);
                    } catch (err: any) {
                      alert(`❌ Error: ${err.response?.data?.message || err.message}`);
                    }
                    setEnriching(false);
                  }}
                  disabled={enriching || reformatting}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-lg text-xs font-bold hover:from-emerald-700 hover:to-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
                >
                  {enriching ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
                  {enriching ? 'Enriching...' : '⚡ Re-enrich Specs'}
                </button>
                <button
                  type="button"
                  onClick={async () => {
                    if (!articleId) return;
                    const isYoutube = !!formData.youtube_url;
                    const confirmMsg = isYoutube
                      ? '🔄 REGENERATE ARTICLE?\n\nThis will:\n• Re-download YouTube transcript\n• Re-generate title, content, summary\n• Update tags, specs, A/B titles\n\n⚠️ Current content will be backed up but REPLACED!\n\nContinue?'
                      : '🔄 REGENERATE RSS ARTICLE?\n\nThis will:\n• Re-expand the original press release with AI\n• Re-generate title, content, summary\n• Update A/B titles\n\n⚠️ Current content will be backed up but REPLACED!\n\nContinue?';
                    if (!confirm(confirmMsg)) return;
                    setRegenerating(true);
                    try {
                      const { data } = await api.post(`/articles/${articleId}/regenerate/`, {
                        provider: 'gemini',
                      });
                      if (data.success) {
                        const timing = data.generation_metadata?.timings?.total || data.generation_metadata?.word_count || '?';
                        alert(`✅ Article regenerated! (${timing}${typeof timing === 'number' ? ' words' : 's'})\n\nNew title: ${data.article?.title || 'N/A'}\n\nPage will reload to show new content.`);
                        window.location.reload();
                      } else {
                        alert(`❌ ${data.message || 'Regeneration failed'}`);
                      }
                    } catch (err: any) {
                      alert(`❌ Error: ${err.response?.data?.message || err.message}`);
                    }
                    setRegenerating(false);
                  }}
                  disabled={regenerating || reformatting || enriching}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg text-xs font-bold hover:from-orange-600 hover:to-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
                  title={formData.youtube_url ? 'Regenerate article from YouTube' : 'Regenerate article from RSS source'}
                >
                  {regenerating ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                  {regenerating ? 'Regenerating...' : '🔄 Regenerate'}
                </button>
              </div>
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
              <h3 className="text-lg font-bold text-gray-900 mb-2 flex items-center gap-3">
                Images
                {imageSource && imageSource !== 'unknown' && (
                  <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${imageSource === 'pexels' ? 'bg-purple-100 text-purple-700 border border-purple-200' :
                    imageSource === 'youtube' ? 'bg-red-100 text-red-700 border border-red-200' :
                      imageSource === 'rss_original' ? 'bg-blue-100 text-blue-700 border border-blue-200' :
                        imageSource === 'uploaded' ? 'bg-green-100 text-green-700 border border-green-200' :
                          imageSource === 'ai_generated' ? 'bg-amber-100 text-amber-700 border border-amber-200' :
                            'bg-gray-100 text-gray-600 border border-gray-200'
                    }`}>
                    {imageSource === 'pexels' && '📷 Pexels Stock'}
                    {imageSource === 'youtube' && '🎥 YouTube Thumbnail'}
                    {imageSource === 'rss_original' && `📰 Source: ${formData.author_name || 'Press Release'}`}
                    {imageSource === 'uploaded' && '📤 Manual Upload'}
                    {imageSource === 'ai_generated' && '🤖 AI Generated'}
                  </span>
                )}
              </h3>
              <p className="text-sm text-gray-600 mb-3">Replace images or keep existing ones from AI generation</p>

              {/* AI Image Generation Mode */}
              <div className="mb-4 p-3 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg border border-purple-200">
                {/* Mode Tabs */}
                <div className="flex items-center gap-1 mb-3">
                  <Wand2 className="w-4 h-4 text-purple-700" />
                  <span className="text-sm font-semibold text-purple-800 mr-2">AI Photo:</span>
                  <button
                    type="button"
                    onClick={() => setAiMode('auto')}
                    className={`px-3 py-1 text-xs font-bold rounded-l-lg border transition-all ${aiMode === 'auto'
                      ? 'bg-purple-600 text-white border-purple-600 shadow-sm'
                      : 'bg-white text-purple-600 border-purple-300 hover:bg-purple-50'
                      }`}
                  >
                    🚗 Auto
                  </button>
                  <button
                    type="button"
                    onClick={() => setAiMode('custom')}
                    className={`px-3 py-1 text-xs font-bold rounded-r-lg border-t border-b border-r transition-all ${aiMode === 'custom'
                      ? 'bg-purple-600 text-white border-purple-600 shadow-sm'
                      : 'bg-white text-purple-600 border-purple-300 hover:bg-purple-50'
                      }`}
                  >
                    ✏️ Custom
                  </button>
                </div>

                {/* Auto Mode — Scene Style Selector */}
                {aiMode === 'auto' && (
                  <div className="flex items-center gap-3 flex-wrap">
                    <select
                      value={aiStyle}
                      onChange={(e) => setAiStyle(e.target.value)}
                      className="px-3 py-1.5 text-sm border border-purple-300 rounded-lg bg-white text-gray-800 focus:ring-2 focus:ring-purple-400 focus:border-transparent outline-none"
                    >
                      {aiStyles.map(s => (
                        <option key={s.key} value={s.key}>{s.label}</option>
                      ))}
                    </select>
                    <span className="text-xs text-purple-600">AI generates a car photo with the selected scene style</span>
                  </div>
                )}

                {/* Custom Mode — Free-form Prompt */}
                {aiMode === 'custom' && (
                  <div>
                    <input
                      type="text"
                      value={aiCustomPrompt}
                      onChange={(e) => setAiCustomPrompt(e.target.value)}
                      placeholder="e.g. Futuristic steering yoke in a car cockpit, close-up, ambient blue lighting..."
                      className="w-full px-3 py-2 text-sm border border-purple-300 rounded-lg bg-white text-gray-800 focus:ring-2 focus:ring-purple-400 focus:border-transparent outline-none placeholder:text-gray-400"
                    />
                    <span className="text-[10px] text-purple-500 mt-1 block">Describe what you want — AI will generate any image using the reference photo as context</span>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Image 1 */}
                <div>
                  <label className="block text-sm font-bold text-gray-900 mb-2">Image 1 (Main)</label>
                  {formData.current_image && !formData.delete_image && (
                    <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-gray-200 group cursor-pointer" onClick={() => setPreviewImage(formData.current_image)}>
                      <img
                        src={formData.current_image}
                        alt="Current Image 1"
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-all flex items-center justify-center">
                        <Maximize2 className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-lg" />
                      </div>
                      <div className="absolute top-1 right-1 flex gap-1">
                        <span className="bg-green-500 text-white text-xs px-2 py-1 rounded shadow-sm">Current</span>
                        <button
                          type="button"
                          onClick={() => setFormData({ ...formData, delete_image: true })}
                          className="bg-red-500 text-white text-xs px-2 py-1 rounded shadow-sm hover:bg-red-600 transition-colors"
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  )}
                  {formData.delete_image && (
                    <div className="mb-2 text-sm text-red-600 bg-red-50 p-2 rounded border border-red-200 flex justify-between items-center">
                      <span>Marked for deletion</span>
                      <button
                        type="button"
                        onClick={() => setFormData({ ...formData, delete_image: false })}
                        className="text-gray-600 underline text-xs hover:text-gray-900"
                      >
                        Undo
                      </button>
                    </div>
                  )}
                  <label className="inline-flex items-center gap-2 px-3 py-2 bg-gray-50 text-gray-700 rounded-lg border border-gray-300 hover:bg-gray-100 transition-colors cursor-pointer text-sm font-medium">
                    📁 {formData.current_image && !formData.delete_image ? 'Replace Image' : 'Choose Image'}
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => {
                        const file = e.target.files?.[0] || null;
                        setFormData({ ...formData, image: file, delete_image: false });
                        setImageSource('uploaded');
                      }}
                      className="hidden"
                    />
                  </label>
                  {formData.image && (
                    <div className="mt-2 relative h-32 rounded-lg overflow-hidden border-2 border-green-300 bg-gray-100">
                      <img
                        src={URL.createObjectURL(formData.image)}
                        alt="Upload preview"
                        className="w-full h-full object-cover"
                      />
                      <span className="absolute top-1 right-1 bg-green-500 text-white text-xs px-2 py-1 rounded shadow-sm">📤 New Upload</span>
                    </div>
                  )}
                  <div className="flex gap-1.5 mt-1">
                    <button
                      type="button"
                      onClick={() => openPhotoSearch(1)}
                      disabled={photoSearchLoading}
                      className="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-lg hover:from-emerald-600 hover:to-teal-700 transition-all text-sm font-medium disabled:opacity-50 shadow-sm"
                    >
                      <Search className="w-3.5 h-3.5" /> 🔍 Find Photo
                    </button>
                    <button
                      type="button"
                      onClick={() => generateAIImage(1)}
                      disabled={generatingAI !== null || (!formData.current_image && !formData.image)}
                      className="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-lg hover:from-purple-600 hover:to-indigo-700 transition-all text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                    >
                      {generatingAI === 1 ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating...</> : <><Wand2 className="w-3.5 h-3.5" /> 🎨 AI Photo</>}
                    </button>
                  </div>
                </div>

                {/* Image 2 */}
                <div>
                  <label className="block text-sm font-bold text-gray-900 mb-2">Image 2</label>
                  {formData.current_image_2 && !formData.delete_image_2 && (
                    <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-gray-200 group cursor-pointer" onClick={() => setPreviewImage(formData.current_image_2)}>
                      <img
                        src={formData.current_image_2}
                        alt="Current Image 2"
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-all flex items-center justify-center">
                        <Maximize2 className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-lg" />
                      </div>
                      <div className="absolute top-1 right-1 flex gap-1">
                        <span className="bg-green-500 text-white text-xs px-2 py-1 rounded shadow-sm">Current</span>
                        <button
                          type="button"
                          onClick={() => setFormData({ ...formData, delete_image_2: true })}
                          className="bg-red-500 text-white text-xs px-2 py-1 rounded shadow-sm hover:bg-red-600 transition-colors"
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  )}
                  {formData.delete_image_2 && (
                    <div className="mb-2 text-sm text-red-600 bg-red-50 p-2 rounded border border-red-200 flex justify-between items-center">
                      <span>Marked for deletion</span>
                      <button
                        type="button"
                        onClick={() => setFormData({ ...formData, delete_image_2: false })}
                        className="text-gray-600 underline text-xs hover:text-gray-900"
                      >
                        Undo
                      </button>
                    </div>
                  )}
                  <label className="inline-flex items-center gap-2 px-3 py-2 bg-gray-50 text-gray-700 rounded-lg border border-gray-300 hover:bg-gray-100 transition-colors cursor-pointer text-sm font-medium">
                    📁 {formData.current_image_2 && !formData.delete_image_2 ? 'Replace Image' : 'Choose Image'}
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => setFormData({ ...formData, image_2: e.target.files?.[0] || null, delete_image_2: false })}
                      className="hidden"
                    />
                  </label>
                  {formData.image_2 && (
                    <div className="mt-2 relative h-32 rounded-lg overflow-hidden border-2 border-green-300 bg-gray-100">
                      <img
                        src={URL.createObjectURL(formData.image_2)}
                        alt="Upload preview"
                        className="w-full h-full object-cover"
                      />
                      <span className="absolute top-1 right-1 bg-green-500 text-white text-xs px-2 py-1 rounded shadow-sm">📤 New Upload</span>
                    </div>
                  )}
                  <div className="flex gap-1.5 mt-1">
                    <button
                      type="button"
                      onClick={() => openPhotoSearch(2)}
                      disabled={photoSearchLoading}
                      className="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-lg hover:from-emerald-600 hover:to-teal-700 transition-all text-sm font-medium disabled:opacity-50 shadow-sm"
                    >
                      <Search className="w-3.5 h-3.5" /> 🔍 Find Photo
                    </button>
                    <button
                      type="button"
                      onClick={() => generateAIImage(2)}
                      disabled={generatingAI !== null || !formData.current_image}
                      className="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-lg hover:from-purple-600 hover:to-indigo-700 transition-all text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                    >
                      {generatingAI === 2 ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating...</> : <><Wand2 className="w-3.5 h-3.5" /> 🎨 AI Photo</>}
                    </button>
                  </div>
                </div>

                {/* Image 3 */}
                <div>
                  <label className="block text-sm font-bold text-gray-900 mb-2">Image 3</label>
                  {formData.current_image_3 && !formData.delete_image_3 && (
                    <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-gray-200 group cursor-pointer" onClick={() => setPreviewImage(formData.current_image_3)}>
                      <img
                        src={formData.current_image_3}
                        alt="Current Image 3"
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-all flex items-center justify-center">
                        <Maximize2 className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-lg" />
                      </div>
                      <div className="absolute top-1 right-1 flex gap-1">
                        <span className="bg-green-500 text-white text-xs px-2 py-1 rounded shadow-sm">Current</span>
                        <button
                          type="button"
                          onClick={() => setFormData({ ...formData, delete_image_3: true })}
                          className="bg-red-500 text-white text-xs px-2 py-1 rounded shadow-sm hover:bg-red-600 transition-colors"
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  )}
                  {formData.delete_image_3 && (
                    <div className="mb-2 text-sm text-red-600 bg-red-50 p-2 rounded border border-red-200 flex justify-between items-center">
                      <span>Marked for deletion</span>
                      <button
                        type="button"
                        onClick={() => setFormData({ ...formData, delete_image_3: false })}
                        className="text-gray-600 underline text-xs hover:text-gray-900"
                      >
                        Undo
                      </button>
                    </div>
                  )}
                  <label className="inline-flex items-center gap-2 px-3 py-2 bg-gray-50 text-gray-700 rounded-lg border border-gray-300 hover:bg-gray-100 transition-colors cursor-pointer text-sm font-medium">
                    📁 {formData.current_image_3 && !formData.delete_image_3 ? 'Replace Image' : 'Choose Image'}
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => setFormData({ ...formData, image_3: e.target.files?.[0] || null, delete_image_3: false })}
                      className="hidden"
                    />
                  </label>
                  {formData.image_3 && (
                    <div className="mt-2 relative h-32 rounded-lg overflow-hidden border-2 border-green-300 bg-gray-100">
                      <img
                        src={URL.createObjectURL(formData.image_3)}
                        alt="Upload preview"
                        className="w-full h-full object-cover"
                      />
                      <span className="absolute top-1 right-1 bg-green-500 text-white text-xs px-2 py-1 rounded shadow-sm">📤 New Upload</span>
                    </div>
                  )}
                  <div className="flex gap-1.5 mt-1">
                    <button
                      type="button"
                      onClick={() => openPhotoSearch(3)}
                      disabled={photoSearchLoading}
                      className="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-lg hover:from-emerald-600 hover:to-teal-700 transition-all text-sm font-medium disabled:opacity-50 shadow-sm"
                    >
                      <Search className="w-3.5 h-3.5" /> 🔍 Find Photo
                    </button>
                    <button
                      type="button"
                      onClick={() => generateAIImage(3)}
                      disabled={generatingAI !== null || !formData.current_image}
                      className="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-lg hover:from-purple-600 hover:to-indigo-700 transition-all text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                    >
                      {generatingAI === 3 ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating...</> : <><Wand2 className="w-3.5 h-3.5" /> 🎨 AI Photo</>}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <GallerySection
              galleryImages={galleryImages}
              newGalleryImages={newGalleryImages}
              setNewGalleryImages={setNewGalleryImages}
              deleteGalleryImage={deleteGalleryImage}
              uploadingGallery={uploadingGallery}
            />

            <TagSelector
              categories={categories}
              tags={tags}
              setTags={setTags}
              formData={formData}
              setFormData={setFormData}
              handleTagToggle={handleTagToggle}
            />

            <div className="flex flex-wrap gap-8">
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="published"
                  checked={formData.published}
                  onChange={(e) => setFormData({ ...formData, published: e.target.checked })}
                  className="w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                />
                <label htmlFor="published" className="text-sm font-bold text-gray-900 cursor-pointer">
                  Published (Visible on site)
                </label>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="is_hero"
                  checked={formData.is_hero}
                  onChange={(e) => setFormData({ ...formData, is_hero: e.target.checked })}
                  className="w-5 h-5 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
                />
                <label htmlFor="is_hero" className="text-sm font-bold text-gray-900 cursor-pointer">
                  Hero (Promote to homepage banner)
                </label>
              </div>
            </div>

            {/* Submit Button */}
            <div className="flex gap-4 pt-4">
              <button
                type="submit"
                disabled={saving}
                className="flex-1 bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-3 rounded-lg font-bold hover:from-indigo-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md flex items-center justify-center gap-2"
              >
                {saving ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    Saving...
                  </>
                ) : (
                  <>
                    <Save size={20} />
                    Save Changes
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
        </form >
      </div >

      {/* Image Preview Lightbox Modal */}
      {previewImage && (
        <div
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setPreviewImage(null)}
        >
          <div className="relative max-w-5xl max-h-[90vh] w-full" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setPreviewImage(null)}
              className="absolute -top-10 right-0 text-white hover:text-gray-300 transition-colors"
            >
              <X className="w-8 h-8" />
            </button>
            <img
              src={previewImage!}
              alt="Preview"
              className="w-full h-full object-contain rounded-lg shadow-2xl"
            />
            <a
              href={previewImage!}
              target="_blank"
              rel="noopener noreferrer"
              className="absolute bottom-4 right-4 px-3 py-1.5 bg-white/90 text-gray-800 rounded-lg text-sm font-medium hover:bg-white transition-colors shadow-lg"
            >
              Open Original ↗
            </a>
          </div>
        </div>
      )}

      {/* Photo Search Modal */}
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
        selectPhoto={selectPhoto}
      />
    </>
  );
}

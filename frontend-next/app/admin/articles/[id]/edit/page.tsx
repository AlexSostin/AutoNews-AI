'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Save, Plus, X, Sparkles, Loader2, Search, ChevronDown, Zap, Lock, Unlock, Wand2, Maximize2, Download, Eye, EyeOff, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import api from '@/lib/api';

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

interface GalleryImage {
  id: number;
  image: string;
  caption: string;
  order: number;
}

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
  const [tagSearch, setTagSearch] = useState('');
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [letterFilter, setLetterFilter] = useState<Record<string, string | null>>({});
  const [slugEditable, setSlugEditable] = useState(false);
  const [generatingAI, setGeneratingAI] = useState<number | null>(null);
  const [aiStyle, setAiStyle] = useState('scenic_road');
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  // Find Photo state
  const [photoSearchOpen, setPhotoSearchOpen] = useState(false);
  const [photoSearchSlot, setPhotoSearchSlot] = useState(1);
  const [photoSearchResults, setPhotoSearchResults] = useState<any[]>([]);
  const [photoSearchLoading, setPhotoSearchLoading] = useState(false);
  const [photoSearchQuery, setPhotoSearchQuery] = useState('');
  const [savingPhoto, setSavingPhoto] = useState<string | null>(null);

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
      });
      if (response.data.success) {
        const url = response.data.image_url;
        if (slot === 1) setFormData(prev => ({ ...prev, current_image: url, delete_image: false, image: null }));
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
        if (photoSearchSlot === 1) setFormData(prev => ({ ...prev, current_image: url, delete_image: false, image: null }));
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

  const removeNewGalleryImage = (index: number) => {
    setNewGalleryImages(prev => prev.filter((_, i) => i !== index));
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
        formDataToSend.append('tag_ids', JSON.stringify(formData.tags));
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
                    if (!articleId || !formData.youtube_url) {
                      alert('❌ No YouTube URL — cannot regenerate');
                      return;
                    }
                    if (!confirm('🔄 REGENERATE ARTICLE?\n\nThis will:\n• Re-download YouTube transcript\n• Re-generate title, content, summary\n• Update tags, specs, A/B titles\n\n⚠️ Current content will be backed up but REPLACED!\n\nContinue?')) return;
                    setRegenerating(true);
                    try {
                      const { data } = await api.post(`/articles/${articleId}/regenerate/`, {
                        provider: 'gemini',
                      });
                      if (data.success) {
                        const timing = data.generation_metadata?.timings?.total || '?';
                        alert(`✅ Article regenerated! (${timing}s)\n\nNew title: ${data.article?.title || 'N/A'}\n\nPage will reload to show new content.`);
                        window.location.reload();
                      } else {
                        alert(`❌ ${data.message || 'Regeneration failed'}`);
                      }
                    } catch (err: any) {
                      alert(`❌ Error: ${err.response?.data?.message || err.message}`);
                    }
                    setRegenerating(false);
                  }}
                  disabled={regenerating || reformatting || enriching || !formData.youtube_url}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg text-xs font-bold hover:from-orange-600 hover:to-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
                  title={!formData.youtube_url ? 'No YouTube URL — cannot regenerate' : 'Regenerate article from YouTube'}
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
              <h3 className="text-lg font-bold text-gray-900 mb-2">Images</h3>
              <p className="text-sm text-gray-600 mb-3">Replace images or keep existing ones from AI generation</p>

              {/* AI Style Selector */}
              <div className="mb-4 p-3 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg border border-purple-200">
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="text-sm font-semibold text-purple-800 flex items-center gap-1"><Wand2 className="w-4 h-4" /> AI Style:</span>
                  <select
                    value={aiStyle}
                    onChange={(e) => setAiStyle(e.target.value)}
                    className="px-3 py-1.5 text-sm border border-purple-300 rounded-lg bg-white text-gray-800 focus:ring-2 focus:ring-purple-400 focus:border-transparent outline-none"
                  >
                    {aiStyles.map(s => (
                      <option key={s.key} value={s.key}>{s.label}</option>
                    ))}
                  </select>
                  <span className="text-xs text-purple-600">Select a scene style, then click 🎨 AI Photo on any image slot</span>
                </div>
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
                      onChange={(e) => setFormData({ ...formData, image: e.target.files?.[0] || null, delete_image: false })}
                      className="hidden"
                    />
                  </label>
                  {formData.image && (
                    <p className="text-xs text-green-600 mt-1">✓ Will replace with: {formData.image.name}</p>
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
                    <p className="text-xs text-green-600 mt-1">✓ Will replace with: {formData.image_2.name}</p>
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
                    <p className="text-xs text-green-600 mt-1">✓ Will replace with: {formData.image_3.name}</p>
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

            {/* Gallery Images Section */}
            <div className="border-t pt-6">
              <h3 className="text-lg font-bold text-gray-900 mb-2">Additional Gallery Images</h3>
              <p className="text-sm text-gray-600 mb-4">Add extra images that will appear in the Vehicle Gallery alongside the 3 main images above</p>

              {/* Existing Gallery Images as individual cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                {galleryImages.map((img, index) => (
                  <div key={img.id}>
                    <label className="block text-sm font-bold text-gray-900 mb-2">Image {index + 4}</label>
                    <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-gray-200 group">
                      <img
                        src={img.image.startsWith('http') ? img.image : `${typeof window !== 'undefined' && window.location.hostname !== 'localhost' ? 'https://heroic-healing-production-2365.up.railway.app' : 'http://localhost:8000'}${img.image}`}
                        alt={img.caption || `Gallery image ${index + 4}`}
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute top-1 right-1 flex gap-1">
                        <span className="bg-green-500 text-white text-xs px-2 py-1 rounded shadow-sm">Current</span>
                        <button
                          type="button"
                          onClick={() => deleteGalleryImage(img.id)}
                          className="bg-red-500 text-white text-xs px-2 py-1 rounded shadow-sm hover:bg-red-600 transition-colors"
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  </div>
                ))}

                {/* New gallery images to upload - individual cards */}
                {newGalleryImages.map((file, index) => (
                  <div key={`new-${index}`}>
                    <label className="block text-sm font-bold text-gray-900 mb-2">Image {galleryImages.length + index + 4}</label>
                    <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-green-300 group">
                      <img
                        src={URL.createObjectURL(file)}
                        alt={file.name}
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute top-1 right-1 flex gap-1">
                        <span className="bg-green-500 text-white text-xs px-2 py-1 rounded shadow-sm">New</span>
                        <button
                          type="button"
                          onClick={() => removeNewGalleryImage(index)}
                          className="bg-red-500 text-white text-xs px-2 py-1 rounded shadow-sm hover:bg-red-600 transition-colors"
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                    <p className="text-xs text-green-600 mt-1">✓ Will upload: {file.name}</p>
                  </div>
                ))}
              </div>

              {/* Add Image Button */}
              <div>
                <label className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-50 text-indigo-700 rounded-lg border-2 border-dashed border-indigo-300 hover:bg-indigo-100 transition-colors cursor-pointer font-semibold">
                  <Plus size={20} />
                  + Add More Images
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => {
                      if (e.target.files?.[0]) {
                        setNewGalleryImages(prev => [...prev, e.target.files![0]]);
                        e.target.value = '';
                      }
                    }}
                    className="hidden"
                  />
                </label>
                {uploadingGallery && (
                  <span className="ml-3 text-sm text-gray-600">Uploading...</span>
                )}
              </div>
            </div>

            {/* Categories */}
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Categories *</label>
              <div className="flex flex-wrap gap-2">
                {categories.map((cat) => (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => {
                      const ids = formData.category_ids.includes(cat.id)
                        ? formData.category_ids.filter(id => id !== cat.id)
                        : [...formData.category_ids, cat.id];
                      setFormData({ ...formData, category_ids: ids });
                    }}
                    className={`px-4 py-2 rounded-lg text-sm font-bold transition-all border-2 ${formData.category_ids.includes(cat.id)
                      ? 'bg-indigo-600 border-indigo-600 text-white shadow-md'
                      : 'bg-white border-gray-200 text-gray-700 hover:border-indigo-300'
                      }`}
                  >
                    {cat.name}
                    {formData.category_ids.includes(cat.id) && (
                      <span className="ml-2">✓</span>
                    )}
                  </button>
                ))}
              </div>
              {formData.category_ids.length === 0 && (
                <p className="text-sm text-red-500 mt-1">Select at least one category</p>
              )}
            </div>

            {/* Tags */}
            <div className="border-t pt-6">
              <label className="block text-lg font-bold text-gray-900 mb-2">Tags & Categories</label>
              <p className="text-sm text-gray-600 mb-4">Select relevant tags grouped by category</p>

              {/* Search Filter */}
              <div className="relative mb-4">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={tagSearch}
                  onChange={(e) => setTagSearch(e.target.value)}
                  placeholder="Search tags..."
                  className="w-full pl-10 pr-4 py-2.5 border-2 border-gray-200 rounded-xl text-sm focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 outline-none transition-all text-gray-900 placeholder:text-gray-400"
                />
                {tagSearch && (
                  <button
                    onClick={() => setTagSearch('')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Selected tags summary */}
              {formData.tags.length > 0 && (
                <div className="mb-4 flex flex-wrap gap-1.5">
                  {tags.filter(t => formData.tags.includes(t.id)).map(tag => (
                    <span
                      key={tag.id}
                      className="inline-flex items-center gap-1 px-2.5 py-1 bg-indigo-100 text-indigo-800 rounded-full text-xs font-semibold"
                    >
                      {tag.name}
                      <button
                        type="button"
                        onClick={() => handleTagToggle(tag.id)}
                        className="hover:text-indigo-950"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}

              <div className="space-y-2">
                {(() => {
                  const LETTER_COLORS: Record<string, string> = {
                    A: 'bg-blue-500', B: 'bg-emerald-500', C: 'bg-violet-500', D: 'bg-amber-500',
                    E: 'bg-rose-500', F: 'bg-cyan-500', G: 'bg-indigo-500', H: 'bg-orange-500',
                    I: 'bg-teal-500', J: 'bg-pink-500', K: 'bg-lime-600', L: 'bg-purple-500',
                    M: 'bg-sky-500', N: 'bg-red-500', O: 'bg-green-500', P: 'bg-fuchsia-500',
                    Q: 'bg-yellow-600', R: 'bg-blue-600', S: 'bg-emerald-600', T: 'bg-violet-600',
                    U: 'bg-amber-600', V: 'bg-rose-600', W: 'bg-cyan-600', X: 'bg-indigo-600',
                    Y: 'bg-orange-600', Z: 'bg-teal-600',
                  };
                  const getLetterColor = (letter: string) => LETTER_COLORS[letter.toUpperCase()] || 'bg-gray-500';
                  const ALPHA_GROUPED = ['Manufacturers', 'Models'];

                  const searchLower = tagSearch.toLowerCase();
                  const grouped = tags.reduce((acc, tag) => {
                    const group = tag.group_name || 'General';
                    if (!acc[group]) acc[group] = [];
                    acc[group].push(tag);
                    return acc;
                  }, {} as Record<string, Tag[]>);

                  return Object.entries(grouped)
                    .sort(([a], [b]) => {
                      if (a === 'General') return 1;
                      if (b === 'General') return -1;
                      return a.localeCompare(b);
                    })
                    .map(([groupName, groupTags]) => {
                      const filteredTags = tagSearch
                        ? groupTags.filter(t => t.name.toLowerCase().includes(searchLower))
                        : groupTags;

                      if (tagSearch && filteredTags.length === 0) return null;

                      const selectedCount = groupTags.filter(t => formData.tags.includes(t.id)).length;
                      const isCollapsed = collapsedGroups.has(groupName) && !tagSearch;

                      const toggleCollapse = () => {
                        setCollapsedGroups(prev => {
                          const next = new Set(prev);
                          if (next.has(groupName)) next.delete(groupName);
                          else next.add(groupName);
                          return next;
                        });
                      };

                      const renderTagButton = (tag: Tag) => (
                        <button
                          key={tag.id}
                          type="button"
                          onClick={() => handleTagToggle(tag.id)}
                          className={`px-3 py-1.5 rounded-lg text-sm font-semibold transition-all border-2 ${formData.tags.includes(tag.id)
                            ? 'bg-indigo-600 border-indigo-600 text-white shadow-md scale-105'
                            : 'bg-white border-gray-200 text-gray-700 hover:border-indigo-300 hover:text-indigo-600 hover:bg-indigo-50/50'
                            }`}
                        >
                          {tag.name}
                          {formData.tags.includes(tag.id) && (
                            <span className="ml-1.5 inline-flex items-center justify-center w-4 h-4 bg-white/20 rounded-full text-[10px]">✓</span>
                          )}
                        </button>
                      );

                      return (
                        <div key={groupName} className="bg-gray-50/50 rounded-xl border border-gray-100 overflow-hidden">
                          <button
                            type="button"
                            onClick={toggleCollapse}
                            className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-100/50 transition-colors"
                          >
                            <span className="flex items-center gap-2 text-sm font-black text-indigo-900 uppercase tracking-wider">
                              <span className="w-2 h-2 bg-indigo-600 rounded-full"></span>
                              {groupName}
                              {selectedCount > 0 && (
                                <span className="ml-1 px-2 py-0.5 bg-indigo-600 text-white text-[10px] font-bold rounded-full normal-case tracking-normal">
                                  {selectedCount}
                                </span>
                              )}
                            </span>
                            <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isCollapsed ? '' : 'rotate-180'}`} />
                          </button>

                          {!isCollapsed && (
                            <div className="px-4 pb-4">
                              {/* Alphabet quick-filter for Manufacturers & Models */}
                              {ALPHA_GROUPED.includes(groupName) && (() => {
                                const existingLetters = new Set(filteredTags.map(t => (t.name[0] || '').toUpperCase()));
                                const activeLetter = letterFilter[groupName] || null;
                                return (
                                  <div className="flex flex-wrap gap-1 mb-3 pb-3 border-b border-gray-100">
                                    <button
                                      type="button"
                                      onClick={() => setLetterFilter(prev => ({ ...prev, [groupName]: null }))}
                                      className={`px-2 py-0.5 rounded text-[11px] font-bold transition-all ${!activeLetter
                                        ? 'bg-indigo-600 text-white shadow-sm'
                                        : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
                                        }`}
                                    >
                                      All
                                    </button>
                                    {'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').map(letter => {
                                      const hasItems = existingLetters.has(letter);
                                      const isActive = activeLetter === letter;
                                      return (
                                        <button
                                          key={letter}
                                          type="button"
                                          onClick={() => hasItems && setLetterFilter(prev => ({
                                            ...prev,
                                            [groupName]: isActive ? null : letter
                                          }))}
                                          className={`w-6 h-6 rounded text-[11px] font-bold transition-all flex items-center justify-center ${isActive
                                            ? `${getLetterColor(letter)} text-white shadow-sm`
                                            : hasItems
                                              ? 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                                              : 'text-gray-200 cursor-default'
                                            }`}
                                        >
                                          {letter}
                                        </button>
                                      );
                                    })}
                                  </div>
                                );
                              })()}

                              {/* Tag pills */}
                              <div className="flex flex-wrap gap-2">
                                {(() => {
                                  const activeLetter = letterFilter[groupName] || null;
                                  const visibleTags = ALPHA_GROUPED.includes(groupName) && activeLetter
                                    ? filteredTags.filter(t => (t.name[0] || '').toUpperCase() === activeLetter)
                                    : filteredTags;
                                  return visibleTags.map(renderTagButton);
                                })()}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })
                    .filter(Boolean);
                })()}
              </div>
            </div>

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
      {photoSearchOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setPhotoSearchOpen(false)}
        >
          <div
            className="relative bg-white rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b bg-gradient-to-r from-emerald-50 to-teal-50">
              <div>
                <h3 className="text-lg font-bold text-gray-900">🔍 Find Press Photo</h3>
                <p className="text-sm text-gray-500">Image Slot {photoSearchSlot} — select a photo to save</p>
              </div>
              <button
                onClick={() => setPhotoSearchOpen(false)}
                className="p-2 hover:bg-gray-200 rounded-full transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Search Bar */}
            <div className="px-6 py-3 border-b bg-gray-50">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={photoSearchQuery}
                  onChange={(e) => setPhotoSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && searchPhotosCustom()}
                  placeholder="Search for car photos..."
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm text-gray-900"
                />
                <button
                  onClick={searchPhotosCustom}
                  disabled={photoSearchLoading}
                  className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors text-sm font-medium disabled:opacity-50"
                >
                  {photoSearchLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Search'}
                </button>
              </div>
            </div>

            {/* Results Grid */}
            <div className="flex-1 overflow-y-auto p-6">
              {photoSearchLoading && photoSearchResults.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-gray-500">
                  <Loader2 className="w-10 h-10 animate-spin text-emerald-500 mb-3" />
                  <p className="text-sm font-medium">Searching for photos...</p>
                </div>
              ) : photoSearchResults.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-gray-400">
                  <Search className="w-10 h-10 mb-3" />
                  <p className="text-sm font-medium">No photos found. Try a different search query.</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {photoSearchResults.map((photo, index) => (
                    <div
                      key={index}
                      className={`group relative rounded-xl overflow-hidden border-2 transition-all cursor-pointer hover:shadow-lg ${savingPhoto === photo.url
                        ? 'border-emerald-500 ring-2 ring-emerald-200'
                        : 'border-gray-200 hover:border-emerald-400'
                        }`}
                      onClick={() => !savingPhoto && selectPhoto(photo.url)}
                    >
                      <div className="aspect-[4/3] bg-gray-100">
                        <img
                          src={photo.thumbnail}
                          alt={photo.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          loading="lazy"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none';
                          }}
                        />
                      </div>
                      {/* Overlay on hover */}
                      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-3">
                        <p className="text-white text-xs font-medium line-clamp-2">{photo.title}</p>
                        <p className="text-white/70 text-[10px] mt-0.5">{photo.source}</p>
                        {photo.width > 0 && (
                          <p className="text-white/50 text-[10px]">{photo.width}×{photo.height}</p>
                        )}
                      </div>
                      {/* License badge */}
                      {photo.license === 'editorial' && (
                        <span className="absolute top-2 left-2 bg-emerald-500 text-white text-[10px] px-1.5 py-0.5 rounded-full font-bold shadow" title="From press/manufacturer site — safe for editorial use">
                          ✅ EDITORIAL
                        </span>
                      )}
                      {photo.license === 'cc' && (
                        <span className="absolute top-2 left-2 bg-blue-500 text-white text-[10px] px-1.5 py-0.5 rounded-full font-bold shadow" title="Creative Commons — free to use with attribution">
                          🆓 CC
                        </span>
                      )}
                      {photo.license === 'unknown' && (
                        <span className="absolute top-2 left-2 bg-amber-500 text-white text-[10px] px-1.5 py-0.5 rounded-full font-bold shadow" title="Unknown license — verify before commercial use">
                          ⚠️ CHECK
                        </span>
                      )}
                      {/* Download button */}
                      <a
                        href={photo.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        download
                        className="absolute top-2 right-2 p-1.5 bg-black/60 hover:bg-black/80 text-white rounded-lg opacity-0 group-hover:opacity-100 transition-opacity shadow-lg"
                        title="Open full-res image (right-click → Save As)"
                      >
                        <Download className="w-4 h-4" />
                      </a>
                      {/* Saving spinner */}
                      {savingPhoto === photo.url && (
                        <div className="absolute inset-0 bg-white/80 flex items-center justify-center">
                          <div className="flex flex-col items-center">
                            <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
                            <p className="text-xs font-medium text-emerald-700 mt-1">Saving...</p>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            {photoSearchResults.length > 0 && (
              <div className="px-6 py-3 border-t bg-gray-50 text-xs text-gray-500">
                <div className="flex justify-between items-center">
                  <span>{photoSearchResults.length} photos found — click to save, ⬇ to download</span>
                  <span>Image Slot {photoSearchSlot}</span>
                </div>
                <div className="flex gap-4 mt-1.5 text-[10px]">
                  <span><span className="inline-block w-2 h-2 rounded-full bg-emerald-500 mr-1" />EDITORIAL — press/manufacturer, safe for reviews</span>
                  <span><span className="inline-block w-2 h-2 rounded-full bg-blue-500 mr-1" />CC — Creative Commons, free with attribution</span>
                  <span><span className="inline-block w-2 h-2 rounded-full bg-amber-500 mr-1" />CHECK — verify license before publishing</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

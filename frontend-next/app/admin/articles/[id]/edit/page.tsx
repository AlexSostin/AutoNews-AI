'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Save, Plus, X, Sparkles, Loader2, Search, ChevronDown, Zap, Lock, Unlock } from 'lucide-react';
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
  const [tagSearch, setTagSearch] = useState('');
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [letterFilter, setLetterFilter] = useState<Record<string, string | null>>({});
  const [slugEditable, setSlugEditable] = useState(false);

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
            <h3 className="text-lg font-bold text-gray-900 mb-4">Images</h3>
            <p className="text-sm text-gray-600 mb-4">Replace images or keep existing ones from AI generation</p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Image 1 */}
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Image 1 (Main)</label>
                {formData.current_image && !formData.delete_image && (
                  <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-gray-200 group">
                    <img
                      src={formData.current_image}
                      alt="Current Image 1"
                      className="w-full h-full object-cover"
                    />
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
              </div>

              {/* Image 2 */}
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Image 2</label>
                {formData.current_image_2 && !formData.delete_image_2 && (
                  <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-gray-200">
                    <img
                      src={formData.current_image_2}
                      alt="Current Image 2"
                      className="w-full h-full object-cover"
                    />
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
              </div>

              {/* Image 3 */}
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Image 3</label>
                {formData.current_image_3 && !formData.delete_image_3 && (
                  <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-gray-200">
                    <img
                      src={formData.current_image_3}
                      alt="Current Image 3"
                      className="w-full h-full object-cover"
                    />
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
  );
}

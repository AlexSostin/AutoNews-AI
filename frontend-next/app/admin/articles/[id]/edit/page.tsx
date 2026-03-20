/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @next/next/no-img-element */
/* eslint-disable react-hooks/exhaustive-deps */
'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { X } from 'lucide-react';
import api from '@/lib/api';
import { PhotoSearchModal } from './components/PhotoSearchModal';
import { TagSelector, Category, Tag } from './components/TagSelector';
// GallerySection kept for GallerySectionRef type only — gallery is now managed inside ArticleImageManager
import { PageHeader } from '../../../components/ui/PageHeader';
import { ArticleBasicInfo } from '../../components/ArticleBasicInfo';
import { ArticleContentEditor } from '../../components/ArticleContentEditor';
import { ArticleSeoMeta } from '../../components/ArticleSeoMeta';
import { ArticlePublishSettings } from '../../components/ArticlePublishSettings';
import { ArticleImageManager } from '../../components/ArticleImageManager';
import { useGenerationStore, percentToStep } from '@/lib/useGenerationStore';

export default function EditArticlePage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const [articleId, setArticleId] = useState<string | null>(null);
  const [articleSlug, setArticleSlug] = useState<string | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [reformatting, setReformatting] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [autoResolving, setAutoResolving] = useState(false);

  const [generatingAI, setGeneratingAI] = useState<number | null>(null);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [restoringYT, setRestoringYT] = useState(false);
  // Find Photo state
  const [photoSearchOpen, setPhotoSearchOpen] = useState(false);
  const [photoSearchSlot, setPhotoSearchSlot] = useState(1);
  const [photoSearchResults, setPhotoSearchResults] = useState<any[]>([]);
  const [photoSearchLoading, setPhotoSearchLoading] = useState(false);
  const [photoSearchQuery, setPhotoSearchQuery] = useState('');
  const [savingPhoto, setSavingPhoto] = useState<string | null>(null);
  const [imageSource, setImageSource] = useState<string>('unknown');
  // Gallery state is now managed internally by ArticleImageManager
  // Content backups per slot — used to restore <figure> on Undo
  const contentBackups = useRef<Record<number, string>>({});

  /**
   * Sync article HTML content when an image slot changes.
   * - If newUrl is null (deletion): remove the <figure> block containing the old image
   * - If newUrl is provided (replacement): update the <img src> in content
   */
  const syncContentWithSlotImage = (oldUrl: string | null, newUrl: string | null, slot?: number) => {
    if (!oldUrl && !slot) return; // nothing to sync

    // RESTORE mode: if oldUrl is null but slot is provided, restore from backup
    if (!oldUrl && slot && contentBackups.current[slot]) {
      setFormData((prev: any) => ({
        ...prev,
        content: contentBackups.current[slot],
      }));
      delete contentBackups.current[slot];
      return;
    }

    if (!oldUrl) return;

    setFormData((prev: any) => {
      let content = prev.content || '';
      if (!content) return prev;

      // Extract just the pathname/filename from the URL for flexible matching
      const extractPath = (url: string) => {
        try {
          const u = new URL(url);
          return u.pathname;
        } catch {
          return url;
        }
      };
      const oldPath = extractPath(oldUrl);

      if (newUrl) {
        // REPLACE: swap src attribute in any <img> that matches the old URL
        const escapedOld = oldUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const escapedPath = oldPath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const srcPattern = new RegExp(
          `(<img\\b[^>]*\\bsrc=["'])(?:[^"']*${escapedPath}|${escapedOld})(["'])`,
          'gi'
        );
        content = content.replace(srcPattern, `$1${newUrl}$2`);
      } else {
        // DELETE: save backup before removing (for Undo)
        if (slot) {
          contentBackups.current[slot] = content;
        }

        // Remove only the specific <figure> block containing this image
        content = content.replace(
          /\s*<figure[^>]*article-inline-image[^>]*>[\s\S]*?<\/figure>\s*/gi,
          (match: string) => match.includes(oldPath) || match.includes(oldUrl!) ? '\n' : match
        );

        // Fallback: also try standalone <img> (not wrapped in figure)
        const escapedPath = oldPath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const imgPattern = new RegExp(
          `\\s*<img[^>]*src=["'][^"']*${escapedPath}["'][^>]*/?>\\s*`,
          'gi'
        );
        content = content.replace(imgPattern, '\n');
      }

      return { ...prev, content };
    });
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

  // Restore YouTube thumbnail for Image 1
  const restoreYouTubeThumbnail = async () => {
    if (!articleId || !formData.youtube_url || restoringYT) return;
    // Extract video ID from various YouTube URL formats
    const match = formData.youtube_url.match(/(?:v=|youtu\.be\/|embed\/|shorts\/)([a-zA-Z0-9_-]{11})/);
    if (!match) {
      alert('❌ Could not extract video ID from YouTube URL');
      return;
    }
    const videoId = match[1];
    const thumbUrl = `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`;
    setRestoringYT(true);
    try {
      const response = await api.post(`/articles/${articleId}/save-external-image/`, {
        image_url: thumbUrl,
        image_slot: 1,
      });
      if (response.data.success) {
        setFormData((prev: any) => ({ ...prev, current_image: response.data.image_url, delete_image: false, image: null }));
        setImageSource('youtube');
        alert('✅ YouTube thumbnail restored!');
      }
    } catch (error: any) {
      alert(`❌ Failed to restore thumbnail: ${error?.response?.data?.error || error.message}`);
    } finally {
      setRestoringYT(false);
    }
  };

  const [formData, setFormData] = useState({
    title: '',
    slug: '',
    summary: '',
    seo_description: '',
    content: '',
    category_ids: [] as number[],
    tags: [] as number[],
    published: false,
    is_hero: false,
    is_news_only: false,
    scheduled_publish_at: '',
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
      // Store the article slug — needed for slug-based API endpoints like auto-resolve-fact-check
      setArticleSlug(article.slug || null);

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
        seo_description: article.seo_description || '',
        content: article.content || '',
        category_ids: Array.isArray(article.categories) ? article.categories.map((cat: any) => cat.id) : [],
        tags: Array.isArray(article.tags) ? article.tags.map((tag: any) => tag.id) : [],
        published: article.is_published ?? false,
        is_hero: article.is_hero ?? false,
        is_news_only: article.is_news_only ?? false,
        scheduled_publish_at: article.scheduled_publish_at
          ? new Date(new Date(article.scheduled_publish_at).getTime() - new Date().getTimezoneOffset() * 60_000).toISOString().slice(0, 16)
          : '',
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

      // Fetch gallery images is now handled internally by GallerySection
    } catch (error) {
      console.error('Failed to fetch data:', error);
      alert('Failed to load article');
    } finally {
      setLoading(false);
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
        formDataToSend.append('slug', formData.slug);
        formDataToSend.append('summary', formData.summary);
        formDataToSend.append('seo_description', formData.seo_description);
        formDataToSend.append('content', formData.content);
        formData.category_ids.forEach(id => formDataToSend.append('category_ids', id.toString()));
        formData.tags.forEach(id => formDataToSend.append('tag_ids', id.toString()));
        formDataToSend.append('is_published', formData.published.toString());
        formDataToSend.append('is_hero', formData.is_hero.toString());
        formDataToSend.append('is_news_only', formData.is_news_only.toString());
        if (formData.scheduled_publish_at) {
          formDataToSend.append('scheduled_publish_at', new Date(formData.scheduled_publish_at).toISOString());
        } else {
          formDataToSend.append('scheduled_publish_at', '');
        }

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
          seo_description: formData.seo_description,
          content: formData.content,
          category_ids: formData.category_ids,
          tag_ids: formData.tags,
          is_published: formData.published,
          is_hero: formData.is_hero,
          is_news_only: formData.is_news_only,
          scheduled_publish_at: formData.scheduled_publish_at
            ? new Date(formData.scheduled_publish_at).toISOString()
            : null,
          youtube_url: formData.youtube_url,
          author_name: formData.author_name,
          author_channel_url: formData.author_channel_url,
          show_source: formData.show_source,
          show_youtube: formData.show_youtube,
          show_price: formData.show_price,
          image_source: imageSource,
        };
        payload.slug = formData.slug;

        await api.put(`/articles/${articleId}/`, payload);
      }


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
        <PageHeader
          title="Edit Article"
          backHref="/admin/articles"
          onSave={() => handleSubmit({ preventDefault: () => { } } as React.FormEvent)}
          isSaving={saving}
        />

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 1. Basic Info: Title, Slug, Summary, SEO Description */}
          <ArticleBasicInfo
            title={formData.title}
            slug={formData.slug}
            summary={formData.summary}
            seoDescription={formData.seo_description}
            onTitleChange={(v: string) => setFormData({ ...formData, title: v })}
            onSlugChange={(v: string) => setFormData({ ...formData, slug: v })}
            onSummaryChange={(v: string) => setFormData({ ...formData, summary: v })}
            onSeoDescriptionChange={(v: string) => setFormData({ ...formData, seo_description: v })}
          />

          {/* 2. Article Content (WYSIWYG Editor) */}
          <ArticleContentEditor
            content={formData.content}
            articleContext={{
              title: formData.title,
              tags: tags.filter(t => formData.tags.includes(t.id)).map(t => t.name),
              summary: formData.summary,
              content: formData.content, // Will be overridden by the editor's live content
            }}
            onContentChange={(v: string) => setFormData({ ...formData, content: v })}
            onReformat={async () => {
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
            onEnrich={async () => {
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
            onRegenerate={async () => {
              if (!articleId) return;
              const isYoutube = !!formData.youtube_url;
              const confirmMsg = isYoutube
                ? '🔄 REGENERATE ARTICLE?\n\nThis will:\n• Re-download YouTube transcript\n• Re-generate title, content, summary\n• Update tags, specs, A/B titles\n\n⚠️ Current content will be backed up but REPLACED!\n\nContinue?'
                : '🔄 REGENERATE RSS ARTICLE?\n\nThis will:\n• Re-expand the original press release with AI\n• Re-generate title, content, summary\n• Update A/B titles\n\n⚠️ Current content will be backed up but REPLACED!\n\nContinue?';
              if (!confirm(confirmMsg)) return;
              setRegenerating(true);
              const genLabel = formData.title || articleId || 'Article';
              useGenerationStore.getState().startGeneration(genLabel);
              try {
                const { data: startData } = await api.post(`/articles/${articleId}/regenerate/`, {
                  provider: 'gemini',
                });
                
                if (startData.success && startData.task_id) {
                  const taskId = startData.task_id;
                  let pollCount = 0;
                  
                  const poll = async (): Promise<void> => {
                    try {
                      const statusRes = await api.get(`/articles/regenerate_status/`, {
                        params: { task_id: taskId }
                      });
                      const data = statusRes.data;
                      
                      if (data.status === 'done') {
                        useGenerationStore.getState().finishGeneration(formData.slug || articleId!);
                        window.location.reload();
                        return;
                      }
                      
                      if (data.status === 'error') {
                        const isTimeout = !!data.result?.timeout;
                        useGenerationStore.getState().failGeneration(data.error || 'Regeneration failed', isTimeout);
                        setRegenerating(false);
                        return;
                      }
                      
                      // Advance drawer progress on each tick (caps at 95%)
                      pollCount++;
                      const pct = Math.min(5 + pollCount * 6, 95);
                      useGenerationStore.getState().updateProgress(pct, percentToStep(pct));

                      // Still running
                      await new Promise(r => setTimeout(r, 3000));
                      return poll();
                    } catch (err: any) {
                      const errMsg = err.response?.data?.error || err.message || 'Polling error';
                      useGenerationStore.getState().failGeneration(errMsg);
                      setRegenerating(false);
                    }
                  };
                  
                  await poll();
                } else {
                  const errMsg = startData.message || 'Failed to start regeneration';
                  useGenerationStore.getState().failGeneration(errMsg);
                  setRegenerating(false);
                }
              } catch (err: any) {
                const errMsg = err.response?.data?.message || err.message || 'Error starting regeneration';
                useGenerationStore.getState().failGeneration(errMsg);
                setRegenerating(false);
              }
            }}
            isReformatting={reformatting}
            isEnriching={enriching}
            isRegenerating={regenerating}
            hasYoutubeUrl={!!formData.youtube_url}
            isAutoResolving={autoResolving}
            onAutoResolve={async () => {
              if (!articleId || autoResolving) return;
              if (!confirm('🔧 Auto-Resolve Fact-Check?\n\nAI will:\n• Re-fetch web sources for this car\n• Replace wrong numbers with correct ones from web\n• Keep unverified numbers with a caveat note\n• Remove ONLY directly contradicted claims\n\nThe article will be updated automatically.')) return;
              setAutoResolving(true);
              try {
                const { data } = await api.post(`/articles/${articleSlug || articleId}/auto-resolve-fact-check/`, { provider: 'gemini' });
                if (data.success) {
                  const replaced = data.replaced?.length || 0;
                  const caveated = data.caveated?.length || 0;
                  const removed = data.removed?.length || 0;
                  const warning = data.warning ? `\n\n⚠️ ${data.warning}` : '';
                  alert(`✅ Done!\n\nReplaced: ${replaced} claims with correct values\nCaveated: ${caveated} claims (kept with note)\nRemoved: ${removed} contradicted claims${warning}\n\nPage will reload to show updated content.`);
                  window.location.reload();
                } else {
                  alert(`❌ ${data.message || 'Auto-resolve failed'}`);
                }
              } catch (err: any) {
                alert(`❌ Error: ${err.response?.data?.error || err.message}`);
              } finally {
                setAutoResolving(false);
              }
            }}
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

          {/* 4. Source & Display Settings */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="border-b border-gray-100 bg-gray-50/50 p-6 flex items-center gap-3">
              <div className="p-2 bg-white rounded-lg shadow-sm">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-500"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></svg>
              </div>
              <h2 className="text-lg font-semibold text-gray-900">Source & Display</h2>
            </div>
            <div className="p-6 space-y-4">
              <div className={`grid grid-cols-1 md:grid-cols-2 gap-4 transition-opacity ${!formData.show_source ? 'opacity-50' : ''}`}>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">Content Source</label>
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, show_source: !formData.show_source })}
                      className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium transition-all ${formData.show_source
                        ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                        : 'bg-gray-200 text-gray-500 hover:bg-gray-300'
                        }`}
                      title={formData.show_source ? 'Visible on public page' : 'Hidden from public page'}
                    >
                      {formData.show_source ? 'Visible' : 'Hidden'}
                    </button>
                  </div>
                  <input
                    type="text"
                    value={formData.author_name}
                    onChange={(e) => setFormData({ ...formData, author_name: e.target.value })}
                    placeholder="e.g., Toyota Global, Doug DeMuro, Carwow"
                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-gray-900"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Source URL</label>
                  <input
                    type="url"
                    value={formData.author_channel_url}
                    onChange={(e) => setFormData({ ...formData, author_channel_url: e.target.value })}
                    placeholder="https://global.toyota/... or YouTube channel"
                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-gray-900"
                  />
                </div>
              </div>

              {/* Price Visibility Toggle */}
              <div className="flex items-center justify-between py-3 px-4 bg-gray-50 rounded-xl border border-gray-200">
                <div>
                  <span className="text-sm font-medium text-gray-900">💰 Price Display</span>
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
                  {formData.show_price ? 'Visible' : 'Hidden'}
                </button>
              </div>
            </div>
          </div>

          {/* 5. Images */}
          <ArticleImageManager
            formData={formData}
            setFormData={setFormData}
            imageSource={imageSource}
            setImageSource={setImageSource}
            setPreviewImage={setPreviewImage}
            openPhotoSearch={openPhotoSearch}
            photoSearchLoading={photoSearchLoading}
            generateAIImage={async (slot: number, aiStyle: string, aiMode: string, aiCustomPrompt: string) => {
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
                  if (slot === 2) {
                    syncContentWithSlotImage(formData.current_image_2, url);
                    setFormData(prev => ({ ...prev, current_image_2: url, delete_image_2: false, image_2: null }));
                  }
                  if (slot === 3) {
                    syncContentWithSlotImage(formData.current_image_3, url);
                    setFormData(prev => ({ ...prev, current_image_3: url, delete_image_3: false, image_3: null }));
                  }
                  alert('✅ AI image generated and saved!');
                }
              } catch (error: any) {
                const msg = error?.response?.data?.error || 'Failed to generate AI image';
                alert(`❌ ${msg}`);
              } finally {
                setGeneratingAI(null);
              }
            }}
            generatingAI={generatingAI}
            restoreYouTubeThumbnail={restoreYouTubeThumbnail}
            restoringYT={restoringYT}
            articleId={articleId}
            onSlotChange={(slot, oldUrl, newUrl) => {
              if (slot >= 2) syncContentWithSlotImage(oldUrl, newUrl, slot);
            }}
          />

          {/* 7. Publish Settings (at the bottom) */}
          <ArticlePublishSettings
            isPublished={formData.published}
            isHero={formData.is_hero}
            isNewsOnly={formData.is_news_only}
            scheduledPublishAt={formData.scheduled_publish_at}
            onPublishedChange={(v: boolean) => setFormData({ ...formData, published: v })}
            onHeroChange={(v: boolean) => setFormData({ ...formData, is_hero: v })}
            onNewsOnlyChange={(v: boolean) => setFormData({ ...formData, is_news_only: v })}
            onScheduledPublishAtChange={(v: string) => setFormData({ ...formData, scheduled_publish_at: v })}
          />

          {/* 8. Bottom Save Button */}
          <div className="flex justify-end gap-3 pt-2 pb-6">
            <button
              type="button"
              onClick={async () => {
                if (!articleId) return;
                if (!confirm('🔧 Repair compare-grid HTML?\n\nThis will fix malformed compare-grid structures in article content.')) return;
                try {
                  const { data } = await api.post(`/articles/${articleId}/repair-html/`);
                  alert(data.repaired ? `✅ ${data.message}\n\nPage will reload.` : `✓ ${data.message}`);
                  if (data.repaired) window.location.reload();
                } catch (err: any) {
                  alert(`❌ ${err.response?.data?.detail || err.message}`);
                }
              }}
              className="px-4 py-2.5 text-sm font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-xl hover:bg-amber-100 transition-colors"
            >
              🔧 Repair HTML
            </button>
            <button
              type="button"
              onClick={() => router.push('/admin/articles')}
              className="px-5 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-xl hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2.5 text-sm font-semibold text-white bg-indigo-600 rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm flex items-center gap-2"
            >
              {saving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                  Saving...
                </>
              ) : (
                'Save Article'
              )}
            </button>
          </div>
        </form>
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

import React, { useRef } from 'react';
// Import TinyMCE so it's bundled locally (self-hosted, no API key needed)
import 'tinymce/tinymce';
// Default icons, required for the editor UI
import 'tinymce/icons/default';
// Theme
import 'tinymce/themes/silver';
// Skin
import 'tinymce/skins/ui/oxide/skin.min.css';
// Plugins
import 'tinymce/plugins/advlist';
import 'tinymce/plugins/autolink';
import 'tinymce/plugins/lists';
import 'tinymce/plugins/link';
import 'tinymce/plugins/image';
import 'tinymce/plugins/charmap';
import 'tinymce/plugins/preview';
import 'tinymce/plugins/anchor';
import 'tinymce/plugins/searchreplace';
import 'tinymce/plugins/visualblocks';
import 'tinymce/plugins/code';
import 'tinymce/plugins/fullscreen';
import 'tinymce/plugins/insertdatetime';
import 'tinymce/plugins/media';
import 'tinymce/plugins/table';
import 'tinymce/plugins/wordcount';
// Model (required for TinyMCE 7+)
import 'tinymce/models/dom';

// @ts-ignore - TinyMCE types might be missing in package.json
import { Editor } from '@tinymce/tinymce-react';
import { FormCard } from '@/app/admin/components/forms/FormCard';
import { FileText, Sparkles, Loader2, Zap, RefreshCw } from 'lucide-react';

interface ArticleContentEditorProps {
    content: string;
    onContentChange: (v: string) => void;
    onReformat: () => void;
    onEnrich: () => void;
    onRegenerate: () => void;
    isReformatting: boolean;
    isEnriching: boolean;
    isRegenerating: boolean;
    hasYoutubeUrl: boolean;
}

export function ArticleContentEditor({
    content,
    onContentChange,
    onReformat,
    onEnrich,
    onRegenerate,
    isReformatting,
    isEnriching,
    isRegenerating,
    hasYoutubeUrl
}: ArticleContentEditorProps) {
    const editorRef = useRef<any>(null);

    const CustomToolbar = () => (
        <div className="flex gap-2">
            <button
                type="button"
                onClick={onReformat}
                disabled={isReformatting || !content.trim()}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg text-xs font-bold hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
            >
                {isReformatting ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                {isReformatting ? 'Reformatting...' : '✨ Reformat with AI'}
            </button>
            <button
                type="button"
                onClick={onEnrich}
                disabled={isEnriching || isReformatting}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-lg text-xs font-bold hover:from-emerald-700 hover:to-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
            >
                {isEnriching ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
                {isEnriching ? 'Enriching...' : '⚡ Re-enrich Specs'}
            </button>
            <button
                type="button"
                onClick={onRegenerate}
                disabled={isRegenerating || isReformatting || isEnriching}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg text-xs font-bold hover:from-orange-600 hover:to-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
                title={hasYoutubeUrl ? 'Regenerate article from YouTube' : 'Regenerate article from RSS source'}
            >
                {isRegenerating ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                {isRegenerating ? 'Regenerating...' : '🔄 Regenerate'}
            </button>
        </div>
    );

    return (
        <FormCard
            title="Article Content"
            icon={<FileText className="text-blue-500" size={20} />}
            action={<CustomToolbar />}
        >
            <div className="rounded-xl overflow-hidden border border-gray-200 shadow-sm [&_.tox-tinymce]:border-0">
                <Editor
                    licenseKey="gpl"
                    onInit={(evt: any, editor: any) => editorRef.current = editor}
                    value={content}
                    onEditorChange={(newContent: string) => onContentChange(newContent)}
                    init={{
                        height: 800,
                        menubar: true,
                        skin: false,
                        content_css: false,
                        plugins: [
                            'advlist', 'autolink', 'lists', 'link', 'image', 'charmap', 'preview',
                            'anchor', 'searchreplace', 'visualblocks', 'code', 'fullscreen',
                            'insertdatetime', 'media', 'table', 'wordcount'
                        ],
                        toolbar: 'undo redo | blocks | ' +
                            'bold italic forecolor | alignleft aligncenter ' +
                            'alignright alignjustify | bullist numlist outdent indent | ' +
                            'removeformat | image media link',
                        content_style: `
              body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
                font-size: 16px; 
                line-height: 1.6;
                color: #374151;
                background-color: #ffffff;
              }
              img { max-width: 100%; height: auto; border-radius: 8px; }
              h2, h3, h4 { color: #111827; font-weight: 600; margin-top: 1.5em; }
              p { margin-bottom: 1em; }
              a { color: #4f46e5; text-decoration: none; }
              a:hover { text-decoration: underline; }
            `,

                    }}
                />
            </div>
        </FormCard>
    );
}

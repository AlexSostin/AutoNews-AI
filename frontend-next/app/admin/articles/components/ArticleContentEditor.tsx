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

import { Editor } from '@tinymce/tinymce-react';
import { FormCard } from '@/app/admin/components/forms/FormCard';
import { FileText, Sparkles, Loader2, Zap, RefreshCw, Wand2, Wrench } from 'lucide-react';
import api from '@/lib/api';

interface ArticleContentEditorProps {
    content: string;
    onContentChange: (v: string) => void;
    onReformat: () => void;
    onEnrich: () => void;
    onRegenerate: () => void;
    onRegenerateSeo?: () => void;
    onAutoFill?: () => void;
    onAutoResolve?: () => void;
    isReformatting: boolean;
    isEnriching: boolean;
    isRegenerating: boolean;
    isRegeneratingSeo?: boolean;
    isAutoFilling?: boolean;
    isAutoResolving?: boolean;
    hasYoutubeUrl: boolean;
    articleSlug?: string;
    articleContext?: {
        title: string;
        tags: string[];
        summary: string;
        content: string;
    };
    onEditorChange?: (v: string) => void;
}

const CustomToolbar = ({
    onReformat,
    onEnrich,
    onRegenerate,
    onRegenerateSeo,
    onAutoFill,
    onAutoResolve,
    isReformatting,
    isEnriching,
    isRegenerating,
    isRegeneratingSeo,
    isAutoFilling,
    isAutoResolving,
    hasYoutubeUrl,
    content
}: {
    onReformat: () => void;
    onEnrich: () => void;
    onRegenerate: () => void;
    onRegenerateSeo?: () => void;
    onAutoFill?: () => void;
    onAutoResolve?: () => void;
    isReformatting: boolean;
    isEnriching: boolean;
    isRegenerating: boolean;
    isRegeneratingSeo?: boolean;
    isAutoFilling?: boolean;
    isAutoResolving?: boolean;
    hasYoutubeUrl: boolean;
    content: string;
}) => (
    <div className="flex gap-2">
        <button
            type="button"
            onClick={onReformat}
            disabled={isReformatting || !content?.trim()}
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
        {onRegenerateSeo && (
            <button
                type="button"
                onClick={onRegenerateSeo}
                disabled={isRegeneratingSeo || isReformatting || !content.trim()}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-blue-500 to-indigo-500 text-white rounded-lg text-xs font-bold hover:from-blue-600 hover:to-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
                title="Regenerate Title, Summary and SEO Description from article body"
            >
                {isRegeneratingSeo ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />}
                {isRegeneratingSeo ? 'Generating...' : '🪄 Regenerate SEO'}
            </button>
        )}
        {onAutoFill && (
            <button
                type="button"
                onClick={onAutoFill}
                disabled={isAutoFilling || isReformatting || !content.trim()}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-lg text-xs font-bold hover:from-amber-600 hover:to-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
                title="Extract title, summary, tags from content"
            >
                {isAutoFilling ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />}
                {isAutoFilling ? 'Extracting...' : '🪄 Auto-fill'}
            </button>
        )}
        {/* Auto-Resolve button — only shown when fact-check warning is in content */}
        {onAutoResolve && (content.includes('ai-editor-note') || content.includes('ai-fact-check-block')) && (
            <button
                type="button"
                onClick={onAutoResolve}
                disabled={isAutoResolving || isReformatting}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-lg text-xs font-bold hover:from-amber-600 hover:to-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
                title="Auto-fix fact-check warnings using original web sources"
            >
                {isAutoResolving ? <Loader2 size={14} className="animate-spin" /> : <Wrench size={14} />}
                {isAutoResolving ? 'Resolving...' : '🔧 Auto-Resolve'}
            </button>
        )}
    </div>
);

export function ArticleContentEditor({
    content,
    onContentChange,
    onReformat,
    onEnrich,
    onRegenerate,
    onRegenerateSeo,
    onAutoFill,
    onAutoResolve,
    isReformatting,
    isEnriching,
    isRegenerating,
    isRegeneratingSeo,
    isAutoFilling,
    isAutoResolving,
    hasYoutubeUrl,
    articleSlug,
    articleContext,
    onEditorChange,
}: ArticleContentEditorProps) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const editorRef = useRef<any>(null);

    return (
        <FormCard
            title="Article Content"
            icon={<FileText className="text-blue-500" size={20} />}
            action={
                <CustomToolbar
                    onReformat={onReformat}
                    onEnrich={onEnrich}
                    onRegenerate={onRegenerate}
                    onRegenerateSeo={onRegenerateSeo}
                    onAutoFill={onAutoFill}
                    onAutoResolve={onAutoResolve}
                    isReformatting={isReformatting}
                    isEnriching={isEnriching}
                    isRegenerating={isRegenerating}
                    isRegeneratingSeo={isRegeneratingSeo}
                    isAutoFilling={isAutoFilling}
                    isAutoResolving={isAutoResolving}
                    hasYoutubeUrl={hasYoutubeUrl}
                    content={content}
                />
            }
        >
            <div className="rounded-xl overflow-hidden border border-gray-200 shadow-sm [&_.tox-tinymce]:border-0">
                <Editor
                    licenseKey="gpl"
                    onInit={(_evt: unknown, editor: unknown) => { editorRef.current = editor; }}
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
                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                        setup: (editor: any) => {
                            editor.ui.registry.addButton('magicwand', {
                                icon: 'brightness', // fallback icon since magicwand isn't built in
                                tooltip: 'AI Copilot (Magic Wand)',
                                onAction: () => {
                                    const selectedText = editor.selection.getContent({ format: 'html' });
                                    if (!selectedText || selectedText.trim() === '') {
                                        editor.windowManager.alert('Please select some text to rewrite first.');
                                        return;
                                    }

                                    editor.windowManager.open({
                                        title: '🪄 AI Editor Copilot',
                                        size: 'normal',
                                        body: {
                                            type: 'panel',
                                            items: [
                                                {
                                                    type: 'htmlpanel',
                                                    html: '<p style="margin-bottom: 10px; color: #6b7280; font-size: 14px;">I will rewrite the selected text exactly as you instruct me to.</p>'
                                                },
                                                {
                                                    type: 'input',
                                                    name: 'instruction',
                                                    label: 'Instruction (e.g. "make it punchy", "translate to Spanish")'
                                                }
                                            ]
                                        },
                                        buttons: [
                                            {
                                                type: 'cancel',
                                                text: 'Cancel'
                                            },
                                            {
                                                type: 'submit',
                                                text: 'Magic Rewrite',
                                                primary: true
                                            }
                                        ],
                                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                        onSubmit: async (apiInstance: any) => {
                                            const data = apiInstance.getData();
                                            if (!data.instruction.trim()) {
                                                editor.windowManager.alert('Please provide an instruction.');
                                                return;
                                            }

                                            apiInstance.block('Thinking...');

                                            try {
                                                const slug = articleSlug || window.location.pathname.split('/')[3];
                                                
                                                // Prepare payload
                                                const payload: any = {
                                                    text: selectedText,
                                                    instruction: data.instruction
                                                };
                                                
                                                // Always pass current accurate content length directly from editor for context
                                                if (articleContext) {
                                                    payload.context = {
                                                        ...articleContext,
                                                        content: editor.getContent()
                                                    };
                                                }
                                                
                                                const response = await api.post(`/articles/${slug}/ai_edit_chunk/`, payload);
                                                
                                                const result = response.data;
                                                
                                                if (result && result.success) {
                                                    editor.selection.setContent(result.edited_text);
                                                    apiInstance.close();
                                                    
                                                    // Trigger parent update
                                                    const updatedContent = editor.getContent();
                                                    if (onEditorChange) { // backward compatibility alias
                                                        onEditorChange(updatedContent);
                                                    } else {
                                                        onContentChange(updatedContent);
                                                    }
                                                } else {
                                                    apiInstance.unblock();
                                                    editor.windowManager.alert(`Error: ${result.error || 'Failed to edit'}`);
                                                }
                                            } catch (err: any) {
                                                apiInstance.unblock();
                                                editor.windowManager.alert(`Error connecting to AI: ${err.message}`);
                                            }
                                        }
                                    });
                                }
                            });
                        },
                        toolbar: 'magicwand | undo redo | blocks | ' +
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

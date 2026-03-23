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
              
              /* AutoNews AI generated components */
              .fm-verdict { background-color: #f8fafc; border-left: 4px solid #3b82f6; padding: 16px; margin-top: 24px; border-radius: 4px; }
              .verdict-label { font-weight: 700; color: #1e293b; margin-bottom: 8px; text-transform: uppercase; font-size: 13px; letter-spacing: 0.05em; }
              
              .spec-bar { display: flex; flex-wrap: wrap; gap: 20px; background: #f1f5f9; padding: 16px; border-radius: 8px; margin: 20px 0; }
              .spec-item { display: flex; flex-direction: column; }
              .spec-label { font-size: 11px; color: #64748b; font-weight: 700; letter-spacing: 0.05em; margin-bottom: 2px; }
              .spec-value { font-size: 16px; color: #0f172a; font-weight: 600; }
              
              .compare-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin: 24px 0; }
              .compare-card { border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; background: #ffffff; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
              .compare-card.featured { border-color: #3b82f6; border-width: 2px; background: #f8fafc; }
              .compare-badge { display: inline-block; background: #3b82f6; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-bottom: 8px; }
              .compare-card-name { font-weight: 700; font-size: 16px; margin-bottom: 16px; color: #0f172a; }
              .compare-row { display: flex; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding: 8px 0; font-size: 14px; }
              .compare-row:last-child { border-bottom: none; padding-bottom: 0; }
              .compare-row .k { color: #64748b; }
              .compare-row .v { color: #0f172a; font-weight: 500; }
              
              .pros-cons { display: flex; flex-wrap: wrap; gap: 24px; margin: 24px 0; }
              .pc-block { flex: 1; min-width: 250px; padding: 20px; border-radius: 12px; }
              .pc-block.pros { background: #f0fdf4; border: 1px solid #bbf7d0; }
              .pc-block.cons { background: #fef2f2; border: 1px solid #fecaca; }
              .pc-title { font-weight: 700; font-size: 16px; margin-bottom: 12px; color: #0f172a; }
              .pc-list { margin: 0; padding-left: 20px; }
              .pc-list li { margin-bottom: 8px; color: #334155; }
            `,

                    }}
                />
            </div>
        </FormCard>
    );
}

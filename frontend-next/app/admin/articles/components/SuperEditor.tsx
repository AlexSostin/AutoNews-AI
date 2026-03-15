import { useEditor, EditorContent, Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import SlashCommand from './SlashCommand';
import { getSuggestionItems, renderItems } from './SlashCommandItems';

interface SuperEditorProps {
  content: string;
  onChange: (html: string) => void;
  articleContext?: {
    title: string;
    tags: string[];
    summary: string;
    content: string;
  };
  onEditorCreated?: (editor: Editor) => void;
}

const MenuBar = ({ editor }: { editor: Editor | null }) => {
  if (!editor) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5 mb-2 p-1.5 bg-gray-50/80 backdrop-blur-sm rounded-xl border border-gray-100/80 shadow-sm sticky top-0 z-10 transition-all">
      <div className="flex bg-white rounded-lg p-0.5 shadow-sm border border-gray-100">
        <button
          onClick={(e) => { e.preventDefault(); editor.chain().focus().toggleBold().run(); }}
          disabled={!editor.can().chain().focus().toggleBold().run()}
          className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
            editor.isActive('bold') ? 'bg-indigo-100 text-indigo-700' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          Bold
        </button>
        <button
          onClick={(e) => { e.preventDefault(); editor.chain().focus().toggleItalic().run(); }}
          disabled={!editor.can().chain().focus().toggleItalic().run()}
          className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
            editor.isActive('italic') ? 'bg-indigo-100 text-indigo-700' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          Italic
        </button>
      </div>

      <div className="w-px h-6 bg-gray-200 mx-1"></div>

      <div className="flex bg-white rounded-lg p-0.5 shadow-sm border border-gray-100">
        <button
          onClick={(e) => { e.preventDefault(); editor.chain().focus().toggleHeading({ level: 2 }).run(); }}
          className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
            editor.isActive('heading', { level: 2 }) ? 'bg-indigo-100 text-indigo-700' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          H2
        </button>
        <button
          onClick={(e) => { e.preventDefault(); editor.chain().focus().toggleHeading({ level: 3 }).run(); }}
          className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
            editor.isActive('heading', { level: 3 }) ? 'bg-indigo-100 text-indigo-700' : 'bg-white text-gray-700 hover:bg-gray-100'
          }`}
        >
          H3
        </button>
      </div>

      <div className="flex-1"></div>
      <button
        onClick={(e) => { 
          e.preventDefault(); 
          alert('AI Copilot Chat will open here (Phase 2)!'); 
        }}
        className="px-4 py-1.5 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-md text-sm font-medium hover:from-indigo-600 hover:to-purple-700 transition-all flex items-center gap-1.5 shadow-sm"
      >
        <span>✨</span> Ask AI Copilot ( / )
      </button>
    </div>
  );
};

export const SuperEditor = ({ content, onChange, articleContext, onEditorCreated }: SuperEditorProps) => {
  console.debug('Super Editor Initialized for:', articleContext?.title);
  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit,
      SlashCommand.configure({
        suggestion: {
          items: getSuggestionItems,
          render: renderItems,
        },
      }),
    ],
    content: content,
    onCreate: ({ editor }) => {
      onEditorCreated?.(editor as Editor);
    },
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    },
    editorProps: {
      attributes: {
        class: 'prose prose-lg max-w-none focus:outline-none min-h-[600px] p-6 md:p-10 bg-white rounded-2xl',
      },
    },
  });

  return (
    <div className="flex flex-col rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] bg-white overflow-hidden border border-gray-100 transition-all hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)]">
      <div className="bg-gradient-to-r from-gray-50 to-white border-b border-gray-100 px-6 py-4 flex items-center justify-between">
         <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
           <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.6)] animate-pulse"></span>
           Super Editor v2
         </h3>
         <div className="text-xs text-gray-400 font-medium">Auto-saving enabled</div>
      </div>
      <div className="p-4 bg-[#f8fafc]">
        <MenuBar editor={editor} />
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100/50 relative group">
          <EditorContent editor={editor} />
        </div>
      </div>
    </div>
  );
};

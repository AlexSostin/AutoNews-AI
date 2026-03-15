import { useState, useRef, useEffect } from 'react';
import { Bot, Send, User, Check } from 'lucide-react';
import api from '@/lib/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  isApplying?: boolean; // If the assistant suggested a change and we are inserting it
  suggestedContent?: string; // The actual content to insert
}

interface AICopilotSidebarProps {
  articleId: string;
  articleContext: {
    title: string;
    tags: string[];
    summary: string;
    content: string;
  };
  onApplyChange?: (newContent: string) => void;
}

export const AICopilotSidebar = ({ articleId, articleContext, onApplyChange }: AICopilotSidebarProps) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Hi! I am your AI Copilot. I can see your article context. How can I help you improve it today?',
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const handleOpenCopilot = () => {
      inputRef.current?.focus();
    };
    window.addEventListener('open-ai-copilot', handleOpenCopilot);
    return () => window.removeEventListener('open-ai-copilot', handleOpenCopilot);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { id: Date.now().toString(), role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Filter out 'welcome' to save tokens, format for backend
      const chatPayload = [...messages, userMessage]
        .filter(m => m.id !== 'welcome')
        .map(m => ({ role: m.role, content: m.content }));

      const response = await api.post(`/articles/${articleId}/ai_copilot_chat/`, {
        messages: chatPayload,
        context: articleContext
      });

      if (response.data.success) {
        let rawContent = response.data.response || "I processed your request, but returned no text.";
        let extractedContent = "";

        // Parse ```suggested-edit block if it exists
        const match = rawContent.match(/```suggested-edit\n([\s\S]*?)```/);
        if (match) {
          extractedContent = match[1].trim();
          // Remove the block from the conversational text
          rawContent = rawContent.replace(/```suggested-edit\n[\s\S]*?```/, '').trim();
          if (!rawContent) {
            rawContent = "Here is the suggested text:";
          }
        }

        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: rawContent,
          isApplying: !!extractedContent,
          suggestedContent: extractedContent
        }]);
      } else {
        throw new Error(response.data.error || 'Failed to get AI response');
      }
    } catch (error: unknown) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `❌ Error: ${error instanceof Error ? error.message : 'Something went wrong.'}`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white border-l border-gray-200 shadow-sm w-[400px] flex-shrink-0">
      <div className="p-4 border-b border-gray-100 bg-gray-50 flex items-center justify-between">
        <div className="flex items-center gap-2 text-indigo-600 font-semibold">
          <Bot className="w-5 h-5" />
          <span>AI Copilot</span>
        </div>
        <div className="text-xs text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full font-medium border border-emerald-200">
          Context Linked
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50/30">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-8 h-8 flex-shrink-0 rounded-full flex items-center justify-center ${
              msg.role === 'user' ? 'bg-gray-800 text-white' : 'bg-indigo-100 text-indigo-600'
            }`}>
              {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>
            
            <div className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`px-4 py-2.5 rounded-2xl max-w-[280px] text-sm leading-relaxed shadow-sm whitespace-pre-wrap ${
                msg.role === 'user' 
                  ? 'bg-gray-800 text-white rounded-tr-sm' 
                  : 'bg-white border border-gray-200 text-gray-800 rounded-tl-sm'
              }`}>
                {msg.content}
              </div>
              
              {/* If AI suggested text, show it in a block and show action buttons */}
              {msg.role === 'assistant' && msg.isApplying && msg.suggestedContent && onApplyChange && (
                <div className="mt-2 flex flex-col gap-2 max-w-[280px]">
                  <div className="p-3 bg-indigo-50 border border-indigo-100 rounded-lg text-xs font-mono text-indigo-900 break-words max-h-40 overflow-y-auto shadow-inner-sm relative">
                    <div className="absolute top-0 right-0 px-2 py-0.5 bg-indigo-100 text-[10px] font-bold text-indigo-500 rounded-bl-md uppercase tracking-wide">Suggested Diff</div>
                    <div className="mt-3">{msg.suggestedContent.substring(0, 200)}{msg.suggestedContent.length > 200 ? '...' : ''}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button 
                      onClick={() => {
                        onApplyChange(msg.suggestedContent!);
                        setMessages(prev => prev.map(m => m.id === msg.id ? { ...m, isApplying: false } : m));
                      }}
                      className="flex-1 flex justify-center items-center gap-1.5 px-3 py-2 bg-emerald-500 text-white rounded-lg text-xs font-medium hover:bg-emerald-600 transition-colors shadow-sm"
                    >
                      <Check className="w-3.5 h-3.5" />
                      Accept
                    </button>
                    <button 
                      onClick={() => {
                        setMessages(prev => prev.map(m => m.id === msg.id ? { ...m, isApplying: false } : m));
                      }}
                      className="flex-1 flex justify-center items-center gap-1.5 px-3 py-2 bg-rose-50 text-rose-600 border border-rose-200 rounded-lg text-xs font-medium hover:bg-rose-100 transition-colors"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 flex-shrink-0 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center">
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 flex gap-1.5 shadow-sm">
              <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
              <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-white border-t border-gray-100">
        <form onSubmit={handleSubmit} className="relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask AI to write, rewrite, or analyze..."
            className="w-full pl-4 pr-12 py-3 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all outline-none"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="absolute right-2 top-2 bottom-2 aspect-square flex items-center justify-center bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
        <div className="mt-2 text-center">
          <span className="text-[10px] text-gray-400 font-medium tracking-wide uppercase">Powered by Gemini 2.5 Pro</span>
        </div>
      </div>
    </div>
  );
};

interface SiteThemePickerProps {
    currentTheme: string;
    onUpdateTheme: (theme: string) => void;
}

export function SiteThemePicker({ currentTheme, onUpdateTheme }: SiteThemePickerProps) {
    const THEMES = [
        { value: 'default', label: 'Default', desc: 'Indigo / Purple', colors: ['#4f46e5', '#6366f1', '#818cf8'] },
        { value: 'midnight-green', label: 'Midnight Green', desc: 'Emerald / Teal', colors: ['#059669', '#10b981', '#34d399'] },
        { value: 'deep-ocean', label: 'Deep Ocean', desc: 'Blue / Navy', colors: ['#2563eb', '#3b82f6', '#60a5fa'] },
    ];

    return (
        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-5 mb-6">
            <div className="flex items-center justify-between mb-4">
                <div>
                    <h3 className="text-base font-black text-gray-900">🎨 Site Theme</h3>
                    <p className="text-xs text-gray-500 mt-1">Changes the brand color across the entire site for all visitors</p>
                </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {THEMES.map((theme) => (
                    <button
                        key={theme.value}
                        onClick={() => onUpdateTheme(theme.value)}
                        className={`relative p-4 rounded-xl border-2 transition-all text-left ${currentTheme === theme.value
                            ? 'border-gray-900 shadow-lg scale-[1.02]'
                            : 'border-gray-200 hover:border-gray-400 hover:shadow-md'
                            }`}
                    >
                        <div className="flex gap-1.5 mb-3">
                            {theme.colors.map((c, i) => (
                                <div key={i} className="w-8 h-8 rounded-lg shadow-sm" style={{ backgroundColor: c }} />
                            ))}
                        </div>
                        <p className="text-sm font-black text-gray-900">{theme.label}</p>
                        <p className="text-xs text-gray-500">{theme.desc}</p>
                        {currentTheme === theme.value && (
                            <div className="absolute top-2 right-2 w-5 h-5 bg-gray-900 rounded-full flex items-center justify-center">
                                <span className="text-white text-xs">✓</span>
                            </div>
                        )}
                    </button>
                ))}
            </div>
        </div>
    );
}

import { AutomationSettings, AutomationStats } from '../types';
import { ModuleCard, SettingRow, ToggleSwitch } from './ui';
import { timeAgo } from '../utils';

interface Props {
    settings: AutomationSettings;
    stats?: AutomationStats | null;
    saving: boolean;
    triggering: string | null;
    updateSetting: (key: string, value: unknown) => void;
    triggerTask: (taskType: string) => void;
}

export function TelegramPublishingCard({
    settings,
    stats,
    saving,
    triggering,
    updateSetting,
    triggerTask,
}: Props) {
    return (
        <ModuleCard
            title="📱 Telegram Publishing"
            enabled={settings.telegram_enabled}
            onToggle={(v) => updateSetting('telegram_enabled', v)}
            lastRun={settings.telegram_last_run}
            lastStatus={settings.telegram_last_status}
            saving={saving}
        >
            {/* Channel & stats */}
            <div className="grid grid-cols-2 gap-2 mb-3">
                <div className="bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                    <p className="text-xs text-gray-500 font-medium">Channel</p>
                    <p className="text-sm font-bold text-gray-700 truncate">{settings.telegram_channel_id || '@freshmotors_news'}</p>
                </div>
                <div className="bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                    <p className="text-xs text-gray-500 font-medium">Today</p>
                    <p className="text-lg font-black text-gray-700">{settings.telegram_today_count || 0}</p>
                </div>
            </div>

            {/* Settings */}
            <SettingRow label="Attach image">
                <ToggleSwitch
                    checked={settings.telegram_post_with_image}
                    onChange={(v) => updateSetting('telegram_post_with_image', v)}
                />
            </SettingRow>

            {/* Action buttons */}
            <div className="flex gap-2 mt-3 pt-3 border-t border-gray-100">
                <button
                    onClick={() => triggerTask('telegram-test')}
                    disabled={triggering === 'telegram-test' || undefined}
                    className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${triggering === 'telegram-test'
                            ? 'bg-gray-100 text-gray-400 cursor-wait'
                            : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200'
                        }`}
                >
                    {triggering === 'telegram-test' ? '⏳ Sending...' : '🧪 Send Test'}
                </button>
                <button
                    onClick={() => triggerTask('telegram-send')}
                    disabled={triggering === 'telegram-send' || undefined}
                    className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${triggering === 'telegram-send'
                            ? 'bg-gray-100 text-gray-400 cursor-wait'
                            : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200'
                        }`}
                >
                    {triggering === 'telegram-send' ? '⏳ Posting...' : '📤 Send Latest'}
                </button>
            </div>

            {/* Recent posts */}
            {stats?.recent_social_posts && stats.recent_social_posts.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                    <p className="text-xs font-bold text-gray-700 mb-2">Recent posts</p>
                    <div className="space-y-1.5 max-h-[140px] overflow-y-auto pr-1">
                        {stats.recent_social_posts.filter(p => p.platform === 'telegram').slice(0, 5).map((post) => (
                            <div key={post.id} className="flex items-center gap-2 text-xs bg-gray-50 rounded-lg px-2.5 py-1.5 border border-gray-100">
                                <span className={
                                    post.status === 'sent' ? 'text-emerald-600' :
                                        post.status === 'failed' ? 'text-red-600' :
                                            post.status === 'pending' ? 'text-amber-600' :
                                                'text-gray-400'
                                }>
                                    {post.status === 'sent' ? '✅' : post.status === 'failed' ? '❌' : post.status === 'pending' ? '⏳' : '⏩'}
                                </span>
                                <span className="truncate flex-1 text-gray-700 font-medium">{post.article_title}</span>
                                <span className="text-gray-400 whitespace-nowrap">{timeAgo(post.posted_at || post.created_at)}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </ModuleCard>
    );
}

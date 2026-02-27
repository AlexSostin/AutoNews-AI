import { AutomationStats } from '../types';
import { StatCard } from './ui';

interface StatsOverviewProps {
    stats: AutomationStats | null;
}

export function StatsOverview({ stats }: StatsOverviewProps) {
    if (!stats) return null;

    return (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
            <StatCard label="Pending Total" value={stats.pending_total} icon="📋" />
            <StatCard label="High Quality" value={stats.pending_high_quality} icon="⭐" color="text-emerald-600" />
            <StatCard label="Published Today" value={stats.published_today} icon="📰" color="text-blue-600" />
            <StatCard label="Auto-Published" value={stats.auto_published_today} icon="🤖" color="text-purple-600" />
            <StatCard label="RSS Today" value={stats.rss_articles_today} icon="📡" color="text-orange-600" />
            <StatCard label="YouTube Today" value={stats.youtube_articles_today} icon="🎬" color="text-red-600" />
        </div>
    );
}

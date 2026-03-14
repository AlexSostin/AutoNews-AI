import { AutomationStats } from '../types';
import { ActionCard } from './ui';
import { timeAgo } from '../utils';

interface Props {
    stats?: AutomationStats | null;
    triggering: string | null;
    triggerTask: (taskType: string) => void;
}

export function MlRecommenderCard({
    stats,
    triggering,
    triggerTask,
}: Props) {
    const ml = stats?.ml_model;

    return (
        <ActionCard
            title="🧠 ML Content Recommender"
            onTrigger={() => triggerTask('ml-retrain')}
            triggering={triggering === 'ml-retrain'}
            actionButtonText="🔄 Retrain Now"
            actionButtonLoadingText="⏳ Training..."
        >
            <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-bold text-gray-700">Model Status</span>
                <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${ml?.trained
                    ? 'bg-emerald-100 text-emerald-700 border border-emerald-200'
                    : 'bg-gray-100 text-gray-500 border border-gray-200'
                    }`}>
                    {ml?.trained ? '✅ Trained' : '⏳ Not trained'}
                </span>
            </div>

            {ml?.trained ? (
                <div className="space-y-2 flex-1 mt-1">
                    <div className="grid grid-cols-2 gap-2">
                        <div className="bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                            <p className="text-xs text-gray-500 font-medium">Articles</p>
                            <p className="text-lg font-black text-indigo-700">{ml.article_count || 0}</p>
                        </div>
                        <div className="bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                            <p className="text-xs text-gray-500 font-medium">Features (TF-IDF)</p>
                            <p className="text-lg font-black text-indigo-700">{(ml.vocabulary_size || 0).toLocaleString()}</p>
                        </div>
                        <div className="bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                            <p className="text-xs text-gray-500 font-medium">Tags</p>
                            <p className="text-lg font-black text-indigo-700">{ml.unique_tags || 0}</p>
                        </div>
                        <div className="bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                            <p className="text-xs text-gray-500 font-medium">Last trained</p>
                            <p className="text-sm font-bold text-indigo-700">{timeAgo(ml.built_at)}</p>
                        </div>
                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                        Powers similar articles, tag predictions, and content recommendations.
                    </p>
                </div>
            ) : (
                <p className="text-sm text-gray-600 flex-1 mt-1">
                    ML model has not been trained yet. Click &quot;Retrain Now&quot; or run <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">python manage.py train_content_model</code>.
                </p>
            )}
        </ActionCard>
    );
}

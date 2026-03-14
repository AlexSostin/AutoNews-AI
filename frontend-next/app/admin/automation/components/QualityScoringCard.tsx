import { AutomationSettings } from '../types';
import { ActionCard } from './ui';

interface Props {
    settings: AutomationSettings;
    triggering: string | null;
    triggerTask: (taskType: string) => void;
}

export function QualityScoringCard({
    settings,
    triggering,
    triggerTask,
}: Props) {
    return (
        <ActionCard
            title="📊 Quality Scoring"
            onTrigger={() => triggerTask('score')}
            triggering={triggering === 'score'}
            actionButtonText="🔄 Score Unscored"
            actionButtonLoadingText="⏳ Scoring..."
        >
            <p className="text-sm text-gray-600 leading-relaxed flex-1">
                Evaluates pending articles on: content length, title quality, structure,
                images, specs, tags, and red flags. Score 1-10. Articles ≥ <strong className="text-gray-800">{settings.auto_publish_min_quality}</strong> are
                eligible for auto-publishing.
            </p>
        </ActionCard>
    );
}

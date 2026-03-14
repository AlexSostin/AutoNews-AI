import { AutomationSettings, AutomationStats } from '../types';
import { EmbeddingsCard } from './EmbeddingsCard';
import { RssScanningCard } from './RssScanningCard';
import { YoutubeScanningCard } from './YoutubeScanningCard';
import { AutoPublishCard } from './AutoPublishCard';
import { AutoImageCard } from './AutoImageCard';
import { GoogleIndexingCard } from './GoogleIndexingCard';
import { VehicleSpecsCard } from './VehicleSpecsCard';
import { ComparisonsCard } from './ComparisonsCard';
import { TelegramPublishingCard } from './TelegramPublishingCard';
import { QualityScoringCard } from './QualityScoringCard';
import { MlRecommenderCard } from './MlRecommenderCard';
import { BulkEnrichmentCard } from './BulkEnrichmentCard';
import { AbTestLifecycleCard } from './AbTestLifecycleCard';

interface TaskModulesProps {
    settings: AutomationSettings;
    stats: AutomationStats | null;
    eligibleStats: AutomationStats['eligible'] | undefined;
    saving: boolean;
    triggering: string | null;
    updateSetting: (key: string, value: unknown) => void;
    triggerTask: (taskType: string) => void;
}

export function TaskModules({
    settings,
    stats,
    eligibleStats,
    saving,
    triggering,
    updateSetting,
    triggerTask
}: TaskModulesProps) {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <RssScanningCard 
                settings={settings} saving={saving} triggering={triggering} 
                updateSetting={updateSetting} triggerTask={triggerTask} 
            />
            
            <YoutubeScanningCard 
                settings={settings} saving={saving} triggering={triggering} 
                updateSetting={updateSetting} triggerTask={triggerTask} 
            />
            
            <AutoPublishCard 
                settings={settings} eligibleStats={eligibleStats} saving={saving} 
                triggering={triggering} updateSetting={updateSetting} triggerTask={triggerTask} 
            />
            
            <AutoImageCard 
                settings={settings} saving={saving} updateSetting={updateSetting} 
            />
            
            <GoogleIndexingCard 
                settings={settings} saving={saving} updateSetting={updateSetting} 
            />
            
            <VehicleSpecsCard 
                settings={settings} saving={saving} triggering={triggering} 
                updateSetting={updateSetting} triggerTask={triggerTask} 
            />
            
            <ComparisonsCard 
                settings={settings} saving={saving} updateSetting={updateSetting} 
            />
            
            <TelegramPublishingCard 
                settings={settings} stats={stats} saving={saving} triggering={triggering} 
                updateSetting={updateSetting} triggerTask={triggerTask} 
            />
            
            <QualityScoringCard 
                settings={settings} saving={saving} triggering={triggering} 
                triggerTask={triggerTask} updateSetting={updateSetting} 
            />
            
            <MlRecommenderCard 
                stats={stats} triggering={triggering} triggerTask={triggerTask} 
            />
            
            <BulkEnrichmentCard 
                stats={stats} 
            />
            
            <AbTestLifecycleCard 
                triggering={triggering} triggerTask={triggerTask} 
            />
            
            <EmbeddingsCard 
                triggering={triggering} triggerTask={triggerTask} 
            />
        </div>
    );
}

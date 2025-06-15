import { useState } from "react";
import InteractionTypesChart from "@/charts/InteractionTypesChart";
import ViewDistributionChart from "@/charts/ViewDistributionChart";
import SessionDurationChart from "@/charts/SessionDurationChart";
import LanguageChart from "@/charts/LanguageChart";
import { useLanguage } from "@/hooks/useLanguage";

type ViewMode = 'type' | 'page_view' | 'duration' | 'language';

const InteractionAnalytics = () => {
    const [view, setView] = useState<ViewMode>('type');
    const { t } = useLanguage();

    const renderView = () => {
        switch (view) {
            case 'page_view':
                return <ViewDistributionChart />;
            case 'duration':
                return <SessionDurationChart />;
            case 'language':
                return <LanguageChart />;
            case 'type':
            default:
                return <InteractionTypesChart />;
        }
    }

    return (
        <div className="analytics-wrapper">
            <div className="view-switcher">
                <button onClick={() => setView('type')} className={view === 'type' ? 'active' : ''}>
                    {t('buttons.interactionType')}
                </button>
                <button onClick={() => setView('page_view')} className={view === 'page_view' ? 'active' : ''}>
                    {t('buttons.pageViews')}
                </button>
                <button onClick={() => setView('duration')} className={view === 'duration' ? 'active' : ''}>
                    {t('buttons.sessionDuration')}
                </button>
                <button onClick={() => setView('language')} className={view === 'language' ? 'active' : ''}>
                    {t('buttons.language')}
                </button>
            </div>
            <div className="analytics-content">
                {renderView()}
            </div>
        </div>
    );
}

export default InteractionAnalytics;
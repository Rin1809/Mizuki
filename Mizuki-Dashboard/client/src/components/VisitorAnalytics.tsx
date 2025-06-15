import { useState } from "react";
import TopVisitorsTable from "./TopVisitorsTable";
import VisitorTrendChart from "@/charts/VisitorTrendChart";
import TopIPDistributionChart from "@/charts/TopIPDistributionChart";
import { useLanguage } from "@/hooks/useLanguage";

type ViewMode = 'pie' | 'trend' | 'table';

const VisitorAnalytics = () => {
    const [view, setView] = useState<ViewMode>('pie');
    const { t } = useLanguage();

    const renderView = () => {
        switch (view) {
            case 'trend':
                return <VisitorTrendChart />;
            case 'table':
                return <TopVisitorsTable />;
            case 'pie':
            default:
                return <TopIPDistributionChart />;
        }
    }

    return (
        <div className="analytics-wrapper">
            <div className="view-switcher">
                <button onClick={() => setView('pie')} className={view === 'pie' ? 'active' : ''}>
                    {t('buttons.ipDistribution')}
                </button>
                <button onClick={() => setView('trend')} className={view === 'trend' ? 'active' : ''}>
                    {t('buttons.trend')}
                </button>
                <button onClick={() => setView('table')} className={view === 'table' ? 'active' : ''}>
                    {t('buttons.ranking')}
                </button>
            </div>
            <div className="analytics-content">
                {renderView()}
            </div>
        </div>
    );
}

export default VisitorAnalytics;
import { useState } from "react";
import CountryDistributionChart from "@/charts/CountryDistributionChart";
import VisitorDistributionPieChart from "@/charts/VisitorDistributionPieChart";
import IspDistributionChart from "@/charts/IspDistributionChart";
import TopCitiesChart from "@/charts/TopCitiesChart";
import { useLanguage } from "@/hooks/useLanguage";

type ViewMode = 'loyalty' | 'country' | 'city' | 'isp';

const DistributionAnalytics = () => {
    const [view, setView] = useState<ViewMode>('loyalty');
    const { t } = useLanguage();

    const renderView = () => {
        switch (view) {
            case 'country':
                return <CountryDistributionChart />;
            case 'city':
                return <TopCitiesChart />;
            case 'isp':
                return <IspDistributionChart />;
            case 'loyalty':
            default:
                return <VisitorDistributionPieChart />;
        }
    }

    return (
        <div className="analytics-wrapper">
            <div className="view-switcher">
                <button onClick={() => setView('loyalty')} className={view === 'loyalty' ? 'active' : ''}>
                    {t('buttons.loyalty')}
                </button>
                <button onClick={() => setView('country')} className={view === 'country' ? 'active' : ''}>
                    {t('buttons.country')}
                </button>
                 <button onClick={() => setView('city')} className={view === 'city' ? 'active' : ''}>
                    {t('buttons.city')}
                </button>
                <button onClick={() => setView('isp')} className={view === 'isp' ? 'active' : ''}>
                    {t('buttons.isp')}
                </button>
            </div>
            <div className="analytics-content">
                {renderView()}
            </div>
        </div>
    );
}

export default DistributionAnalytics;
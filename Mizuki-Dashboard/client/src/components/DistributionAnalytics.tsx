// Mizuki-Dashboard/client/src/components/DistributionAnalytics.tsx
import { useState } from "react";
import CountryDistributionChart from "@/charts/CountryDistributionChart";
import VisitorDistributionPieChart from "@/charts/VisitorDistributionPieChart";
import IspDistributionChart from "@/charts/IspDistributionChart";
import TopCitiesChart from "@/charts/TopCitiesChart";

type ViewMode = 'loyalty' | 'country' | 'city' | 'isp';

const DistributionAnalytics = () => {
    const [view, setView] = useState<ViewMode>('loyalty');

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
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div className="view-switcher">
                <button onClick={() => setView('loyalty')} className={view === 'loyalty' ? 'active' : ''}>
                    Mức Độ Quay Lại
                </button>
                <button onClick={() => setView('country')} className={view === 'country' ? 'active' : ''}>
                    Quốc Gia
                </button>
                 <button onClick={() => setView('city')} className={view === 'city' ? 'active' : ''}>
                    Thành Phố
                </button>
                <button onClick={() => setView('isp')} className={view === 'isp' ? 'active' : ''}>
                    Nhà Mạng
                </button>
            </div>
            <div className="analytics-content">
                {renderView()}
            </div>
        </div>
    );
}

export default DistributionAnalytics;
import { useState } from "react";
import TopVisitorsTable from "./TopVisitorsTable";
import VisitorTrendChart from "@/charts/VisitorTrendChart";
import TopIPDistributionChart from "@/charts/TopIPDistributionChart";

type ViewMode = 'pie' | 'trend' | 'table';

const VisitorAnalytics = () => {
    const [view, setView] = useState<ViewMode>('pie');

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
                    Phân Bố IP
                </button>
                <button onClick={() => setView('trend')} className={view === 'trend' ? 'active' : ''}>
                    Xu Hướng
                </button>
                <button onClick={() => setView('table')} className={view === 'table' ? 'active' : ''}>
                    Xếp Hạng
                </button>
            </div>
            <div className="analytics-content">
                {renderView()}
            </div>
        </div>
    );
}

export default VisitorAnalytics;
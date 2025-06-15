// Mizuki-Dashboard/client/src/components/InteractionAnalytics.tsx
import { useState } from "react";
import InteractionTypesChart from "@/charts/InteractionTypesChart";
import ViewDistributionChart from "@/charts/ViewDistributionChart";
import SessionDurationChart from "@/charts/SessionDurationChart";
import LanguageChart from "@/charts/LanguageChart";

type ViewMode = 'type' | 'page_view' | 'duration' | 'language';

const InteractionAnalytics = () => {
    const [view, setView] = useState<ViewMode>('type');

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
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div className="view-switcher">
                <button onClick={() => setView('type')} className={view === 'type' ? 'active' : ''}>
                    Loại Tương Tác
                </button>
                <button onClick={() => setView('page_view')} className={view === 'page_view' ? 'active' : ''}>
                    Lượt Xem Trang
                </button>
                <button onClick={() => setView('duration')} className={view === 'duration' ? 'active' : ''}>
                    Thời Lượng Phiên
                </button>
                <button onClick={() => setView('language')} className={view === 'language' ? 'active' : ''}>
                    Ngôn Ngữ
                </button>
            </div>
            <div className="analytics-content">
                {renderView()}
            </div>
        </div>
    );
}

export default InteractionAnalytics;
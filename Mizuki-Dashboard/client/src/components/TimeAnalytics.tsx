import { useState } from "react";
import VisitsByTimeChart from "@/charts/VisitsByTimeChart";
import CombinedVisitorTrendChart from "@/charts/CombinedVisitorTrendChart";

type ViewMode = 'overview' | 'breakdown';
type Period = 'hour' | 'day' | 'week';

const TimeAnalytics = () => {
    const [view, setView] = useState<ViewMode>('overview');
    const [period, setPeriod] = useState<Period>('hour');

    const renderView = () => {
        switch (view) {
            case 'breakdown':
                return <CombinedVisitorTrendChart />;
            case 'overview':
            default:
                return <VisitsByTimeChart period={period} />;
        }
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div className="view-switcher">
                <button onClick={() => setView('overview')} className={view === 'overview' ? 'active' : ''}>
                    Tổng Quan
                </button>
                <button onClick={() => setView('breakdown')} className={view === 'breakdown' ? 'active' : ''}>
                    Phân Tích Chi Tiết
                </button>
            </div>
            
            {view === 'overview' && (
                <div className="view-switcher" style={{ marginTop: '-10px', marginBottom: '20px' }}>
                    <button onClick={() => setPeriod('hour')} className={period === 'hour' ? 'active small' : 'small'}>
                        Theo Giờ
                    </button>
                    <button onClick={() => setPeriod('day')} className={period === 'day' ? 'active small' : 'small'}>
                        Theo Ngày
                    </button>
                    <button onClick={() => setPeriod('week')} className={period === 'week' ? 'active small' : 'small'}>
                        Theo Tuần
                    </button>
                </div>
            )}

            <div className="analytics-content">
                {renderView()}
            </div>
        </div>
    );
}

export default TimeAnalytics;
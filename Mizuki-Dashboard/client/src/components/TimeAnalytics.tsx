import { useState } from "react";
import VisitsByTimeChart from "@/charts/VisitsByTimeChart";
import CombinedVisitorTrendChart from "@/charts/CombinedVisitorTrendChart";
import VisitsByTimeOfDayPieChart from "@/charts/VisitsByTimeOfDayPieChart";
import VisitsByHourBarChart from "@/charts/VisitsByHourBarChart";

type ViewMode = 'overview' | 'breakdown' | 'distribution';
type Period = 'hour' | 'day' | 'week';
type DistributionView = 'bySession' | 'byHour';

const TimeAnalytics = () => {
    const [view, setView] = useState<ViewMode>('overview');
    const [period, setPeriod] = useState<Period>('hour');
    const [distributionView, setDistributionView] = useState<DistributionView>('bySession');

    const renderChart = () => {
        switch (view) {
            case 'breakdown':
                return <CombinedVisitorTrendChart />;
            case 'distribution':
                return distributionView === 'bySession' ? <VisitsByTimeOfDayPieChart /> : <VisitsByHourBarChart />;
            case 'overview':
            default:
                return <VisitsByTimeChart period={period} />;
        }
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {/* Bo chuyen doi view chinh */}
            <div className="view-switcher">
                <button onClick={() => setView('overview')} className={view === 'overview' ? 'active' : ''}>
                    Tổng Quan
                </button>
                <button onClick={() => setView('breakdown')} className={view === 'breakdown' ? 'active' : ''}>
                    Phân Tích
                </button>
                <button onClick={() => setView('distribution')} className={view === 'distribution' ? 'active' : ''}>
                    Phân Bố
                </button>
            </div>
            
            {/* Bo chuyen doi phu cho Tong Quan */}
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

            {/* Bo chuyen doi phu cho Phan Bo */}
            {view === 'distribution' && (
                <div className="view-switcher" style={{ marginTop: '-10px', marginBottom: '20px' }}>
                    <button onClick={() => setDistributionView('bySession')} className={distributionView === 'bySession' ? 'active small' : 'small'}>
                        Theo Buổi
                    </button>
                    <button onClick={() => setDistributionView('byHour')} className={distributionView === 'byHour' ? 'active small' : 'small'}>
                        Theo Giờ
                    </button>
                </div>
            )}

            <div className="analytics-content">
                {renderChart()}
            </div>
        </div>
    );
}

export default TimeAnalytics;
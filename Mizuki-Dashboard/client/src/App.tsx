// Mizuki-Dashboard/client/src/App.tsx
import { useState, useEffect } from 'react';
import './App.css';
import StatCard from '@/components/StatCard';
import VisitorAnalytics from '@/components/VisitorAnalytics';
import TimeAnalytics from '@/components/TimeAnalytics';
import InteractionAnalytics from './components/InteractionAnalytics';
import DistributionAnalytics from './components/DistributionAnalytics';
import PlatformAnalytics from './components/PlatformAnalytics';
import ActivityByTimeChart from './charts/ActivityByTimeChart';
import DetailedInteractionAnalytics from './components/DetailedInteractionAnalytics';
import BotAnalysisChart from './charts/BotAnalysisChart';


interface OverviewStats {
  totalVisits: number;
  uniqueVisitors: number;
  totalInteractions: number;
  totalSessions: number;
  avgSessionDuration: number;
}

function App() {
  const [overview, setOverview] = useState<OverviewStats | null>(null);

  useEffect(() => {
    fetch('/api/stats/overview')
      .then(res => res.json())
      .then(data => setOverview(data))
      .catch(err => console.error("Loi lay overview:", err));
  }, []);

  return (
    <div className="dashboard-container">
      <header>
        <h1>Mizuki Analytics Dashboard ᓚᘏᗢ</h1>
      </header>
      <main>
        <section className="stats-overview">
          <StatCard title="Tổng Lượt Truy Cập" value={overview?.totalVisits} />
          <StatCard title="Khách Truy Cập" value={overview?.uniqueVisitors} />
          <StatCard title="Tổng Tương Tác" value={overview?.totalInteractions} />
          <StatCard title="Tổng Số Phiên" value={overview?.totalSessions} />
          <StatCard title="TB Thời Lượng Phiên" value={overview ? `${overview.avgSessionDuration}s` : '...'} />
        </section>
        
        <section className="charts-grid">
          <div className="chart-wrapper">
            <h2>Phân Tích Khách Truy Cập</h2>
            <VisitorAnalytics />
          </div>

          <div className="chart-wrapper">
            <h2>Phân Tích Theo Thời Gian</h2>
            <TimeAnalytics />
          </div>

          <div className="chart-wrapper">
            <h2>Phân Tích Tương Tác</h2>
            <InteractionAnalytics />
          </div>

          <div className="chart-wrapper">
            <h2>Phân Bố Dữ Liệu</h2>
            <DistributionAnalytics />
          </div>
          
          <div className="chart-wrapper">
            <h2>Phân Tích Nền Tảng</h2>
            <PlatformAnalytics />
          </div>
          
          <div className="chart-wrapper">
            <h2>Thời Gian Hoạt Động</h2>
            <ActivityByTimeChart />
          </div>

           <div className="chart-wrapper">
            <h2>Tương Tác Chi Tiết</h2>
            <DetailedInteractionAnalytics />
          </div>

          <div className="chart-wrapper">
            <h2>Phân Tích Bot / Crawler</h2>
            <BotAnalysisChart />
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
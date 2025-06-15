import { useState, useEffect } from 'react';
import './App.css';
// dung alias @ de chi vao thu muc src
import StatCard from '@/components/StatCard';
import VisitsByTimeChart from '@/charts/VisitsByTimeChart';
import CountryDistributionChart from '@/charts/CountryDistributionChart';

interface OverviewStats {
  totalVisits: number;
  uniqueVisitors: number;
  totalInteractions: number;
  totalSessions: number;
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
        </section>
        <section className="charts-grid">
          <div className="chart-wrapper">
            <h2>Lượt truy cập theo thời gian</h2>
            <VisitsByTimeChart />
          </div>
          <div className="chart-wrapper">
            <h2>Phân bố quốc gia (Top 10)</h2>
            <CountryDistributionChart />
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
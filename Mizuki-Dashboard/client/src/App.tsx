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
import LiveStat from './components/LiveStat';
import BounceRateTrendChart from './charts/BounceRateTrendChart';
import { useLanguage } from './hooks/useLanguage';
import { Locale } from './lib/translations';

interface OverviewStats {
  totalVisits: number;
  uniqueVisitors: number;
  totalInteractions: number;
  totalSessions: number;
  avgSessionDuration: number;
  bounceRate: number;
}

const EyeIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639l4.418-5.523A2 2 0 018.135 5h7.73a2 2 0 011.681 1.16l4.418 5.523a1.012 1.012 0 010 .639l-4.418 5.523A2 2 0 0115.865 19h-7.73a2 2 0 01-1.681-1.16z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);
const UsersIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
  </svg>
);
const InteractionIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15.042 21.672L13.684 16.6m0 0l-2.51 2.225.569-9.47 5.227 7.917-3.286-.672zm-7.518-.267A8.25 8.25 0 1120.25 10.5M8.288 14.212A5.25 5.25 0 1117.25 10.5" />
  </svg>
);
const ClockIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);
const BounceIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3" />
  </svg>
);

function App() {
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const { t, locale, setLocale } = useLanguage();

  useEffect(() => {
    fetch('/api/stats?endpoint=overview')
      .then(res => res.json())
      .then(data => setOverview(data))
      .catch(err => console.error("Loi lay overview:", err));
  }, []);

  return (
    <div className="dashboard-container">
      <header>
        <div className="header-content">
          <div className="header-left">
            <div className="header-title">
              <img src="/icon.ico" alt="Mizuki Icon" className="header-icon" />
              <h1>{t('appTitle')}</h1>
            </div>
          </div>
          <div className="header-right">
            <LiveStat />
            <div className="language-selector">
              <select value={locale} onChange={(e) => setLocale(e.target.value as Locale)}>
                <option value="vi">Tiếng Việt</option>
                <option value="en">English</option>
                <option value="ja">日本語</option>
              </select>
            </div>
          </div>
        </div>
      </header>
      <main>
        <section className="overview-grid">
          <StatCard title={t('overview.totalVisits')} value={overview?.totalVisits} icon={<EyeIcon />} />
          <StatCard title={t('overview.uniqueVisitors')} value={overview?.uniqueVisitors} icon={<UsersIcon />} />
          <StatCard title={t('overview.totalInteractions')} value={overview?.totalInteractions} icon={<InteractionIcon />} />
          <StatCard title={t('overview.avgSessionDuration')} value={overview?.avgSessionDuration} unit={t('overview.unitSeconds')} icon={<ClockIcon />} />
          <StatCard title={t('overview.bounceRate')} value={overview?.bounceRate} unit="%" icon={<BounceIcon />} />
        </section>
        
        <div className="main-content">
          <div className="main-column">
            <div className="chart-wrapper">
              <h2>{t('charts.timeAnalytics')}</h2>
              <TimeAnalytics />
            </div>
            <div className="chart-wrapper">
              <h2>{t('charts.visitorAnalytics')}</h2>
              <VisitorAnalytics />
            </div>
             <div className="chart-wrapper">
              <h2>{t('charts.activityHeatmap')}</h2>
              <ActivityByTimeChart />
            </div>
            <div className="chart-wrapper">
              <h2>{t('charts.bounceRateTrend')}</h2>
              <BounceRateTrendChart />
            </div>
          </div>
          <div className="sidebar-column">
            <div className="chart-wrapper">
              <h2>{t('charts.interactionAnalytics')}</h2>
              <InteractionAnalytics />
            </div>
            <div className="chart-wrapper">
              <h2>{t('charts.platformAnalytics')}</h2>
              <PlatformAnalytics />
            </div>
            <div className="chart-wrapper">
              <h2>{t('charts.geoNetworkAnalytics')}</h2>
              <DistributionAnalytics />
            </div>
            <div className="chart-wrapper">
              <h2>{t('charts.detailedInteractions')}</h2>
              <DetailedInteractionAnalytics />
            </div>
            <div className="chart-wrapper">
              <h2>{t('charts.botAnalysis')}</h2>
              <BotAnalysisChart />
            </div>
          </div>
        </div>
      </main>
      <footer>
        <p>{t('footer')}</p>
      </footer>
    </div>
  );
}

export default App;
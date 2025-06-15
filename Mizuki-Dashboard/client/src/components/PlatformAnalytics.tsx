import { useState, useEffect } from "react";
import { Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend, ChartOptions } from 'chart.js';
import { useLanguage } from "@/hooks/useLanguage";

ChartJS.register(ArcElement, Tooltip, Legend);

const chartColors = ['#bb9af7', '#7dcfff', '#73daca', '#b9f27c', '#ff9e64', '#f7768e', '#e0af68'];

const createChartData = (labels: string[], data: number[], label: string) => ({
    labels,
    datasets: [{
        label,
        data,
        backgroundColor: chartColors.slice(0, labels.length),
        borderColor: '#1a1b26',
        borderWidth: 2,
    }]
});

const chartOptions: ChartOptions<'doughnut'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom', labels: { color: '#c0caf5', font: { size: 12 } } },
    }
};

type ViewMode = 'browser' | 'os';

const PlatformAnalytics = () => {
    const [view, setView] = useState<ViewMode>('browser');
    const [browserData, setBrowserData] = useState<any>({ datasets: [] });
    const [osData, setOsData] = useState<any>({ datasets: [] });
    const [loading, setLoading] = useState(true);
    const { t } = useLanguage();

    useEffect(() => {
        fetch('/api/stats/platform-distribution')
            .then(res => res.json())
            .then(data => {
                if (data.byBrowser) {
                    setBrowserData(createChartData(
                        data.byBrowser.map((d: any) => d.browser),
                        data.byBrowser.map((d: any) => d.count),
                        t('chartLabels.visits')
                    ));
                }
                if (data.byOs) {
                    setOsData(createChartData(
                        data.byOs.map((d: any) => d.os),
                        data.byOs.map((d: any) => d.count),
                        t('chartLabels.visits')
                    ));
                }
                setLoading(false);
            });
    }, [t]);

    if (loading) return <p>{t('loading')}</p>;

    return (
        <div className="analytics-wrapper">
            <div className="view-switcher">
                <button onClick={() => setView('browser')} className={view === 'browser' ? 'active' : ''}>
                    {t('buttons.byBrowser')}
                </button>
                <button onClick={() => setView('os')} className={view === 'os' ? 'active' : ''}>
                    {t('buttons.byOs')}
                </button>
            </div>
            <div className="analytics-content">
                {view === 'browser' ? <Doughnut data={browserData} options={chartOptions} /> : <Doughnut data={osData} options={chartOptions} />}
            </div>
        </div>
    );
}

export default PlatformAnalytics;
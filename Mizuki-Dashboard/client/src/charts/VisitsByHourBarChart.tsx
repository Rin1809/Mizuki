import { useState, useEffect } from 'react';
import { Bar } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ChartOptions } from 'chart.js';
import { useLanguage } from '@/hooks/useLanguage';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const VisitsByHourBarChart = () => {
    const [chartData, setChartData] = useState<any>({ datasets: [] });
    const [loading, setLoading] = useState(true);
    const { t } = useLanguage();

    useEffect(() => {
        fetch('/api/stats/visits-by-hour')
            .then(res => res.json())
            .then(data => {
                if (!data || !data.distribution) {
                    setLoading(false);
                    return;
                }
                
                const labels = Array.from({ length: 24 }, (_, i) => `${i}:00`);
                const counts = Array(24).fill(0);

                for (const item of data.distribution) {
                    if (item.hour >= 0 && item.hour < 24) {
                        counts[item.hour] = item.count;
                    }
                }
                
                setChartData({
                    labels,
                    datasets: [{
                        label: t('chartLabels.visits'),
                        data: counts,
                        backgroundColor: '#7dcfff90',
                        borderColor: '#7dcfff',
                        borderWidth: 1,
                        borderRadius: 4,
                    }]
                });
                setLoading(false);
            });
    }, [t]);

    const options: ChartOptions<'bar'> = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: {
                ticks: { color: '#c0caf5', autoSkip: true, maxTicksLimit: 12 },
                grid: { color: 'rgba(192, 202, 245, 0.05)' }
            },
            y: {
                beginAtZero: true,
                ticks: { color: '#c0caf5', stepSize: 1 },
                grid: { color: 'rgba(192, 202, 245, 0.1)' }
            }
        },
        plugins: {
            legend: { display: false },
        }
    };

    if (loading) return <p>{t('loading')}</p>;

    return (
        <div className="chart-container">
            <Bar data={chartData} options={options} />
        </div>
    );
};

export default VisitsByHourBarChart;
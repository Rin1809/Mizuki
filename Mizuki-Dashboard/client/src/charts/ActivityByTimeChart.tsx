// Mizuki-Dashboard/client/src/charts/ActivityByTimeChart.tsx
import { useState, useEffect } from 'react';
import { Bar } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ChartOptions } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

type ViewMode = 'hourly' | 'daily';

const dayLabels = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật'];

const ActivityByTimeChart = () => {
    const [view, setView] = useState<ViewMode>('hourly');
    const [chartData, setChartData] = useState<any>({ datasets: [] });
    const [loading, setLoading] = useState(true);
    const [apiData, setApiData] = useState<any>(null);

    useEffect(() => {
        fetch('/api/stats/activity-by-time')
            .then(res => res.json())
            .then(data => {
                setApiData(data);
                setLoading(false);
            });
    }, []);

    useEffect(() => {
        if (!apiData) return;

        const hourlyLabels = Array.from({ length: 24 }, (_, i) => `${i}:00`);
        const hourlyCounts = Array(24).fill(0);
        apiData.byHour.forEach((item: any) => {
            hourlyCounts[item.hour] = item.count;
        });

        const dailyCounts = Array(7).fill(0);
        apiData.byDayOfWeek.forEach((item: any) => {
            dailyCounts[item.day_of_week - 1] = item.count;
        });

        const dataMap = {
            hourly: { labels: hourlyLabels, counts: hourlyCounts, label: 'Lượt truy cập theo giờ' },
            daily: { labels: dayLabels, counts: dailyCounts, label: 'Lượt truy cập theo ngày' }
        };

        const currentData = dataMap[view];
        setChartData({
            labels: currentData.labels,
            datasets: [{
                label: currentData.label,
                data: currentData.counts,
                backgroundColor: '#9ece6a',
                borderColor: '#7a9c51',
                borderWidth: 1,
            }]
        });

    }, [view, apiData]);

    const options: ChartOptions<'bar'> = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: { ticks: { color: '#c0caf5' }, grid: { color: 'rgba(192, 202, 245, 0.1)' } },
            y: { ticks: { color: '#c0caf5', stepSize: 1 }, grid: { color: 'rgba(192, 202, 245, 0.1)' } }
        },
        plugins: { legend: { display: false } }
    };

    if (loading) return <p>Đang tải...</p>;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div className="view-switcher" style={{ marginTop: '-10px', marginBottom: '20px' }}>
                <button onClick={() => setView('hourly')} className={view === 'hourly' ? 'active small' : 'small'}>Theo Giờ</button>
                <button onClick={() => setView('daily')} className={view === 'daily' ? 'active small' : 'small'}>Theo Ngày</button>
            </div>
            <div className="analytics-content">
                <Bar data={chartData} options={options} />
            </div>
        </div>
    );
};

export default ActivityByTimeChart;
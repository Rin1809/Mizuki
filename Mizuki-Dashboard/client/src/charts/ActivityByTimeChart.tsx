import { useState, useEffect } from 'react';
import { Bubble } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, Tooltip, Legend, ChartOptions, BubbleController, ChartDataset } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, Tooltip, Legend, BubbleController);

const dayLabels = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'CN'];
const hourLabels = Array.from({ length: 24 }, (_, i) => `${i}h`);

const ActivityHeatmapChart = () => {
    const [chartData, setChartData] = useState<any>({ datasets: [] });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('/api/stats/activity-by-time')
            .then(res => res.json())
            .then(data => {
                if (!data.heatmapData) {
                    setLoading(false);
                    return;
                }

                const maxCount = Math.max(...data.heatmapData.map((d: any) => d.count), 0);

                const bubbleData = data.heatmapData.map((item: any) => ({
                    x: item.hour_of_day,
                    y: item.day_of_week - 1,
                    v: item.count,
                    r: Math.max(5, (item.count / (maxCount || 1)) * 20),
                }));

                const dataset: ChartDataset<'bubble'> = {
                    label: 'Lượt truy cập',
                    data: bubbleData,
                    backgroundColor: 'rgba(158, 206, 106, 0.7)',
                    borderColor: '#9ece6a',
                    borderWidth: 1,
                };
                
                setChartData({
                    labels: hourLabels,
                    datasets: [dataset]
                });
                setLoading(false);
            });
    }, []);

    const options: ChartOptions<'bubble'> = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: {
                type: 'category',
                labels: hourLabels,
                ticks: { color: '#c0caf5', autoSkip: true, maxTicksLimit: 12 },
                grid: { color: 'rgba(192, 202, 245, 0.05)' },
                title: { display: true, text: 'Giờ trong ngày', color: '#c0caf5' }
            },
            y: {
                type: 'category',
                labels: dayLabels,
                offset: true,
                ticks: { color: '#c0caf5' },
                grid: { color: 'rgba(192, 202, 245, 0.1)' },
                title: { display: true, text: 'Ngày trong tuần', color: '#c0caf5' }
            }
        },
        plugins: {
            legend: { display: false },
            tooltip: {
                callbacks: {
                    label: function(context: any) {
                        const day = dayLabels[context.raw.y];
                        const hour = `${context.raw.x}h - ${context.raw.x + 1}h`;
                        const count = context.raw.v;
                        return `${day}, ${hour}: ${count} lượt`;
                    }
                }
            }
        }
    };

    if (loading) return <p>Đang tải...</p>;

    return (
        <div className="analytics-content">
            <Bubble data={chartData} options={options} />
        </div>
    );
};

export default ActivityHeatmapChart;
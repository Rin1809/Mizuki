import { useState, useEffect } from 'react';
import { Pie } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, ChartOptions } from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

const chartColors = ['#e0af68', '#7dcfff', '#bb9af7', '#565f89'];

const VisitsByTimeOfDayPieChart = () => {
    const [chartData, setChartData] = useState<any>({ datasets: [] });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('/api/stats/visits-by-time-of-day')
            .then(res => res.json())
            .then(data => {
                if (!data || !data.distribution) {
                    setLoading(false);
                    return;
                }
                const labels = data.distribution.map((d: any) => d.time_of_day);
                const counts = data.distribution.map((d: any) => d.count);
                
                setChartData({
                    labels,
                    datasets: [{
                        label: 'Số lượt truy cập',
                        data: counts,
                        backgroundColor: chartColors.slice(0, labels.length),
                        borderColor: '#1a1b26',
                        borderWidth: 2,
                    }]
                });
                setLoading(false);
            });
    }, []);

    const options: ChartOptions<'pie'> = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: { color: '#c0caf5' }
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        let label = context.dataset.label || '';
                        if (label) { label += ': '; }
                        if (context.parsed !== null) {
                            const total = context.dataset.data.reduce((acc: number, val: number) => acc + val, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            label += `${context.parsed.toLocaleString('vi-VN')} (${percentage}%)`;
                        }
                        return label;
                    }
                }
            }
        }
    };

    if (loading) return <p>Đang tải...</p>;

    return (
        <div className="chart-container">
            <Pie data={chartData} options={options} />
        </div>
    );
};

export default VisitsByTimeOfDayPieChart;
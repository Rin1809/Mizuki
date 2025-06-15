import { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, TimeScale, ChartOptions, Filler } from 'chart.js';
import 'chartjs-adapter-date-fns';
import { vi } from 'date-fns/locale';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, TimeScale, Filler);

const BounceRateTrendChart = () => {
    const [chartData, setChartData] = useState<any>({ datasets: [] });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('/api/stats/bounce-rate-trends')
            .then(res => res.json())
            .then(apiResponse => {
                if (!apiResponse || !apiResponse.trends) {
                    setLoading(false);
                    return;
                }
                const data = apiResponse.trends;
                const labels = data.map((d: any) => new Date(d.day));
                const rates = data.map((d: any) => parseFloat(d.bounce_rate).toFixed(2));
                
                setChartData({
                    labels,
                    datasets: [{
                        label: 'Tỷ lệ thoát',
                        data: rates,
                        borderColor: '#f7768e',
                        backgroundColor: 'rgba(247, 118, 142, 0.25)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 2,
                        pointBackgroundColor: '#f7768e',
                        pointHoverRadius: 5,
                    }]
                });
                setLoading(false);
            })
            .catch(error => {
                console.error("Loi khi fetch bounce rate trends:", error);
                setLoading(false);
            });
    }, []);

    const options: ChartOptions<'line'> = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: {
                type: 'time',
                time: { unit: 'day' },
                adapters: { date: { locale: vi } },
                ticks: { color: '#c0caf5' },
                grid: { color: 'rgba(192, 202, 245, 0.1)' }
            },
            y: {
                beginAtZero: true,
                ticks: {
                    color: '#c0caf5',
                    callback: function(value) {
                        return value + '%';
                    }
                },
                grid: { color: 'rgba(192, 202, 245, 0.1)' }
            }
        },
        plugins: {
            legend: { display: false },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        let label = context.dataset.label || '';
                        if (label) {
                            label += ': ';
                        }
                        if (context.parsed.y !== null) {
                            label += context.parsed.y.toFixed(2) + '%';
                        }
                        return label;
                    }
                }
            }
        }
    };

    if (loading) return <p>Đang tải dữ liệu...</p>;

    return (
        <div className="chart-container">
            <Line data={chartData} options={options} />
        </div>
    );
};

export default BounceRateTrendChart;
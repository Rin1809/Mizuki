import { useState, useEffect } from 'react';
import { Pie } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, ChartOptions } from 'chart.js';
import { useLanguage } from '@/hooks/useLanguage';

ChartJS.register(ArcElement, Tooltip, Legend);
const chartColors = ['#7dcfff', '#b9f27c', '#ff9e64', '#f7768e'];

const VisitorDistributionPieChart = () => {
    const [chartData, setChartData] = useState<any>({ datasets: [] });
    const { t, locale } = useLanguage();

    useEffect(() => {
        fetch('/api/stats/visitor-distribution')
            .then(res => res.json())
            .then(data => {
                if (!data || !data.distribution) return;
                const labels = data.distribution.map((d: any) => t(`chartLabels.visitorDistribution.${d.category}`));
                const counts = data.distribution.map((d: any) => d.num_visitors);
                setChartData({
                    labels,
                    datasets: [{
                        label: t('chartLabels.visitors'),
                        data: counts,
                        backgroundColor: chartColors.slice(0, labels.length),
                        borderColor: '#1a1b26',
                        borderWidth: 2,
                    }]
                });
            });
    }, [t]);

    const options: ChartOptions<'pie'> = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { color: '#c0caf5' } },
        tooltip: {
            callbacks: {
                label: function(context) {
                    let label = context.dataset.label || '';
                    if (label) { label += ': '; }
                    if (context.parsed !== null) {
                        const total = context.dataset.data.reduce((acc: number, val: number) => acc + val, 0);
                        const percentage = ((context.parsed / total) * 100).toFixed(1);
                        label += `${context.parsed.toLocaleString(locale)} (${percentage}%)`;
                    }
                    return label;
                }
            }
        }
      }
    };
    return <div className="chart-container"><Pie data={chartData} options={options} /></div>;
};

export default VisitorDistributionPieChart;
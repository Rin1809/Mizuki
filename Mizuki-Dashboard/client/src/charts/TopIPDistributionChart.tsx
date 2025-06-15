import { useState, useEffect } from 'react';
import { Pie } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, ChartOptions } from 'chart.js';
import { useLanguage } from '@/hooks/useLanguage';

ChartJS.register(ArcElement, Tooltip, Legend);

const chartColors = [
    '#bb9af7', '#7dcfff', '#73daca', '#b9f27c', '#ff9e64',
    '#f7768e', '#e0af68', '#9ece6a', '#c0caf5', '#2ac3de',
    '#565f89'
];

const TopIPDistributionChart = () => {
    const [chartData, setChartData] = useState<any>({ datasets: [] });
    const { t, locale } = useLanguage();

    useEffect(() => {
        fetch('/api/stats?endpoint=top-visitors')
            .then(res => res.json())
            .then(data => {
                if (!data || !data.topVisitors || data.topVisitors.length === 0) return;

                const topN = 10;
                const topVisitors = data.topVisitors.slice(0, topN);
                const otherVisitors = data.topVisitors.slice(topN);

                const labels = topVisitors.map((d: any) => d.ip_address);
                const counts = topVisitors.map((d: any) => d.visit_count);

                if (otherVisitors.length > 0) {
                    labels.push(t('chartLabels.otherIPs'));
                    const otherCount = otherVisitors.reduce((sum: number, visitor: any) => sum + visitor.visit_count, 0);
                    counts.push(otherCount);
                }
                
                setChartData({
                    labels,
                    datasets: [{
                        label: t('tables.visitCount'),
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
        legend: {
          position: 'bottom',
          labels: { color: '#c0caf5', font: { size: 11 } }
        },
        tooltip: {
            callbacks: {
                label: function(context) {
                    let label = context.dataset.label || '';
                    if (label) {
                        label += ': ';
                    }
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

export default TopIPDistributionChart;
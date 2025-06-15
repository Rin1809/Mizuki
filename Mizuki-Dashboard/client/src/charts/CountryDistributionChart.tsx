import { useState, useEffect } from 'react';
import { Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, ChartOptions } from 'chart.js';
import { useLanguage } from '@/hooks/useLanguage';

ChartJS.register(ArcElement, Tooltip, Legend);

const chartColors = [
    '#bb9af7', '#7dcfff', '#73daca', '#b9f27c', '#ff9e64',
    '#f7768e', '#e0af68', '#9ece6a', '#c0caf5', '#2ac3de'
];

const CountryDistributionChart = () => {
    const [chartData, setChartData] = useState<any>({ datasets: [] });
    const { t } = useLanguage();

    useEffect(() => {
        fetch('/api/stats?endpoint=visits')
            .then(res => res.json())
            .then(data => {
                if (!data || !data.byCountry) return;
                const labels = data.byCountry.map((d: any) => d.country);
                const counts = data.byCountry.map((d: any) => d.count);
                setChartData({
                    labels,
                    datasets: [{
                        label: t('chartLabels.visits'),
                        data: counts,
                        backgroundColor: chartColors.slice(0, labels.length),
                        borderColor: '#1a1b26',
                        borderWidth: 2,
                    }]
                });
            });
    }, [t]);

    const options: ChartOptions<'doughnut'> = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#c0caf5' }
        }
      }
    };

    return (
        <div className="chart-container">
            <Doughnut data={chartData} options={options} />
        </div>
    );
};

export default CountryDistributionChart;
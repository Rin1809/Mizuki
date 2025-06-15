import { useState, useEffect } from 'react';
import { Bar } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ChartOptions } from 'chart.js';
import { useLanguage } from '@/hooks/useLanguage';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const TopCitiesChart = () => {
    const [chartData, setChartData] = useState<any>({ datasets: [] });
    const { t } = useLanguage();

    useEffect(() => {
        fetch('/api/stats?endpoint=city-distribution')
            .then(res => res.json())
            .then(data => {
                if (!data || !data.cityDistribution) return;
                
                const labels = data.cityDistribution.map((d: any) => `${d.city}, ${d.country}`);
                const counts = data.cityDistribution.map((d: any) => d.count);
                
                setChartData({
                    labels,
                    datasets: [{
                        label: t('chartLabels.visits'),
                        data: counts,
                        backgroundColor: '#e0af68',
                        borderColor: '#b18b53',
                        borderWidth: 1,
                    }]
                });
            });
    }, [t]);

    const options: ChartOptions<'bar'> = {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      scales: {
          x: { 
            ticks: { color: '#c0caf5', stepSize: 1 },
            grid: { color: 'rgba(192, 202, 245, 0.1)' }
          },
          y: { 
            ticks: { color: '#c0caf5' },
            grid: { color: 'rgba(192, 202, 245, 0.1)' }
          }
      },
      plugins: {
        legend: { display: false },
        title: { display: false }
      }
    };

    return (
        <div className="chart-container">
            <Bar data={chartData} options={options} />
        </div>
    );
};

export default TopCitiesChart;
import { useState, useEffect } from 'react';
import { Bar } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ChartOptions } from 'chart.js';
import { useLanguage } from '@/hooks/useLanguage';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const InteractionTypesChart = () => {
    const [chartData, setChartData] = useState<any>({ datasets: [] });
    const { t } = useLanguage();

    useEffect(() => {
        fetch('/api/stats/interactions')
            .then(res => res.json())
            .then(data => {
                if (!data || !data.eventTypeCounts) return;
                const labels = data.eventTypeCounts.map((d: any) => d.event_type);
                const counts = data.eventTypeCounts.map((d: any) => d.count);
                setChartData({
                    labels,
                    datasets: [{
                        label: t('chartLabels.interactions'),
                        data: counts,
                        backgroundColor: '#f7768e',
                        borderColor: '#bb5d6e',
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
          x: { ticks: { color: '#c0caf5', stepSize: 1 } },
          y: { ticks: { color: '#c0caf5' } }
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

export default InteractionTypesChart;
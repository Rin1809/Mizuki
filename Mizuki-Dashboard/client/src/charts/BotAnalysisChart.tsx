import { useState, useEffect } from 'react';
import { Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, ChartOptions } from 'chart.js';
import { useLanguage } from '@/hooks/useLanguage';

ChartJS.register(ArcElement, Tooltip, Legend);

const chartColors = ['#f7768e', '#ff9e64', '#e0af68', '#b9f27c', '#73daca', '#7dcfff', '#bb9af7'];

const BotAnalysisChart = () => {
    const [chartData, setChartData] = useState<any>({ datasets: [] });
    const { t } = useLanguage();

    useEffect(() => {
        fetch('/api/stats?endpoint=bot-analysis')
            .then(res => res.json())
            .then(data => {
                if (!data || !data.botDistribution) return;
                const labels = data.botDistribution.map((d: any) => d.bot_type);
                const counts = data.botDistribution.map((d: any) => d.count);
                setChartData({
                    labels,
                    datasets: [{
                        label: t('chartLabels.visits'),
                        data: counts,
                        backgroundColor: chartColors,
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
          position: 'right',
          labels: { color: '#c0caf5' }
        },
      }
    };

    return (
        <div className="chart-container">
            <Doughnut data={chartData} options={options} />
        </div>
    );
};

export default BotAnalysisChart;
import { useState, useEffect } from 'react';
import { Pie } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, ChartOptions } from 'chart.js';
import { useLanguage } from '@/hooks/useLanguage';

ChartJS.register(ArcElement, Tooltip, Legend);

const LanguageChart = () => {
    const [chartData, setChartData] = useState<any>({ datasets: [] });
    const { t } = useLanguage();

    useEffect(() => {
        fetch('/api/stats?endpoint=language-distribution')
            .then(res => res.json())
            .then(data => {
                if (!data || !data.languageDistribution) return;

                const labels = data.languageDistribution.map((d: any) => d.language.toUpperCase());
                const counts = data.languageDistribution.map((d: any) => d.count);
                
                setChartData({
                    labels,
                    datasets: [{
                        label: t('chartLabels.languageSelection'),
                        data: counts,
                        backgroundColor: ['#e0af68', '#7dcfff', '#bb9af7', '#73daca'],
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
        }
    };

    return (
        <div className="chart-container">
            <Pie data={chartData} options={options} />
        </div>
    );
};

export default LanguageChart;
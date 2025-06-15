// Mizuki-Dashboard/client/src/charts/LanguageChart.tsx
import { useState, useEffect } from 'react';
import { Pie } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, ChartOptions } from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

const LanguageChart = () => {
    const [chartData, setChartData] = useState<any>({ datasets: [] });

    useEffect(() => {
        fetch('/api/stats/language-distribution')
            .then(res => res.json())
            .then(data => {
                if (!data || !data.languageDistribution) return;

                const labels = data.languageDistribution.map((d: any) => d.language.toUpperCase());
                const counts = data.languageDistribution.map((d: any) => d.count);
                
                setChartData({
                    labels,
                    datasets: [{
                        label: 'Số lần chọn',
                        data: counts,
                        backgroundColor: ['#e0af68', '#7dcfff'],
                        borderColor: '#1a1b26',
                        borderWidth: 2,
                    }]
                });
            });
    }, []);

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
import { useState, useEffect } from 'react';
import { Bar, Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, PointElement, LineElement, Title, Tooltip, Legend, TimeScale, ChartOptions, Filler, ChartDataset } from 'chart.js';
import 'chartjs-adapter-date-fns';
import { useLanguage } from '@/hooks/useLanguage';
import { dateLocales } from '@/lib/dateLocales';

ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Title, Tooltip, Legend, TimeScale, Filler);

interface DetailedInteractionChartProps {
    type: 'about-subsections' | 'gallery-hotspots' | 'guestbook-trends';
}

const DetailedInteractionChart = ({ type }: DetailedInteractionChartProps) => {
    const [chartData, setChartData] = useState<any>({ datasets: [] });
    const { t, locale } = useLanguage();

    const chartConfig = {
      'about-subsections': { type: 'bar' as const, label: t('chartLabels.viewedSection'), color: '#b9f27c' },
      'gallery-hotspots': { type: 'bar' as const, label: t('chartLabels.viewedImage'), color: '#ff9e64' },
      'guestbook-trends': { type: 'line' as const, label: t('chartLabels.submittedEntry'), color: '#f7768e' },
    };
    
    const config = chartConfig[type];

    useEffect(() => {
        fetch(`/api/stats/detailed-interactions?type=${type}`)
            .then(res => res.json())
            .then(apiResponse => {
                if (!apiResponse || !apiResponse.data) return;

                const data = apiResponse.data;
                const labels = data.map((d: any) => d.item || new Date(d.date));
                const counts = data.map((d: any) => d.count);

                if (type === 'gallery-hotspots') {
                    labels.forEach((label: string, index: number) => {
                       labels[index] = `${t('chartLabels.image')} ${parseInt(label, 10) + 1}`;
                    });
                }

                const baseDataset = {
                    label: config.label,
                    data: counts,
                    backgroundColor: `${config.color}80`,
                    borderColor: config.color,
                    borderWidth: 2,
                    tension: 0.3,
                };
                
                let dataset: ChartDataset<typeof config.type>;

                if (config.type === 'line') {
                    dataset = { ...baseDataset, fill: true };
                } else {
                    dataset = baseDataset;
                }
                
                setChartData({ labels, datasets: [dataset] });
            });
    }, [type, t]);

    const options: ChartOptions<any> = {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: config.type === 'bar' ? 'y' : 'x',
      scales: {
          x: { 
            type: config.type === 'line' ? 'time' : 'linear',
            time: { unit: 'day' },
            adapters: { date: { locale: dateLocales[locale] } },
            ticks: { color: '#c0caf5' },
            grid: { color: 'rgba(192, 202, 245, 0.1)' }
          },
          y: { 
            beginAtZero: true,
            ticks: { color: '#c0caf5' },
            grid: { color: 'rgba(192, 202, 245, 0.1)' }
          }
      },
      plugins: {
        legend: { display: false }
      }
    };

    const ChartComponent = config.type === 'line' ? Line : Bar;

    return (
        <div className="chart-container">
            <ChartComponent data={chartData} options={options} />
        </div>
    );
};

export default DetailedInteractionChart;
// Mizuki-Dashboard/client/src/charts/DetailedInteractionChart.tsx
import { useState, useEffect } from 'react';
import { Bar, Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, PointElement, LineElement, Title, Tooltip, Legend, TimeScale, ChartOptions, Filler, ChartDataset } from 'chart.js';
import 'chartjs-adapter-date-fns';
import { vi } from 'date-fns/locale';

ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Title, Tooltip, Legend, TimeScale, Filler);

interface DetailedInteractionChartProps {
    type: 'about-subsections' | 'gallery-hotspots' | 'guestbook-trends';
}

const chartConfig = {
    'about-subsections': { type: 'bar' as const, label: 'Lượt xem mục', color: '#b9f27c' },
    'gallery-hotspots': { type: 'bar' as const, label: 'Lượt xem ảnh', color: '#ff9e64' },
    'guestbook-trends': { type: 'line' as const, label: 'Lượt gửi', color: '#f7768e' },
};

const DetailedInteractionChart = ({ type }: DetailedInteractionChartProps) => {
    const [chartData, setChartData] = useState<any>({ datasets: [] });
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
                       labels[index] = `Ảnh ${parseInt(label, 10) + 1}`;
                    });
                }

                // tao dataset mot cach an toan cho typescript
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
                    dataset = {
                        ...baseDataset,
                        fill: true,
                    };
                } else {
                    dataset = baseDataset;
                }
                
                setChartData({
                    labels,
                    datasets: [dataset],
                });
            });
    }, [type, config]);

    const options: ChartOptions<any> = {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: config.type === 'bar' ? 'y' : 'x',
      scales: {
          x: { 
            type: config.type === 'line' ? 'time' : 'linear',
            time: { unit: 'day' },
            adapters: { date: { locale: vi } },
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
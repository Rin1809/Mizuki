import { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, TimeScale, ChartOptions, Filler } from 'chart.js';
import 'chartjs-adapter-date-fns';
import { useLanguage } from '@/hooks/useLanguage';
import { dateLocales } from '@/lib/dateLocales';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, TimeScale, Filler);

const VisitorTrendChart = () => {
  const [chartData, setChartData] = useState<any>({ datasets: [] });
  const { t, locale } = useLanguage();

  useEffect(() => {
    fetch(`/api/stats?endpoint=visitor-trends`)
      .then(res => res.json())
      .then(data => {
        if (!data || !data.trends) return;
        const labels = data.trends.map((d: any) => new Date(d.visit_day));
        const newVisitors = data.trends.map((d: any) => d.new_visitors);
        const returningVisitors = data.trends.map((d: any) => d.returning_visitors);

        setChartData({
          labels,
          datasets: [
            {
              label: t('chartLabels.newVisitors'),
              data: newVisitors,
              borderColor: '#73daca',
              backgroundColor: 'rgba(115, 218, 202, 0.2)',
              fill: true,
              tension: 0.4,
              yAxisID: 'y',
              borderWidth: 2,
              pointRadius: 2,
              pointBackgroundColor: '#73daca',
              pointHoverRadius: 5,
            },
            {
              label: t('chartLabels.returningVisitors'),
              data: returningVisitors,
              borderColor: '#bb9af7',
              backgroundColor: 'rgba(187, 154, 247, 0.2)',
              fill: true,
              tension: 0.4,
              yAxisID: 'y',
              borderWidth: 2,
              pointRadius: 2,
              pointBackgroundColor: '#bb9af7',
              pointHoverRadius: 5,
            }
          ]
        });
      });
  }, [t]);

  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
        mode: 'index',
        intersect: false,
    },
    scales: {
      x: { 
        type: 'time', 
        time: { unit: 'day' }, 
        adapters: { date: { locale: dateLocales[locale] } }, 
        ticks: { color: '#c0caf5' },
        grid: { color: 'rgba(192, 202, 245, 0.1)' }
      },
      y: {
        type: 'linear',
        position: 'left',
        ticks: { 
            color: '#c0caf5', 
            stepSize: 1
        },
        grid: { color: 'rgba(192, 202, 245, 0.1)' },
        beginAtZero: true, 
      }
    },
    plugins: {
      legend: { 
        position: 'top', 
        labels: { color: '#c0caf5' } 
      }
    }
  };

  return <div className="chart-container"><Line data={chartData} options={options} /></div>;
};

export default VisitorTrendChart;
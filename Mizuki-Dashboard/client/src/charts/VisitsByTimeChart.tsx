import { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, TimeScale, ChartOptions } from 'chart.js';
import 'chartjs-adapter-date-fns';
import { vi } from 'date-fns/locale';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, TimeScale);

const VisitsByTimeChart = () => {
  const [chartData, setChartData] = useState<any>({ datasets: [] });
  const [period, _setPeriod] = useState('day'); 

  useEffect(() => {
    fetch(`/api/stats/visits?period=${period}`)
      .then(res => res.json())
      .then(data => {
        if (!data || !data.byTime) return;
        const labels = data.byTime.map((d: any) => new Date(d.date));
        const visitCounts = data.byTime.map((d: any) => d.count);
        setChartData({
          labels,
          datasets: [{
            label: `Lượt truy cập theo ${period === 'day' ? 'ngày' : period === 'week' ? 'tuần' : 'tháng'}`,
            data: visitCounts,
            borderColor: 'rgb(137, 180, 250)',
            backgroundColor: 'rgba(137, 180, 250, 0.2)',
            fill: true,
            tension: 0.2
          }]
        });
      });
  }, [period]);

  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { 
        type: 'time', 
        time: { unit: period as 'day' | 'week' | 'month' },
        adapters: { date: { locale: vi } },
        ticks: { color: '#c0caf5' }
      },
      y: { ticks: { color: '#c0caf5', stepSize: 1 } }
    },
    plugins: {
      legend: { labels: { color: '#c0caf5' } }
    }
  };

  return (
    <div style={{ position: 'relative', height: '400px' }}>
      <Line data={chartData} options={options} />
    </div>
  );
};

export default VisitsByTimeChart;
import { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, TimeScale, ChartOptions, Filler } from 'chart.js';
import 'chartjs-adapter-date-fns';
import { vi } from 'date-fns/locale';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, TimeScale, Filler);

const CombinedVisitorTrendChart = () => {
  const [chartData, setChartData] = useState<any>({ datasets: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch('/api/stats/visits?period=day').then(res => res.json()),
      fetch('/api/stats/visitor-trends').then(res => res.json())
    ])
    .then(([visitsData, trendsData]) => {
      if (!visitsData?.byTime || !trendsData?.trends) {
        setLoading(false);
        return;
      }

      const labels = trendsData.trends.map((d: any) => new Date(d.visit_day));
      const newVisitors = trendsData.trends.map((d: any) => d.new_visitors);
      const returningVisitors = trendsData.trends.map((d: any) => d.returning_visitors);
      
      const totalVisits = visitsData.byTime.map((d: any) => d.count);

      setChartData({
        labels,
        datasets: [
          {
            label: 'Tổng lượt truy cập',
            data: totalVisits,
            borderColor: '#7dcfff',
            backgroundColor: 'rgba(125, 207, 255, 0.2)',
            yAxisID: 'yTotal',
            tension: 0.4,
            borderWidth: 3,
            fill: true,
            pointRadius: 2,
            pointBackgroundColor: '#7dcfff',
            pointHoverRadius: 5,
          },
          {
            label: 'Khách mới',
            data: newVisitors,
            borderColor: '#73daca',
            backgroundColor: 'rgba(115, 218, 202, 0.2)',
            yAxisID: 'yBreakdown',
            tension: 0.4,
            borderWidth: 2,
            fill: true,
            pointRadius: 2,
            pointBackgroundColor: '#73daca',
            pointHoverRadius: 5,
          },
          {
            label: 'Khách quay lại',
            data: returningVisitors,
            borderColor: '#bb9af7',
            backgroundColor: 'rgba(187, 154, 247, 0.2)',
            yAxisID: 'yBreakdown',
            tension: 0.4,
            borderWidth: 2,
            fill: true,
            pointRadius: 2,
            pointBackgroundColor: '#bb9af7',
            pointHoverRadius: 5,
          }
        ]
      });
      setLoading(false);
    })
    .catch(error => {
        console.error("Loi khi fetch combined trend data:", error);
        setLoading(false);
    });
  }, []);

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
        adapters: { date: { locale: vi } }, 
        ticks: { color: '#c0caf5' },
        grid: { color: 'rgba(192, 202, 245, 0.1)' }
      },
      yTotal: { 
        type: 'linear',
        position: 'left',
        beginAtZero: true,
        ticks: { color: '#7dcfff', stepSize: 1 },
        grid: { color: 'rgba(192, 202, 245, 0.1)' },
        title: {
          display: true,
          text: 'Tổng Lượt Truy Cập',
          color: '#7dcfff'
        }
      },
      yBreakdown: { 
        type: 'linear',
        position: 'right',
        beginAtZero: true,
        ticks: { color: '#c0caf5', stepSize: 1 },
        grid: { drawOnChartArea: false },
        title: {
          display: true,
          text: 'Phân Loại Khách',
          color: '#c0caf5'
        }
      }
    },
    plugins: {
      legend: { 
        position: 'bottom',
        labels: { color: '#c0caf5' } 
      },
      tooltip: {
        backgroundColor: 'rgba(26, 27, 38, 0.9)',
        titleFont: { size: 14 },
        bodyFont: { size: 12 },
        padding: 10,
        boxPadding: 4,
      }
    }
  };
  
  if (loading) return <p>Đang tải dữ liệu...</p>;

  return <div className="chart-container"><Line data={chartData} options={options} /></div>;
};

export default CombinedVisitorTrendChart;
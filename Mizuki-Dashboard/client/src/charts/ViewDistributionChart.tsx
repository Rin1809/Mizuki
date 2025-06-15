import { useState, useEffect } from 'react';
import { Bar } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ChartOptions } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const ViewDistributionChart = () => {
    const [chartData, setChartData] = useState<any>({ datasets: [] });

    useEffect(() => {
        fetch('/api/stats/interactions')
            .then(res => res.json())
            .then(data => {
                if (!data || !data.viewChangedCounts) return;
                
                const labels = data.viewChangedCounts.map((d: any) => d.view);
                const counts = data.viewChangedCounts.map((d: any) => d.count);
                
                setChartData({
                    labels,
                    datasets: [{
                        label: 'Số lượt xem',
                        data: counts,
                        backgroundColor: '#73daca',
                        borderColor: '#5aab9d',
                        borderWidth: 1,
                    }]
                });
            });
    }, []);

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

export default ViewDistributionChart;
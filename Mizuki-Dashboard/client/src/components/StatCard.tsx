import React from 'react';

interface StatCardProps {
  title: string;
  value: number | string | undefined;
}

const StatCard: React.FC<StatCardProps> = ({ title, value }) => (
  <div className="stat-card">
    <h3>{title}</h3>
    <p>{value?.toLocaleString('vi-VN') ?? '...'}</p>
  </div>
);

export default StatCard;
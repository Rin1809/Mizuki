import React from 'react';

interface StatCardProps {
  title: string;
  value: number | string | undefined;
  unit?: string;
  icon: React.ReactNode;
}

function StatCard({ title, value, unit, icon }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className="stat-card-icon">{icon}</div>
      <div className="stat-card-info">
        <p className="stat-card-title">{title}</p>
        <p className="stat-card-value">
          {value?.toLocaleString() ?? '...'}
          {unit && <span className="stat-unit">{unit}</span>}
        </p>
      </div>
    </div>
  );
}

export default StatCard;
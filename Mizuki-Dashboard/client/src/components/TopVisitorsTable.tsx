// Mizuki-Dashboard/client/src/components/TopVisitorsTable.tsx
import { useState, useEffect } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';

interface TopVisitor {
  ip_address: string;
  visit_count: number;
  last_visit: string;
}

const TopVisitorsTable = () => {
  const [visitors, setVisitors] = useState<TopVisitor[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/stats/top-visitors')
      .then(res => res.json())
      .then(data => {
        if (data && data.topVisitors) {
          setVisitors(data.topVisitors);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error("Loi lay top visitors:", err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <p>Đang tải dữ liệu...</p>;
  }

  if (visitors.length === 0) {
    return <p>Không có dữ liệu.</p>;
  }

  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>Địa chỉ IP</th>
            <th>Số lần truy cập</th>
            <th>Lần cuối truy cập</th>
          </tr>
        </thead>
        <tbody>
          {visitors.map((visitor) => (
            <tr key={visitor.ip_address}>
              <td><code>{visitor.ip_address}</code></td>
              <td>{visitor.visit_count.toLocaleString('vi-VN')}</td>
              <td>
                {formatDistanceToNow(new Date(visitor.last_visit), {
                  addSuffix: true,
                  locale: vi
                })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default TopVisitorsTable;
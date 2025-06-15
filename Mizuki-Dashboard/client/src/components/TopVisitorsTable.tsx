import { useState, useEffect } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { useLanguage } from '@/hooks/useLanguage';
import { dateLocales } from '@/lib/dateLocales';

interface TopVisitor {
  ip_address: string;
  visit_count: number;
  last_visit: string;
}

const TopVisitorsTable = () => {
  const [visitors, setVisitors] = useState<TopVisitor[]>([]);
  const [loading, setLoading] = useState(true);
  const { t, locale } = useLanguage();

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
    return <p>{t('loading')}</p>;
  }

  if (visitors.length === 0) {
    return <p>{t('noData')}</p>;
  }

  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>{t('tables.ipAddress')}</th>
            <th>{t('tables.visitCount')}</th>
            <th>{t('tables.lastVisit')}</th>
          </tr>
        </thead>
        <tbody>
          {visitors.map((visitor) => (
            <tr key={visitor.ip_address}>
              <td><code>{visitor.ip_address}</code></td>
              <td>{visitor.visit_count.toLocaleString(locale)}</td>
              <td>
                {formatDistanceToNow(new Date(visitor.last_visit), {
                  addSuffix: true,
                  locale: dateLocales[locale]
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
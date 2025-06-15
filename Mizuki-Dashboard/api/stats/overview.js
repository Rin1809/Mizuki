import { pool } from '../_lib/db.js';

export default async function handler(request, response) {
  try {
    // query data
    const [
      totalVisitsRes,
      uniqueVisitorsRes,
      totalInteractionsRes,
      totalSessionsRes
    ] = await Promise.all([
      pool.query('SELECT COUNT(*) FROM visits;'),
      pool.query('SELECT COUNT(DISTINCT ip_address) FROM visits;'),
      pool.query('SELECT COUNT(*) FROM interaction_events;'),
      pool.query('SELECT COUNT(*) FROM interaction_sessions;')
    ]);

    const overview = {
      totalVisits: parseInt(totalVisitsRes.rows[0].count, 10) || 0,
      uniqueVisitors: parseInt(uniqueVisitorsRes.rows[0].count, 10) || 0,
      totalInteractions: parseInt(totalInteractionsRes.rows[0].count, 10) || 0,
      totalSessions: parseInt(totalSessionsRes.rows[0].count, 10) || 0,
    };

    return response.status(200).json(overview);
  } catch (error) {
    // xu ly loi
    console.error('API Overview Error:', error);
    return response.status(500).json({ error: 'Loi lay data overview.' });
  }
}
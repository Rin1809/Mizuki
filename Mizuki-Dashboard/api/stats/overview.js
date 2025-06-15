const { pool } = require('../_lib/db.js');

module.exports = async (req, res) => {
  try {
    const totalVisitsRes = await pool.query('SELECT COUNT(*) FROM visits;');
    const uniqueVisitorsRes = await pool.query('SELECT COUNT(DISTINCT ip_address) FROM visits;');
    const totalInteractionsRes = await pool.query('SELECT COUNT(*) FROM interaction_events;');
    const totalSessionsRes = await pool.query('SELECT COUNT(*) FROM interaction_sessions;');
    // them query tinh thoi luong phien tb
    const avgSessionDurationRes = await pool.query(`
      SELECT AVG(EXTRACT(EPOCH FROM (end_time - start_time))) as avg_duration 
      FROM interaction_sessions 
      WHERE end_time IS NOT NULL AND start_time IS NOT NULL AND (end_time > start_time);
    `);

    const overview = {
      totalVisits: parseInt(totalVisitsRes.rows[0].count, 10),
      uniqueVisitors: parseInt(uniqueVisitorsRes.rows[0].count, 10),
      totalInteractions: parseInt(totalInteractionsRes.rows[0].count, 10),
      totalSessions: parseInt(totalSessionsRes.rows[0].count, 10),
      // format du lieu tra ve
      avgSessionDuration: avgSessionDurationRes.rows[0].avg_duration ? parseFloat(avgSessionDurationRes.rows[0].avg_duration).toFixed(1) : 0,
    };

    res.status(200).json(overview);
  } catch (error) {
    console.error('API Overview Error:', error);
    res.status(500).json({ error: 'Loi lay data overview.' });
  }
};
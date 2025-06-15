const { pool } = require('../_lib/db.js');

module.exports = async (req, res) => {
  try {
    const totalVisitsRes = await pool.query('SELECT COUNT(*) FROM visits;');
    const uniqueVisitorsRes = await pool.query('SELECT COUNT(DISTINCT ip_address) FROM visits;');
    const totalInteractionsRes = await pool.query('SELECT COUNT(*) FROM interaction_events;');
    const totalSessionsRes = await pool.query('SELECT COUNT(*) FROM interaction_sessions;');

    const overview = {
      totalVisits: parseInt(totalVisitsRes.rows[0].count, 10),
      uniqueVisitors: parseInt(uniqueVisitorsRes.rows[0].count, 10),
      totalInteractions: parseInt(totalInteractionsRes.rows[0].count, 10),
      totalSessions: parseInt(totalSessionsRes.rows[0].count, 10),
    };

    res.status(200).json(overview);
  } catch (error) {
    console.error('API Overview Error:', error);
    res.status(500).json({ error: 'Loi lay data overview.' });
  }
};
// Mizuki-Dashboard/api/stats/live-visitors.js
const { pool } = require('../_lib/db.js');

module.exports = async (req, res) => {
    try {
        // dem so luong IP rieng biet trong 5 phut qua
        const liveVisitorsRes = await pool.query(`
            SELECT COUNT(DISTINCT ip_address) 
            FROM visits
            WHERE visit_time > NOW() - INTERVAL '5 minute';
        `);

        res.status(200).json({
            live_count: parseInt(liveVisitorsRes.rows[0].count, 10) || 0,
        });
    } catch (error) {
        console.error('API Live Visitors Error:', error);
        res.status(500).json({ error: 'Loi lay data live visitors.' });
    }
};
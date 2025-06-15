// Mizuki-Dashboard/api/stats/visits-by-hour.js
const { pool } = require('../_lib/db.js');

// phan bo luot truy cap theo gio trong ngay
module.exports = async (req, res) => {
    try {
        const queryRes = await pool.query(`
            SELECT
                EXTRACT(HOUR FROM visit_time AT TIME ZONE 'Asia/Ho_Chi_Minh') as hour,
                COUNT(*) as count
            FROM visits
            GROUP BY hour
            ORDER BY hour ASC;
        `);

        res.status(200).json({
            distribution: queryRes.rows,
        });
    } catch (error) {
        console.error('API Visits by Hour Error:', error);
        res.status(500).json({ error: 'Loi lay data phan bo truy cap theo gio.' });
    }
};
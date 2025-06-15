// Mizuki-Dashboard/api/stats/top-visitors.js
const { pool } = require('../_lib/db.js');

module.exports = async (req, res) => {
    try {
        // Lấy 20 địa chỉ IP có số lần truy cập nhiều nhất
        const topVisitorsRes = await pool.query(`
            SELECT
                ip_address,
                COUNT(*) AS visit_count,
                MAX(visit_time) as last_visit
            FROM visits
            GROUP BY ip_address
            ORDER BY visit_count DESC, last_visit DESC
            LIMIT 20;
        `);

        res.status(200).json({
            topVisitors: topVisitorsRes.rows,
        });
    } catch (error) {
        console.error('API Top Visitors Error:', error);
        res.status(500).json({ error: 'Loi lay data khach truy cap thuong xuyen.' });
    }
};
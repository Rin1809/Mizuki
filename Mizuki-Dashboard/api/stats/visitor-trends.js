// Mizuki-Dashboard/api/stats/visitor-trends.js
const { pool } = require('../_lib/db.js');

module.exports = async (req, res) => {
    try {
        // Lấy dữ liệu 30 ngày gần nhất
        const trendsRes = await pool.query(`
            WITH first_visits AS (
                SELECT 
                    ip_address, 
                    MIN(DATE_TRUNC('day', visit_time)) as first_visit_date
                FROM visits
                GROUP BY ip_address
            )
            SELECT
                DATE_TRUNC('day', v.visit_time)::DATE AS visit_day,
                COUNT(DISTINCT v.ip_address) FILTER (WHERE DATE_TRUNC('day', v.visit_time) = fv.first_visit_date) AS new_visitors,
                COUNT(DISTINCT v.ip_address) FILTER (WHERE DATE_TRUNC('day', v.visit_time) > fv.first_visit_date) AS returning_visitors
            FROM visits v
            JOIN first_visits fv ON v.ip_address = fv.ip_address
            WHERE v.visit_time > NOW() - INTERVAL '365 day'
            GROUP BY visit_day
            ORDER BY visit_day ASC;
        `);

        res.status(200).json({
            trends: trendsRes.rows,
        });
    } catch (error) {
        console.error('API Visitor Trends Error:', error);
        res.status(500).json({ error: 'Loi lay data xu huong khach truy cap.' });
    }
};
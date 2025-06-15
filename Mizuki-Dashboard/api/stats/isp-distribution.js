// Mizuki-Dashboard/api/stats/isp-distribution.js
const { pool } = require('../_lib/db.js');

module.exports = async (req, res) => {
    try {
        // Lấy 15 ISP có nhiều lượt truy cập nhất
        const ispRes = await pool.query(`
            SELECT 
                isp, 
                COUNT(*) AS count
            FROM visits
            WHERE isp IS NOT NULL AND isp <> 'N/A' AND isp <> ''
            GROUP BY isp
            ORDER BY count DESC
            LIMIT 15;
        `);

        res.status(200).json({
            ispDistribution: ispRes.rows,
        });
    } catch (error) {
        console.error('API ISP Distribution Error:', error);
        res.status(500).json({ error: 'Loi lay data phan bo ISP.' });
    }
};
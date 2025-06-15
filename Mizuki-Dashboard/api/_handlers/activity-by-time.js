// Mizuki-Dashboard/api/stats/activity-by-time.js
const { pool } = require('../_lib/db.js');

module.exports = async (req, res) => {
    try {
        // lay data theo tung gio cua tung ngay trong tuan
        const heatmapRes = await pool.query(`
            SELECT 
                EXTRACT(ISODOW FROM visit_time AT TIME ZONE 'Asia/Ho_Chi_Minh') as day_of_week, -- 1=T2, 7=CN
                EXTRACT(HOUR FROM visit_time AT TIME ZONE 'Asia/Ho_Chi_Minh') as hour_of_day,
                COUNT(*) as count
            FROM visits
            WHERE visit_time > NOW() - INTERVAL '30 day'
            GROUP BY day_of_week, hour_of_day
            ORDER BY day_of_week, hour_of_day;
        `);

        res.status(200).json({
            heatmapData: heatmapRes.rows,
        });
    } catch (error) {
        console.error('API Activity By Time (Heatmap) Error:', error);
        res.status(500).json({ error: 'Loi lay data hoat dong cho heatmap.' });
    }
};
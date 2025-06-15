// Mizuki-Dashboard/api/stats/activity-by-time.js
const { pool } = require('../_lib/db.js');

module.exports = async (req, res) => {
    try {
        // Lấy dữ liệu theo giờ trong ngày (timezone Việt Nam)
        const byHourRes = await pool.query(`
            SELECT 
                EXTRACT(HOUR FROM visit_time AT TIME ZONE 'Asia/Ho_Chi_Minh') as hour,
                COUNT(*) as count
            FROM visits
            GROUP BY hour
            ORDER BY hour ASC;
        `);

        // Lấy dữ liệu theo ngày trong tuần (timezone Việt Nam, 1=T2, 7=CN)
        const byDayOfWeekRes = await pool.query(`
            SELECT 
                EXTRACT(ISODOW FROM visit_time AT TIME ZONE 'Asia/Ho_Chi_Minh') as day_of_week,
                COUNT(*) as count
            FROM visits
            GROUP BY day_of_week
            ORDER BY day_of_week ASC;
        `);

        res.status(200).json({
            byHour: byHourRes.rows,
            byDayOfWeek: byDayOfWeekRes.rows,
        });
    } catch (error) {
        console.error('API Activity By Time Error:', error);
        res.status(500).json({ error: 'Loi lay data hoat dong theo thoi gian.' });
    }
};
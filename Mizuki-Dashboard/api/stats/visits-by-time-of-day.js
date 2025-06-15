// Mizuki-Dashboard/api/stats/visits-by-time-of-day.js
const { pool } = require('../_lib/db.js');

// phan bo luot truy cap theo cac buoi trong ngay
module.exports = async (req, res) => {
    try {
        const queryRes = await pool.query(`
            WITH visits_with_time_of_day AS (
                SELECT
                    CASE
                        WHEN EXTRACT(HOUR FROM visit_time AT TIME ZONE 'Asia/Ho_Chi_Minh') BETWEEN 5 AND 11 THEN 'Sáng (05:00 - 11:59)'
                        WHEN EXTRACT(HOUR FROM visit_time AT TIME ZONE 'Asia/Ho_Chi_Minh') BETWEEN 12 AND 16 THEN 'Trưa & Chiều (12:00 - 16:59)'
                        WHEN EXTRACT(HOUR FROM visit_time AT TIME ZONE 'Asia/Ho_Chi_Minh') BETWEEN 17 AND 21 THEN 'Tối (17:00 - 21:59)'
                        ELSE 'Đêm (22:00 - 04:59)'
                    END AS time_of_day
                FROM visits
            )
            SELECT
                time_of_day,
                COUNT(*) as count
            FROM visits_with_time_of_day
            GROUP BY time_of_day
            ORDER BY
                CASE
                    WHEN time_of_day = 'Sáng (05:00 - 11:59)' THEN 1
                    WHEN time_of_day = 'Trưa & Chiều (12:00 - 16:59)' THEN 2
                    WHEN time_of_day = 'Tối (17:00 - 21:59)' THEN 3
                    ELSE 4
                END;
        `);

        res.status(200).json({
            distribution: queryRes.rows,
        });
    } catch (error) {
        console.error('API Visits by Time of Day Error:', error);
        res.status(500).json({ error: 'Loi lay data phan bo truy cap theo buoi.' });
    }
};
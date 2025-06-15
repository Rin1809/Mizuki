const { pool } = require('../_lib/db.js');

module.exports = async (req, res) => {
    try {
        const queryRes = await pool.query(`
            WITH visits_with_time_of_day AS (
                SELECT
                    CASE
                        WHEN EXTRACT(HOUR FROM visit_time AT TIME ZONE 'Asia/Ho_Chi_Minh') BETWEEN 5 AND 11 THEN 'morning'
                        WHEN EXTRACT(HOUR FROM visit_time AT TIME ZONE 'Asia/Ho_Chi_Minh') BETWEEN 12 AND 16 THEN 'afternoon'
                        WHEN EXTRACT(HOUR FROM visit_time AT TIME ZONE 'Asia/Ho_Chi_Minh') BETWEEN 17 AND 21 THEN 'evening'
                        ELSE 'night'
                    END AS time_of_day,
                    EXTRACT(HOUR FROM visit_time AT TIME ZONE 'Asia/Ho_Chi_Minh') as hour
                FROM visits
            )
            SELECT
                time_of_day,
                COUNT(*) as count
            FROM visits_with_time_of_day
            GROUP BY time_of_day
            ORDER BY
                CASE
                    WHEN time_of_day = 'morning' THEN 1
                    WHEN time_of_day = 'afternoon' THEN 2
                    WHEN time_of_day = 'evening' THEN 3
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
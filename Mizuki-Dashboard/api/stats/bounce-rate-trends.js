// Mizuki-Dashboard/api/stats/bounce-rate-trends.js
const { pool } = require('../_lib/db.js');

module.exports = async (req, res) => {
    try {
        const trendsRes = await pool.query(`
            WITH daily_sessions AS (
                SELECT 
                    DATE_TRUNC('day', start_time AT TIME ZONE 'Asia/Ho_Chi_Minh')::DATE AS day,
                    id as session_id
                FROM interaction_sessions
                WHERE start_time > NOW() - INTERVAL '30 day'
            ),
            event_counts AS (
                SELECT 
                    session_id,
                    COUNT(*) as event_count
                FROM interaction_events
                GROUP BY session_id
            ),
            daily_bounce_stats AS (
                SELECT
                    ds.day,
                    COUNT(ds.session_id) as total_sessions,
                    COUNT(ds.session_id) FILTER (WHERE ec.event_count = 1) as bounced_sessions
                FROM daily_sessions ds
                JOIN event_counts ec ON ds.session_id = ec.session_id
                GROUP BY ds.day
            )
            SELECT
                day,
                (bounced_sessions::DECIMAL / total_sessions * 100) as bounce_rate
            FROM daily_bounce_stats
            WHERE total_sessions > 0
            ORDER BY day ASC;
        `);

        res.status(200).json({
            trends: trendsRes.rows,
        });
    } catch (error) {
        console.error('API Bounce Rate Trends Error:', error);
        res.status(500).json({ error: 'Loi lay data xu huong ty le thoat.' });
    }
};
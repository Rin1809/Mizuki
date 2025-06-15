// Mizuki-Dashboard/api/stats/platform-distribution.js
const { pool } = require('../_lib/db.js');

module.exports = async (req, res) => {
    try {
        // Phân tích trình duyệt
        const browserRes = await pool.query(`
            SELECT
                CASE
                    WHEN user_agent ILIKE '%Edg/%' THEN 'Edge'
                    WHEN user_agent ILIKE '%Firefox/%' THEN 'Firefox'
                    WHEN user_agent ILIKE '%SamsungBrowser/%' THEN 'Samsung Browser'
                    WHEN user_agent ILIKE '%Chrome/%' AND user_agent NOT ILIKE '%Chromium%' THEN 'Chrome'
                    WHEN user_agent ILIKE '%Safari/%' AND user_agent NOT ILIKE '%Chrome/%' THEN 'Safari'
                    WHEN user_agent ILIKE '%Opera/%' OR user_agent ILIKE '%OPR/%' THEN 'Opera'
                    WHEN user_agent ILIKE '%Trident/%' OR user_agent ILIKE '%MSIE%' THEN 'Internet Explorer'
                    ELSE 'Khác'
                END AS browser,
                COUNT(*) as count
            FROM visits
            GROUP BY browser
            ORDER BY count DESC;
        `);

        // Phân tích hệ điều hành
        const osRes = await pool.query(`
            SELECT
                CASE
                    WHEN user_agent ILIKE '%Windows NT 10.0%' THEN 'Windows 10/11'
                    WHEN user_agent ILIKE '%Windows NT 6.3%' THEN 'Windows 8.1'
                    WHEN user_agent ILIKE '%Windows NT 6.2%' THEN 'Windows 8'
                    WHEN user_agent ILIKE '%Windows NT 6.1%' THEN 'Windows 7'
                    WHEN user_agent ILIKE '%Windows%' THEN 'Windows'
                    WHEN user_agent ILIKE '%Android%' THEN 'Android'
                    WHEN user_agent ILIKE '%iPhone OS%' OR user_agent ILIKE '%iPad%' THEN 'iOS'
                    WHEN user_agent ILIKE '%Mac OS X%' THEN 'macOS'
                    WHEN user_agent ILIKE '%Linux%' THEN 'Linux'
                    ELSE 'Khác'
                END AS os,
                COUNT(*) as count
            FROM visits
            GROUP BY os
            ORDER BY count DESC;
        `);

        res.status(200).json({
            byBrowser: browserRes.rows,
            byOs: osRes.rows,
        });
    } catch (error) {
        console.error('API Platform Distribution Error:', error);
        res.status(500).json({ error: 'Loi lay data phan bo nen tang.' });
    }
};
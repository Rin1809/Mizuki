const { pool } = require('../_lib/db.js');

module.exports = async (req, res) => {
    try {
        const distributionRes = await pool.query(`
            WITH visit_counts AS (
              SELECT ip_address, COUNT(*) AS visit_count
              FROM visits
              GROUP BY ip_address
            )
            SELECT
              CASE
                WHEN visit_count = 1 THEN '1_time'
                WHEN visit_count BETWEEN 2 AND 3 THEN '2-3_times'
                WHEN visit_count BETWEEN 4 AND 5 THEN '4-5_times'
                ELSE '6+_times'
              END AS category,
              COUNT(*) AS num_visitors
            FROM visit_counts
            GROUP BY category
            ORDER BY MIN(visit_count);
        `);

        res.status(200).json({
            distribution: distributionRes.rows,
        });
    } catch (error) {
        console.error('API Visitor Distribution Error:', error);
        res.status(500).json({ error: 'Loi lay data phan bo khach truy cap.' });
    }
};
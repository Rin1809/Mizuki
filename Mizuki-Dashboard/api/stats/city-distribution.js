// Mizuki-Dashboard/api/stats/city-distribution.js
const { pool } = require('../_lib/db.js');

module.exports = async (req, res) => {
    try {
        const cityRes = await pool.query(`
            SELECT 
                city, 
                country,
                COUNT(*) AS count
            FROM visits
            WHERE city IS NOT NULL AND city <> 'N/A' AND city <> '' AND country IS NOT NULL AND country <> 'N/A'
            GROUP BY city, country
            ORDER BY count DESC
            LIMIT 15;
        `);

        res.status(200).json({
            cityDistribution: cityRes.rows,
        });
    } catch (error) {
        console.error('API City Distribution Error:', error);
        res.status(500).json({ error: 'Loi lay data phan bo thanh pho.' });
    }
};
// Mizuki-Dashboard/api/stats/language-distribution.js
const { pool } = require('../_lib/db.js');

module.exports = async (req, res) => {
    try {
        const langRes = await pool.query(`
            SELECT
                details ->> 'language' as language,
                COUNT(*) as count
            FROM interaction_events
            WHERE event_type = 'language_selected'
            GROUP BY language
            ORDER BY count DESC;
        `);

        res.status(200).json({
            languageDistribution: langRes.rows,
        });
    } catch (error) {
        console.error('API Language Distribution Error:', error);
        res.status(500).json({ error: 'Loi lay data phan bo ngon ngu.' });
    }
};
// api/stats/visits.js
import { pool } from '../_lib/db.js';

export default async function handler(req, res) {
    const { period = 'day' } = req.query;
    if (!['day', 'week', 'month'].includes(period)) {
        return res.status(400).json({ error: 'Thoi gian ko hop le.' });
    }
    try {
        const visitsByTimeRes = await pool.query(
            `SELECT DATE_TRUNC($1, visit_time) AS date, COUNT(*) AS count
             FROM visits
             WHERE visit_time > NOW() - INTERVAL '1 year'
             GROUP BY date
             ORDER BY date ASC;`,
            [period]
        );

        const visitsByCountryRes = await pool.query(
            `SELECT country, COUNT(*) AS count
             FROM visits
             WHERE country IS NOT NULL AND country <> 'N/A' AND country <> 'Local'
             GROUP BY country
             ORDER BY count DESC
             LIMIT 10;`
        );

        res.status(200).json({
            byTime: visitsByTimeRes.rows,
            byCountry: visitsByCountryRes.rows,
        });
    } catch (error) {
        res.status(500).json({ error: 'Loi lay data visit.' });
    }
}
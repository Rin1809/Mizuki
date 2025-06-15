import { pool } from '../_lib/db.js';

export default async function handler(request, response) {
    const { period = 'day' } = request.query;

    if (!['day', 'week', 'month'].includes(period)) {
        return response.status(400).json({ error: 'Thoi gian ko hop le.' });
    }

    try {
        const [visitsByTimeRes, visitsByCountryRes] = await Promise.all([
            // query theo tgian
            pool.query(
                `SELECT DATE_TRUNC($1, visit_time) AS date, COUNT(*) AS count
                 FROM visits
                 WHERE visit_time > NOW() - INTERVAL '1 year'
                 GROUP BY date
                 ORDER BY date ASC;`,
                [period]
            ),
            // query theo qgia
            pool.query(
                `SELECT country, COUNT(*) AS count
                 FROM visits
                 WHERE country IS NOT NULL AND country <> 'N/A' AND country <> 'Local'
                 GROUP BY country
                 ORDER BY count DESC
                 LIMIT 10;`
            )
        ]);

        return response.status(200).json({
            byTime: visitsByTimeRes.rows,
            byCountry: visitsByCountryRes.rows,
        });
    } catch (error) {
        console.error('API Visits Error:', error);
        return response.status(500).json({ error: 'Loi lay data visit.' });
    }
}
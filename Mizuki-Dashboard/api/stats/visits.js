const { pool } = require('../_lib/db.js');

module.exports = async (req, res) => {
    // mac dinh la gio
    const { period = 'hour' } = req.query;

    if (!['hour', 'day', 'week', 'month'].includes(period)) {
        return res.status(400).json({ error: 'Thoi gian ko hop le.' });
    }
    
    let interval;
    let groupBy = `DATE_TRUNC($1, visit_time)`;

    switch (period) {
        case 'hour':
            interval = `72 hour`;
            break;
        case 'day':
            interval = `30 day`;
            break;
        case 'week':
            interval = `26 week`;
            break;
        case 'month':
            interval = `12 month`;
            break;
    }

    try {
        const visitsByTimeRes = await pool.query(
            `SELECT ${groupBy} AS date, COUNT(*) AS count
             FROM visits
             WHERE visit_time > NOW() - INTERVAL '${interval}'
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
        console.error('API Visits Error:', error);
        res.status(500).json({ error: 'Loi lay data visit.' });
    }
};
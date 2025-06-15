const { pool } = require('../_lib/db.js');

module.exports = async (req, res) => {
    try {
        const eventTypeCountsRes = await pool.query(
            `SELECT event_type, COUNT(*) as count
             FROM interaction_events
             GROUP BY event_type
             ORDER BY count DESC;`
        );
        
        const viewChangedCountsRes = await pool.query(
            `SELECT details ->> 'currentView' as view, COUNT(*) as count
             FROM interaction_events
             WHERE event_type = 'view_changed'
             GROUP BY view
             ORDER BY count DESC
             LIMIT 10;`
        );

        res.status(200).json({
            eventTypeCounts: eventTypeCountsRes.rows,
            viewChangedCounts: viewChangedCountsRes.rows,
        });
    } catch (error) {
        console.error('API Interactions Error:', error);
        res.status(500).json({ error: 'Loi lay data interaction.' });
    }
};
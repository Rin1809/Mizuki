import { pool } from '../_lib/db.js';

export default async function handler(request, response) {
    try {
        const [eventTypeCountsRes, viewChangedCountsRes] = await Promise.all([
            pool.query(
                `SELECT event_type, COUNT(*) as count
                 FROM interaction_events
                 GROUP BY event_type
                 ORDER BY count DESC;`
            ),
            pool.query(
                `SELECT details ->> 'currentView' as view, COUNT(*) as count
                 FROM interaction_events
                 WHERE event_type = 'view_changed'
                 GROUP BY view
                 ORDER BY count DESC
                 LIMIT 10;`
            )
        ]);

        return response.status(200).json({
            eventTypeCounts: eventTypeCountsRes.rows,
            viewChangedCounts: viewChangedCountsRes.rows,
        });
    } catch (error) {
        console.error('API Interactions Error:', error);
        return response.status(500).json({ error: 'Loi lay data interaction.' });
    }
}
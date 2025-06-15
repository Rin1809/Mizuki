// Mizuki-Dashboard/api/stats/detailed-interactions.js
const { pool } = require('../_lib/db.js');

module.exports = async (req, res) => {
    const { type } = req.query;

    try {
        let queryResult;
        switch (type) {
            case 'about-subsections':
                queryResult = await pool.query(`
                    SELECT details ->> 'currentSubSection' as item, COUNT(*) as count
                    FROM interaction_events
                    WHERE event_type = 'about_subsection_viewed' AND details ->> 'currentSubSection' <> 'N/A'
                    GROUP BY item
                    ORDER BY count DESC
                    LIMIT 10;
                `);
                break;
            case 'gallery-hotspots':
                queryResult = await pool.query(`
                    SELECT details ->> 'imageIndex' as item, COUNT(*) as count
                    FROM interaction_events
                    WHERE event_type = 'gallery_image_viewed'
                    GROUP BY item
                    ORDER BY count DESC
                    LIMIT 10;
                `);
                break;
            case 'guestbook-trends':
                queryResult = await pool.query(`
                    SELECT DATE_TRUNC('day', event_time AT TIME ZONE 'Asia/Ho_Chi_Minh')::DATE AS date, COUNT(*) AS count
                    FROM interaction_events
                    WHERE event_type = 'guestbook_entry_submitted'
                    GROUP BY date
                    ORDER BY date ASC;
                `);
                break;
            default:
                return res.status(400).json({ error: 'Loai tuong tac khong hop le.' });
        }
        res.status(200).json({ data: queryResult.rows });
    } catch (error) {
        console.error(`API Detailed Interactions Error (type: ${type}):`, error);
        res.status(500).json({ error: `Loi lay data cho loai tuong tac: ${type}` });
    }
};
// Mizuki-Dashboard/api/stats.js

// Import tat ca handler
const overviewHandler = require('./_handlers/overview.js');
const visitsHandler = require('./_handlers/visits.js');
const interactionsHandler = require('./_handlers/interactions.js');
const topVisitorsHandler = require('./_handlers/top-visitors.js');
const visitorDistributionHandler = require('./_handlers/visitor-distribution.js');
const visitorTrendsHandler = require('./_handlers/visitor-trends.js');
const ispDistributionHandler = require('./_handlers/isp-distribution.js');
const sessionDurationHandler = require('./_handlers/session-duration.js');
const platformDistributionHandler = require('./_handlers/platform-distribution.js');
const activityByTimeHandler = require('./_handlers/activity-by-time.js');
const languageDistributionHandler = require('./_handlers/language-distribution.js');
const cityDistributionHandler = require('./_handlers/city-distribution.js');
const detailedInteractionsHandler = require('./_handlers/detailed-interactions.js');
const botAnalysisHandler = require('./_handlers/bot-analysis.js');
const liveVisitorsHandler = require('./_handlers/live-visitors.js');
const bounceRateTrendsHandler = require('./_handlers/bounce-rate-trends.js');
const visitsByTimeOfDayHandler = require('./_handlers/visits-by-time-of-day.js');
const visitsByHourHandler = require('./_handlers/visits-by-hour.js');

// Map endpoint voi handler
const handlers = {
  'overview': overviewHandler,
  'visits': visitsHandler,
  'interactions': interactionsHandler,
  'top-visitors': topVisitorsHandler,
  'visitor-distribution': visitorDistributionHandler,
  'visitor-trends': visitorTrendsHandler,
  'isp-distribution': ispDistributionHandler,
  'session-duration': sessionDurationHandler,
  'platform-distribution': platformDistributionHandler,
  'activity-by-time': activityByTimeHandler,
  'language-distribution': languageDistributionHandler,
  'city-distribution': cityDistributionHandler,
  'detailed-interactions': detailedInteractionsHandler,
  'bot-analysis': botAnalysisHandler,
  'live-visitors': liveVisitorsHandler,
  'bounce-rate-trends': bounceRateTrendsHandler,
  'visits-by-time-of-day': visitsByTimeOfDayHandler,
  'visits-by-hour': visitsByHourHandler,
};

// function chinh
module.exports = async (req, res) => {
  const { endpoint } = req.query;

  const handler = handlers[endpoint];

  if (handler) {
    try {
      await handler(req, res);
    } catch (error) {
      console.error(`[ROUTER][LOI] Endpoint "${endpoint}":`, error);
      res.status(500).json({ error: `Loi server tai endpoint: ${endpoint}` });
    }
  } else {
    // endpoint ko ton tai
    res.status(404).json({ error: 'Endpoint khong hop le' });
  }
};
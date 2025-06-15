// Mizuki-Dashboard/api/index.js
const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');

dotenv.config({ path: '../.env' }); 

const overviewHandler = require('./stats/overview.js');
const visitsHandler = require('./stats/visits.js');
const interactionsHandler = require('./stats/interactions.js');
const topVisitorsHandler = require('./stats/top-visitors.js');
const visitorDistributionHandler = require('./stats/visitor-distribution.js');
const visitorTrendsHandler = require('./stats/visitor-trends.js');
const ispDistributionHandler = require('./stats/isp-distribution.js');
const sessionDurationHandler = require('./stats/session-duration.js');
const platformDistributionHandler = require('./stats/platform-distribution.js');
const activityByTimeHandler = require('./stats/activity-by-time.js');
const languageDistributionHandler = require('./stats/language-distribution.js');
const cityDistributionHandler = require('./stats/city-distribution.js');
const detailedInteractionsHandler = require('./stats/detailed-interactions.js');
const botAnalysisHandler = require('./stats/bot-analysis.js');
const liveVisitorsHandler = require('./stats/live-visitors.js');
const bounceRateTrendsHandler = require('./stats/bounce-rate-trends.js');
const visitsByTimeOfDayHandler = require('./stats/visits-by-time-of-day.js');
const visitsByHourHandler = require('./stats/visits-by-hour.js');

const app = express();

// Sử dụng CORS và JSON parser
app.use(cors());
app.use(express.json());

// Định nghĩa tất cả các routes API
app.get('/api/stats/overview', overviewHandler);
app.get('/api/stats/visits', visitsHandler);
app.get('/api/stats/interactions', interactionsHandler);
app.get('/api/stats/top-visitors', topVisitorsHandler);
app.get('/api/stats/visitor-distribution', visitorDistributionHandler);
app.get('/api/stats/visitor-trends', visitorTrendsHandler);
app.get('/api/stats/isp-distribution', ispDistributionHandler);
app.get('/api/stats/session-duration', sessionDurationHandler);
app.get('/api/stats/platform-distribution', platformDistributionHandler);
app.get('/api/stats/activity-by-time', activityByTimeHandler);
app.get('/api/stats/language-distribution', languageDistributionHandler);
app.get('/api/stats/city-distribution', cityDistributionHandler);
app.get('/api/stats/detailed-interactions', detailedInteractionsHandler);
app.get('/api/stats/bot-analysis', botAnalysisHandler);
app.get('/api/stats/live-visitors', liveVisitorsHandler);
app.get('/api/stats/bounce-rate-trends', bounceRateTrendsHandler);
app.get('/api/stats/visits-by-time-of-day', visitsByTimeOfDayHandler);
app.get('/api/stats/visits-by-hour', visitsByHourHandler);

app.get('/api', (req, res) => {
  res.send('Mizuki Dashboard API is running! ✨');
});

module.exports = app;


const port = process.env.API_PORT || 3001;
if (process.env.NODE_ENV !== 'production') {
  app.listen(port, () => {
    console.log(`🚀 API server (local) đang chay tai http://localhost:${port}`);
  });
}
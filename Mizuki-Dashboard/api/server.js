// Mizuki-Dashboard/api/server.js
const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');

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
// them handler moi
const cityDistributionHandler = require('./stats/city-distribution.js');
const detailedInteractionsHandler = require('./stats/detailed-interactions.js');
const botAnalysisHandler = require('./stats/bot-analysis.js');


dotenv.config({ path: '../.env' });

const app = express();
const port = process.env.API_PORT || 3001;

app.use(cors());
app.use(express.json());

const run = (handler) => (req, res) => {
    if (!req.socket) {
        req.socket = { remoteAddress: '::1' };
    }
    handler(req, res);
};

app.get('/api/stats/overview', run(overviewHandler));
app.get('/api/stats/visits', run(visitsHandler));
app.get('/api/stats/interactions', run(interactionsHandler));
app.get('/api/stats/top-visitors', run(topVisitorsHandler));
app.get('/api/stats/visitor-distribution', run(visitorDistributionHandler));
app.get('/api/stats/visitor-trends', run(visitorTrendsHandler));
app.get('/api/stats/isp-distribution', run(ispDistributionHandler));
app.get('/api/stats/session-duration', run(sessionDurationHandler));
app.get('/api/stats/platform-distribution', run(platformDistributionHandler));
app.get('/api/stats/activity-by-time', run(activityByTimeHandler));
app.get('/api/stats/language-distribution', run(languageDistributionHandler));
// them route moi
app.get('/api/stats/city-distribution', run(cityDistributionHandler));
app.get('/api/stats/detailed-interactions', run(detailedInteractionsHandler));
app.get('/api/stats/bot-analysis', run(botAnalysisHandler));

app.get('/', (req, res) => {
  res.send('Mizuki Dashboard API Server (Local) is running! ✨');
});

app.listen(port, () => {
  console.log(`🚀 API server (local) dang chay tai http://localhost:${port}`);
});
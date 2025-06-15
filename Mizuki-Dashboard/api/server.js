const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');

const overviewHandler = require('./stats/overview.js');
const visitsHandler = require('./stats/visits.js');
const interactionsHandler = require('./stats/interactions.js');

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

app.get('/', (req, res) => {
  res.send('Mizuki Dashboard API Server (Local) is running! ✨');
});

app.listen(port, () => {
  console.log(`🚀 API server (local) dang chay tai http://localhost:${port}`);
});
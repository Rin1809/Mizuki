// api/server.js
import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';

// import handlers
import overviewHandler from './stats/overview.js';
import visitsHandler from './stats/visits.js';
import interactionsHandler from './stats/interactions.js';

// tim file .env o thu muc cha (Mizuki-Dashboard)
dotenv.config({ path: '../.env' });

const app = express();
const port = process.env.API_PORT || 3001;

// middleware
app.use(cors());
app.use(express.json());

// adapter cho handler serverless
const run = (handler) => (req, res) => {
    // mo phong req.socket cho local
    if (!req.socket) {
        req.socket = { remoteAddress: '::1' };
    }
    handler(req, res);
};

// routes
app.get('/api/stats/overview', run(overviewHandler));
app.get('/api/stats/visits', run(visitsHandler));
app.get('/api/stats/interactions', run(interactionsHandler));

app.get('/', (req, res) => {
  res.send('Mizuki Dashboard API Server (Local) is running! ✨');
});

app.listen(port, () => {
  console.log(`🚀 API server (local) dang chay tai http://localhost:${port}`);
});
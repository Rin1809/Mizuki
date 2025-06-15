const pg = require('pg');
const dotenv = require('dotenv');

dotenv.config({ path: '../.env' }); 

const { Pool } = pg;
const connectionString = process.env.DATABASE_URL;

if (!connectionString) {
  console.error('DB_FATAL_ERROR: DATABASE_URL is not set.');
}

const poolConfig = {
  connectionString,
};

if (process.env.NODE_ENV === 'production' && connectionString && (connectionString.includes('neon.tech') || connectionString.includes('aws.neon.tech'))) {
  poolConfig.ssl = { rejectUnauthorized: false };
}

const pool = new Pool(poolConfig);

pool.on('error', (err, client) => {
  console.error('DB_POOL_ERROR: Loi bat ngo', { error: err.message });
});

module.exports = { pool };
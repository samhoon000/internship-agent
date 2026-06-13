import pg from 'pg';
import dotenv from 'dotenv';

import logger from './logger.js';
import { sendDiscordAlert } from './alerting.js';

dotenv.config();

const { Pool } = pg;

// Support SSL configurations dynamically for cloud databases (Supabase, Neon, etc.)
const isProductionDb = process.env.DB_SSL === 'true' || 
                       (process.env.DATABASE_URL && 
                        (process.env.DATABASE_URL.includes('supabase') || 
                         process.env.DATABASE_URL.includes('neon.tech')));

const sslConfig = isProductionDb ? { rejectUnauthorized: false } : false;

const poolConfig = process.env.DATABASE_URL
  ? {
      connectionString: process.env.DATABASE_URL,
      ssl: sslConfig,
    }
  : {
      host: process.env.DB_HOST || 'localhost',
      port: parseInt(process.env.DB_PORT || '5432', 10),
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'postgres',
      database: process.env.DB_NAME || 'internship',
      ssl: sslConfig,
    };

const pool = new Pool(poolConfig);

// Keep reference to the original query method
const originalQuery = pool.query.bind(pool);

// Override query method to translate MySQL '?' placeholders to PostgreSQL '$1', '$2', ...
// and wrap results in [rows, fields] to preserve mysql2's array destructuring syntax.
pool.query = async function (sql, params = []) {
  let index = 1;
  const pgSql = sql.replace(/\?/g, () => `$${index++}`);
  const res = await originalQuery(pgSql, params);
  return [res.rows, res];
};

// Test the connection on startup
(async () => {
  try {
    const connection = await pool.connect();
    logger.info('Database pool connection successful: Connected to PostgreSQL database.');
    connection.release();
  } catch (error) {
    logger.error('Fatal: Database pool connection failed.', { error: error.message });
    await sendDiscordAlert(
      'Database Connection Failed',
      `Fatal: Express backend failed to connect to PostgreSQL database at ${process.env.DB_HOST || 'localhost'}. Error: ${error.message}`,
      'error'
    );
  }
})();

export default pool;

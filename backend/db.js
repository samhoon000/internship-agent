import mysql from 'mysql2/promise';
import dotenv from 'dotenv';

import logger from './logger.js';
import { sendDiscordAlert } from './alerting.js';

dotenv.config();

const pool = mysql.createPool({
  host: process.env.DB_HOST || 'localhost',
  user: process.env.DB_USER || 'root',
  password: process.env.DB_PASSWORD || '',
  database: process.env.DB_NAME || 'internship',
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
});

// Test the connection on startup
(async () => {
  try {
    const connection = await pool.getConnection();
    logger.info('Database pool connection successful: Connected to MySQL database.');
    connection.release();
  } catch (error) {
    logger.error('Fatal: Database pool connection failed.', { error: error.message });
    await sendDiscordAlert(
      'Database Connection Failed',
      `Fatal: Express backend failed to connect to MySQL database at ${process.env.DB_HOST || 'localhost'}. Error: ${error.message}`,
      'error'
    );
  }
})();

export default pool;

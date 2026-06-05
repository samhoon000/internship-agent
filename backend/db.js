import mysql from 'mysql2/promise';
import dotenv from 'dotenv';

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
    console.log('Database pool connection successful: Connected to MySQL database.');
    connection.release();
  } catch (error) {
    console.error('Fatal: Database pool connection failed. Error:', error.message);
  }
})();

export default pool;

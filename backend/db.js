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

// Test the connection on startup & run migrations
(async () => {
  try {
    const connection = await pool.getConnection();
    console.log('Database pool connection successful: Connected to MySQL database.');
    
    // Check if stipend_numeric column exists
    const [columns] = await connection.query('SHOW COLUMNS FROM internships LIKE "stipend_numeric"');
    if (columns.length === 0) {
      console.log('[Migration] Adding "stipend_numeric" column to "internships" table...');
      await connection.query('ALTER TABLE internships ADD COLUMN stipend_numeric INT DEFAULT 0');
      console.log('[Migration] Column "stipend_numeric" added successfully.');
      
      // Migrate existing data
      console.log('[Migration] Starting data migration for existing stipends...');
      const [rows] = await connection.query('SELECT apply_link, stipend FROM internships');
      
      const parseStipend = (stipendStr) => {
        if (!stipendStr) return 0;
        const clean = stipendStr.replace(/,/g, '').replace(/[₹$]/g, '');
        const matches = clean.match(/\d+/g);
        if (!matches) return 0;
        const nums = matches.map(Number);
        if (nums.length >= 2) {
          return (nums[0] + nums[1]) / 2;
        }
        return nums[0];
      };
      
      let updatedCount = 0;
      for (const row of rows) {
        const numericValue = Math.round(parseStipend(row.stipend));
        await connection.query('UPDATE internships SET stipend_numeric = ? WHERE apply_link = ?', [numericValue, row.apply_link]);
        updatedCount++;
      }
      console.log(`[Migration] Successfully migrated ${updatedCount} rows.`);
    } else {
      console.log('[Migration] "stipend_numeric" column is already present.');
    }

    connection.release();
  } catch (error) {
    console.error('Fatal: Database pool connection or migration failed. Error:', error.message);
  }
})();

export default pool;

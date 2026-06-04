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

    // Check if confidence column exists
    const [confidenceCols] = await connection.query('SHOW COLUMNS FROM internships LIKE "confidence"');
    if (confidenceCols.length === 0) {
      console.log('[Migration] Adding "confidence" column to "internships" table...');
      await connection.query('ALTER TABLE internships ADD COLUMN confidence VARCHAR(50) DEFAULT "HIGH" NOT NULL');
      console.log('[Migration] Column "confidence" added successfully.');
    } else {
      console.log('[Migration] "confidence" column is already present.');
    }

    // Check if confidence_score column exists
    const [confScoreCols] = await connection.query('SHOW COLUMNS FROM internships LIKE "confidence_score"');
    if (confScoreCols.length === 0) {
      console.log('[Migration] Adding "confidence_score" column to "internships" table...');
      await connection.query('ALTER TABLE internships ADD COLUMN confidence_score INT DEFAULT 0 NOT NULL');
      await connection.query('UPDATE internships SET confidence_score = legitimacy_score');
      console.log('[Migration] Column "confidence_score" added successfully.');
    } else {
      console.log('[Migration] "confidence_score" column is already present.');
    }

    // Check if confidence_tier column exists
    const [confTierCols] = await connection.query('SHOW COLUMNS FROM internships LIKE "confidence_tier"');
    if (confTierCols.length === 0) {
      console.log('[Migration] Adding "confidence_tier" column to "internships" table...');
      await connection.query('ALTER TABLE internships ADD COLUMN confidence_tier VARCHAR(50) DEFAULT "HIGH_CONFIDENCE" NOT NULL');
      await connection.query('UPDATE internships SET confidence_tier = confidence');
      console.log('[Migration] Column "confidence_tier" added successfully.');
    } else {
      console.log('[Migration] "confidence_tier" column is already present.');
    }

    // Check if description column exists
    const [descCols] = await connection.query('SHOW COLUMNS FROM internships LIKE "description"');
    if (descCols.length === 0) {
      console.log('[Migration] Adding "description" column to "internships" table...');
      await connection.query('ALTER TABLE internships ADD COLUMN description TEXT DEFAULT NULL');
      console.log('[Migration] Column "description" added successfully.');
    } else {
      console.log('[Migration] "description" column is already present.');
    }

    // Check if relevance_score column exists
    const [relevanceCols] = await connection.query('SHOW COLUMNS FROM internships LIKE "relevance_score"');
    if (relevanceCols.length === 0) {
      console.log('[Migration] Adding "relevance_score" column to "internships" table...');
      await connection.query('ALTER TABLE internships ADD COLUMN relevance_score INT DEFAULT 0 NOT NULL');
      console.log('[Migration] Column "relevance_score" added successfully.');
    } else {
      console.log('[Migration] "relevance_score" column is already present.');
    }

    // Align all legitimacy/confidence scores and tiers to the new 4-tier model
    console.log('[Migration] Aligning confidence scores and tiers to 4-tier model...');
    await connection.query('UPDATE internships SET confidence_score = legitimacy_score');
    await connection.query('UPDATE internships SET confidence = "HIGH_CONFIDENCE", confidence_tier = "HIGH_CONFIDENCE" WHERE legitimacy_score >= 80');
    await connection.query('UPDATE internships SET confidence = "MEDIUM_CONFIDENCE", confidence_tier = "MEDIUM_CONFIDENCE" WHERE legitimacy_score >= 60 AND legitimacy_score < 80');
    await connection.query('UPDATE internships SET confidence = "LOW_CONFIDENCE", confidence_tier = "LOW_CONFIDENCE" WHERE legitimacy_score >= 45 AND legitimacy_score < 60');
    const [deletedResult] = await connection.query('DELETE FROM internships WHERE legitimacy_score < 45');
    if (deletedResult && deletedResult.affectedRows > 0) {
      console.log(`[Migration] Purged ${deletedResult.affectedRows} rows with legitimacy score < 45.`);
    }
    console.log('[Migration] Confidence alignment complete.');

    // Run relevance migration check/purge on startup
    console.log('[Migration] Running relevance score calculation on existing listings...');
    const [rows] = await connection.query('SELECT apply_link, role, skills, description FROM internships');
    
    const calculateRelevanceScore = (role, skills, description) => {
      if (!role) return 0;
      const roleLower = role.toLowerCase();
      const skillsLower = (skills || '').toLowerCase();
      const descLower = (description || '').toLowerCase();
      
      const hardExcludes = [
        "sales", "marketing", "hr", "human resources", "seo", "telecalling",
        "telecaller", "customer support", "social media", "content writing"
      ];

      const overrideKeywords = [
        "mis analyst", "data analyst", "ai engineer", "ml engineer", "machine learning",
        "business intelligence", "data science", "data scientist", "data engineering",
        "data engineer", "artificial intelligence", "ai research", "quantitative research",
        "research analyst", "founding engineer", "founding ai engineer", "product engineer",
        "software engineer", "founding software engineer", "research engineer"
      ];
      
      let hasOverride = false;
      const titleNorm = roleLower.replace(/[-/_+:,()\[\]\s]+/g, ' ').trim();
      for (const kw of overrideKeywords) {
        if (kw.length <= 3) {
          const regex = new RegExp(`\\b${kw}\\b`, 'i');
          if (regex.test(roleLower) || regex.test(titleNorm)) {
            hasOverride = true;
            break;
          }
        } else {
          if (roleLower.includes(kw) || titleNorm.includes(kw)) {
            hasOverride = true;
            break;
          }
          if (kw.includes(' ')) {
            const regexPattern = kw.replace(/\s+/g, '.*');
            const regex = new RegExp(regexPattern, 'i');
            if (regex.test(roleLower) || regex.test(titleNorm)) {
              hasOverride = true;
              break;
            }
          }
        }
      }

      if (!hasOverride) {
        for (const kw of hardExcludes) {
          const regex = new RegExp(`\\b${kw.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')}\\b`, 'i');
          if (regex.test(roleLower)) {
            return 0;
          }
        }
      }
      
      let titleScore = 10;
      const analystKeywords = ["data analyst", "business analyst", "analytics", "bi analyst", "reporting analyst", "business intelligence", "mis analyst", "mis executive"];
      const scienceKeywords = ["data science", "data scientist", "machine learning", "ai", "predictive modeling"];
      const engineerKeywords = ["data engineer", "etl", "sql developer", "database"];
      const coreTools = ["data", "analyst", "python", "sql", "excel", "tableau", "power bi"];
      
      if (hasOverride) {
        titleScore = 60;
      } else if (analystKeywords.some(kw => kw.length <= 3 ? new RegExp(`\\b${kw}\\b`, 'i').test(roleLower) : roleLower.includes(kw))) {
        titleScore = 60;
      } else if (scienceKeywords.some(kw => kw.length <= 3 ? new RegExp(`\\b${kw}\\b`, 'i').test(roleLower) : roleLower.includes(kw))) {
        titleScore = 60;
      } else if (engineerKeywords.some(kw => kw.length <= 3 ? new RegExp(`\\b${kw}\\b`, 'i').test(roleLower) : roleLower.includes(kw))) {
        titleScore = 50;
      } else if (coreTools.some(kw => kw.length <= 3 ? new RegExp(`\\b${kw}\\b`, 'i').test(roleLower) : roleLower.includes(kw))) {
        titleScore = 40;
      }
      
      let skillsScore = 0;
      const coreSkills = ["python", "sql", "excel", "power bi", "tableau", "pandas", "numpy", "sklearn", "machine learning", "data science", "database", "bi", "analytics", "reporting"];
      const skillsList = skillsLower.split(',').map(s => s.trim()).filter(Boolean);
      const matchedSkills = new Set();
      for (const s of skillsList) {
        for (const cs of coreSkills) {
          if (s.includes(cs)) {
            matchedSkills.add(cs);
          }
        }
      }
      skillsScore = Math.min(30, matchedSkills.size * 10);
      
      let descScore = 0;
      if (descLower) {
        const matchedDesc = new Set();
        for (const kw of [...coreSkills, ...analystKeywords, ...scienceKeywords]) {
          if (descLower.includes(kw)) {
            matchedDesc.add(kw);
          }
        }
        descScore = Math.min(20, matchedDesc.size * 5);
      }
      
      return titleScore + skillsScore + descScore;
    };

    let updatedCount = 0;
    let deletedCount = 0;
    for (const row of rows) {
      const score = calculateRelevanceScore(row.role, row.skills, row.description);
      if (score < 40) {
        await connection.query('DELETE FROM internships WHERE apply_link = ?', [row.apply_link]);
        deletedCount++;
      } else {
        await connection.query('UPDATE internships SET relevance_score = ? WHERE apply_link = ?', [score, row.apply_link]);
        updatedCount++;
      }
    }
    console.log(`[Migration] Relevance updates done: populated ${updatedCount} rows, purged ${deletedCount} irrelevant rows.`);

    connection.release();
  } catch (error) {
    console.error('Fatal: Database pool connection or migration failed. Error:', error.message);
  }
})();

export default pool;

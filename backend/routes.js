import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import rateLimit from 'express-rate-limit';
import sanitizeHtml from 'sanitize-html';
import Redis from 'ioredis';
import { Queue } from 'bullmq';
import fs from 'fs';
import readline from 'readline';
import pool from './db.js';
import { checkLatestBackup } from '../scripts/verify_backup.js';
import logger from './logger.js';


const router = express.Router();
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(__dirname, '..');

// Redis & BullMQ Queue Configurations
const redisHost = process.env.REDIS_HOST || '127.0.0.1';
const redisPort = process.env.REDIS_PORT || 6379;

const redisConfig = {
  host: redisHost,
  port: redisPort,
  maxRetriesPerRequest: null, // Required by BullMQ
  enableOfflineQueue: false // Fail fast and degrade gracefully if Redis is down
};

const redisClient = new Redis(redisConfig);

redisClient.on('error', (err) => {
  logger.error('[Redis Client Error]', { error: err.message, stack: err.stack });
});

const scraperQueue = new Queue('scraper-queue', { connection: redisClient });
const cleanupQueue = new Queue('cleanup-queue', { connection: redisClient });
const livenessQueue = new Queue('liveness-queue', { connection: redisClient });

// API Rate Limiting Middleware
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // Limit each IP to 100 requests per window
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many requests from this IP, please try again after 15 minutes.' }
});

router.use(apiLimiter);

// Middleware: Verify Admin API Key
const verifyAdminKey = (req, res, next) => {
  const apiKey = req.headers['x-admin-api-key'] || req.query.apiKey;
  const expectedKey = process.env.ADMIN_API_KEY || 'super-secret-admin-key';
  if (!apiKey || apiKey !== expectedKey) {
    return res.status(401).json({ error: 'Unauthorized: Invalid or missing X-Admin-API-Key' });
  }
  next();
};

// Middleware: Verify Redis Connection Liveness
const checkRedisConnection = (req, res, next) => {
  if (redisClient.status !== 'ready') {
    return res.status(503).json({ error: 'Service Unavailable: Redis queue server is offline' });
  }
  next();
};

// Helper: Parse stipend string to numeric value (used for match score calc in JS)
function parseStipend(stipendStr) {
  if (!stipendStr) return 0;
  const clean = stipendStr.replace(/,/g, '').replace(/[₹$]/g, '');
  const matches = clean.match(/\d+/g);
  if (!matches) return 0;
  const nums = matches.map(Number);
  if (nums.length >= 2) {
    return (nums[0] + nums[1]) / 2;
  }
  return nums[0];
}

// Helper: Compute match score dynamically based on user filters
function getMatchScore(row, query = {}) {
  const { skills = '', location = '', remote = '', stipendMin = '0' } = query;
  
  const userSkills = skills ? skills.split(',').map(s => s.trim().toLowerCase()) : ['python', 'sql', 'excel', 'power bi', 'tableau'];
  const selectedLocations = location ? location.split(',').map(s => s.trim().toLowerCase()) : [];
  
  // 1. Skills overlap (40%)
  const jobSkills = (row.skills_list || []).map(s => s.toLowerCase());
  const overlap = userSkills.filter(s => jobSkills.some(js => js.includes(s) || s.includes(js)));
  const skillsOverlapScore = userSkills.length > 0 ? (overlap.length / userSkills.length) * 100 : 100;
  
  // 2. Role relevance (25%)
  const relevanceScore = row.relevance_score || 0;
  
  // 3. Experience alignment (15%)
  let experienceAlignment = 100;
  const textToSearch = `${row.role} ${row.description || ''}`.toLowerCase();
  if (/(2|3|4|5)\s*\+\s*years/i.test(textToSearch) || /prior experience of/i.test(textToSearch)) {
    experienceAlignment = 50;
  }
  
  // 4. Location preference (10%)
  let locationScore = 100;
  if (selectedLocations.length > 0) {
    const matchesLocation = selectedLocations.some(loc => {
      if (loc === 'remote') {
        return row.remote === 1 || (row.location && (row.location.toLowerCase().includes('remote') || row.location.toLowerCase().includes('work from home')));
      }
      return row.location && row.location.toLowerCase().includes(loc);
    });
    locationScore = matchesLocation ? 100 : 0;
  }
  
  // 5. Stipend preference (10%)
  let stipendScore = 100;
  if (stipendMin && stipendMin !== '0') {
    const minStipNum = parseInt(stipendMin, 10);
    const jobStipend = row.stipend_numeric || 0;
    if (jobStipend < minStipNum) {
      stipendScore = minStipNum > 0 ? Math.round((jobStipend / minStipNum) * 100) : 0;
    }
  }
  
  const matchScore = Math.round(
    (skillsOverlapScore * 0.40) +
    (relevanceScore * 0.25) +
    (experienceAlignment * 0.15) +
    (locationScore * 0.10) +
    (stipendScore * 0.10)
  );
  
  return Math.min(100, Math.max(0, matchScore));
}

// SQL Query Builder helper
function buildInternshipsQuery(query) {
  const {
    search = '',
    location = '',
    remote = '',
    duration = '',
    skills = '',
    stipendMin = '0',
    stipendMax = '',
    source = '',
    legitimacyMin = '45',
    datePosted = '',
    confidence = '',
    category = 'Data/AI'
  } = query;

  let sql = `FROM internships WHERE is_active = 1 AND relevance_score >= 40`;
  let params = [];

  if (category) {
    sql += ` AND role_category = ?`;
    params.push(category);
  }

  // Search filter
  if (search.trim()) {
    sql += ` AND MATCH(company_name, role, skills, description) AGAINST(? IN NATURAL LANGUAGE MODE)`;
    params.push(search.trim());
  }

  // Location filter
  if (location) {
    const selectedLocations = location.split(',').map(s => s.trim().toLowerCase());
    const locClauses = [];
    selectedLocations.forEach(loc => {
      if (loc === 'remote') {
        locClauses.push(`(remote = 1 OR location LIKE '%remote%' OR location LIKE '%work from home%')`);
      } else if (loc === 'hybrid') {
        locClauses.push(`location LIKE '%hybrid%'`);
      } else {
        locClauses.push(`location LIKE ?`);
        params.push(`%${loc}%`);
      }
    });
    if (locClauses.length > 0) {
      sql += ` AND (${locClauses.join(' OR ')})`;
    }
  }

  // Remote filter
  if (remote) {
    if (remote === 'remote') {
      sql += ` AND (remote = 1 OR location LIKE '%remote%' OR location LIKE '%work from home%')`;
    } else if (remote === 'onsite') {
      sql += ` AND (remote = 0 AND (location IS NULL OR (location NOT LIKE '%hybrid%' AND location NOT LIKE '%remote%' AND location NOT LIKE '%work from home%')))`;
    } else if (remote === 'hybrid') {
      sql += ` AND location LIKE '%hybrid%'`;
    }
  }

  // Duration filter
  if (duration) {
    const selectedDurations = duration.split(',').map(s => s.trim().toLowerCase());
    const durClauses = [];
    selectedDurations.forEach(d => {
      if (d === '6+') {
        durClauses.push(`duration REGEXP '[6-9]|[0-9]{2,}'`);
      } else {
        const num = parseInt(d, 10);
        if (!isNaN(num)) {
          durClauses.push(`duration LIKE ?`);
          params.push(`%${num}%`);
        }
      }
    });
    if (durClauses.length > 0) {
      sql += ` AND (${durClauses.join(' OR ')})`;
    }
  }

  // Skills filter (matches ALL selected skills exactly)
  if (skills) {
    const selectedSkills = skills.split(',').map(s => s.trim().toLowerCase());
    selectedSkills.forEach(skill => {
      // Remove spaces for exact token comparison in comma-separated list
      const cleanSkill = skill.replace(/\s+/g, '');
      sql += ` AND FIND_IN_SET(?, REPLACE(LOWER(skills), ' ', '')) > 0`;
      params.push(cleanSkill);
    });
  }

  // Sources filter
  if (source) {
    const selectedSources = source.split(',').map(s => s.trim());
    if (selectedSources.length > 0) {
      const placeholders = selectedSources.map(() => '?').join(', ');
      sql += ` AND source IN (${placeholders})`;
      params.push(...selectedSources);
    }
  }

  // Min stipend filter
  const minStip = parseInt(stipendMin, 10) || 0;
  if (minStip > 0) {
    sql += ` AND stipend_numeric >= ?`;
    params.push(minStip);
  }

  // Max stipend filter
  if (stipendMax) {
    const maxStip = parseInt(stipendMax, 10);
    if (!isNaN(maxStip)) {
      sql += ` AND stipend_numeric <= ?`;
      params.push(maxStip);
    }
  }

  // Min legitimacy filter
  const minLegit = parseInt(legitimacyMin, 10) || 45;
  sql += ` AND legitimacy_score >= ?`;
  params.push(minLegit);

  // Date Posted filter
  if (datePosted) {
    let days = 0;
    if (datePosted === 'today') days = 1;
    else if (datePosted === '3days') days = 3;
    else if (datePosted === '7days') days = 7;
    else if (datePosted === '30days') days = 30;

    if (days > 0) {
      sql += ` AND (posted_at >= NOW() - INTERVAL ? DAY OR (posted_at IS NULL AND created_at >= NOW() - INTERVAL ? DAY))`;
      params.push(days, days);
    }
  }

  // Confidence filter
  if (confidence) {
    const selectedConfidences = confidence.split(',').map(s => s.trim());
    if (selectedConfidences.length > 0) {
      const placeholders = selectedConfidences.map(() => '?').join(', ');
      sql += ` AND confidence IN (${placeholders})`;
      params.push(...selectedConfidences);
    }
  }

  return { sql, params };
}

// 1. GET /api/internships - Search, Filter, Sort, Paginate
router.get('/internships', async (req, res) => {
  try {
    const {
      page = '1',
      limit = '10',
      sort = 'newest'
    } = req.query;

    // Parameter validation and sanitization
    const pageNum = Math.max(1, parseInt(page, 10) || 1);
    const limitNum = Math.min(100, Math.max(1, parseInt(limit, 10) || 10));
    const offset = (pageNum - 1) * limitNum;

    if (req.query.search) {
      req.query.search = req.query.search.trim().replace(/[^\w\s\-\,\.\+\#]/gi, '');
    }
    if (req.query.location) {
      req.query.location = req.query.location.trim().replace(/[^\w\s\-\,]/gi, '');
    }
    if (req.query.skills) {
      req.query.skills = req.query.skills.trim().replace(/[^\w\s\-\,\+\#]/gi, '');
    }

    const { sql: whereSql, params: whereParams } = buildInternshipsQuery(req.query);

    const baseColumns = [
      'apply_link', 'company_name', 'role', 'stipend', 'stipend_numeric', 'paid',
      'location', 'remote', 'duration', 'skills', 'source', 'legitimacy_score',
      'confidence_score', 'freshness_score', 'confidence', 'confidence_tier',
      'relevance_score', 'posted_at', 'created_at'
    ];

    let selectColumns = [...baseColumns];
    let selectParams = [];
    const hasSearch = req.query.search && req.query.search.trim();

    if (hasSearch) {
      selectColumns.push(`MATCH(company_name, role, skills, description) AGAINST(? IN NATURAL LANGUAGE MODE) AS search_score`);
      selectParams.push(req.query.search.trim());
    }

    const columnsStr = selectColumns.join(', ');

    if (sort === 'legitimacy') {
      const querySql = `SELECT ${columnsStr} ${whereSql}`;
      const [rows] = await pool.query(querySql, [...selectParams, ...whereParams]);

      const processed = rows.map(row => {
        const skills_list = row.skills ? row.skills.split(',').map(s => s.trim()).filter(Boolean) : [];
        const match_score = getMatchScore({ ...row, skills_list }, req.query);
        return { ...row, skills_list, match_score };
      });

      processed.sort((a, b) => b.match_score - a.match_score || new Date(b.posted_at || b.created_at) - new Date(a.posted_at || a.created_at));

      const total = processed.length;
      const paginated = processed.slice(offset, offset + limitNum);

      return res.json({
        internships: paginated,
        total,
        page: pageNum,
        limit: limitNum,
        totalPages: Math.ceil(total / limitNum)
      });
    } else {
      const countSql = `SELECT COUNT(*) as total ${whereSql}`;
      const [[{ total }]] = await pool.query(countSql, whereParams);

      let orderClause = '';
      if (sort === 'stipend') {
        orderClause = ` ORDER BY stipend_numeric DESC, COALESCE(posted_at, created_at) DESC`;
      } else if (sort === 'remote_first') {
        orderClause = ` ORDER BY (CASE WHEN remote = 1 OR location LIKE '%remote%' OR location LIKE '%work from home%' THEN 1 ELSE 0 END) DESC, COALESCE(posted_at, created_at) DESC`;
      } else if (sort === 'company') {
        orderClause = ` ORDER BY company_name ASC`;
      } else if (sort === 'recently_added') {
        orderClause = ` ORDER BY created_at DESC`;
      } else {
        if (hasSearch) {
          orderClause = ` ORDER BY search_score DESC, COALESCE(posted_at, created_at) DESC`;
        } else {
          orderClause = ` ORDER BY COALESCE(posted_at, created_at) DESC`;
        }
      }

      const querySql = `SELECT ${columnsStr} ${whereSql}${orderClause} LIMIT ? OFFSET ?`;
      const queryParams = [...selectParams, ...whereParams, limitNum, offset];

      const [rows] = await pool.query(querySql, queryParams);

      const paginated = rows.map(row => {
        const skills_list = row.skills ? row.skills.split(',').map(s => s.trim()).filter(Boolean) : [];
        const match_score = getMatchScore({ ...row, skills_list }, req.query);
        return { ...row, skills_list, match_score };
      });

      return res.json({
        internships: paginated,
        total,
        page: pageNum,
        limit: limitNum,
        totalPages: Math.ceil(total / limitNum)
      });
    }
  } catch (error) {
    logger.error('Error fetching internships:', { error: error.message, stack: error.stack });
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// 2. GET /api/internships/:applyLink - Specific internship details (with XSS sanitization)
router.get('/internships/:applyLink', async (req, res) => {
  try {
    const rawLink = req.params.applyLink;
    let decodedLink = decodeURIComponent(rawLink);
    
    try {
      const buffer = Buffer.from(rawLink, 'base64');
      const base64Decoded = buffer.toString('utf-8');
      if (base64Decoded.startsWith('http://') || base64Decoded.startsWith('https://')) {
        decodedLink = base64Decoded;
      }
    } catch (e) {
      // Ignored
    }

    const [rows] = await pool.query('SELECT * FROM internships WHERE apply_link = ? AND is_active = 1', [decodedLink]);
    
    if (rows.length === 0) {
      return res.status(404).json({ error: 'Internship not found' });
    }

    const row = rows[0];
    const skills_list = row.skills ? row.skills.split(',').map(s => s.trim()).filter(Boolean) : [];
    
    // XSS Sanitization
    if (row.description) {
      row.description = sanitizeHtml(row.description, {
        allowedTags: [
          'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'p', 'a', 'ul', 'ol',
          'nl', 'li', 'b', 'i', 'strong', 'em', 'strike', 'code', 'hr', 'br', 'div',
          'table', 'thead', 'caption', 'tbody', 'tr', 'th', 'td', 'pre', 'span'
        ],
        allowedAttributes: {
          a: [ 'href', 'name', 'target' ],
          img: [ 'src', 'alt' ],
          span: [ 'style' ],
          div: [ 'style' ]
        }
      });
    }

    const itemWithScore = {
      ...row,
      skills_list,
      match_score: getMatchScore({ ...row, skills_list }, req.query)
    };

    // Find similar internships
    const firstRoleWord = row.role.split(' ')[0] + '%';
    const skillsMatchPatterns = skills_list.map(s => `%${s}%`);

    let similarSql = `
      SELECT apply_link, company_name, role, stipend, stipend_numeric, paid,
             location, remote, duration, skills, source, legitimacy_score,
             confidence_score, freshness_score, confidence, confidence_tier,
             relevance_score, posted_at, created_at
      FROM internships
      WHERE is_active = 1 AND apply_link != ? AND relevance_score >= 40
        AND role_category = ?
        AND (role LIKE ? OR source = ?
    `;
    const similarParams = [decodedLink, row.role_category || 'Data/AI', firstRoleWord, row.source];

    if (skillsMatchPatterns.length > 0) {
      const skillsClauses = skillsMatchPatterns.map(() => 'skills LIKE ?').join(' OR ');
      similarSql += ` OR ${skillsClauses}`;
      similarParams.push(...skillsMatchPatterns);
    }
    similarSql += `) LIMIT 3`;

    const [similarRows] = await pool.query(similarSql, similarParams);
    
    const similar = similarRows.map(sRow => {
      const sSkillsList = sRow.skills ? sRow.skills.split(',').map(s => s.trim()).filter(Boolean) : [];
      return {
        ...sRow,
        skills_list: sSkillsList,
        match_score: getMatchScore({ ...sRow, skills_list: sSkillsList }, req.query)
      };
    });

    res.json({
      internship: itemWithScore,
      similar
    });
  } catch (error) {
    logger.error('Error fetching internship details:', { error: error.message, stack: error.stack });
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// 3. GET /api/filters - Unique values for filters (excludes description, active only)
router.get('/filters', async (req, res) => {
  try {
    const { category = 'Data/AI' } = req.query;
    const cacheKey = `filters:${category}`;

    try {
      const cachedData = await redisClient.get(cacheKey);
      if (cachedData) {
        return res.json(JSON.parse(cachedData));
      }
    } catch (cacheErr) {
      logger.error('[Redis Cache Read Error - filters]', { error: cacheErr.message });
    }

    const [rows] = await pool.query(
      'SELECT location, source, skills FROM internships WHERE is_active = 1 AND relevance_score >= 40 AND role_category = ?',
      [category]
    );
    
    const locationsSet = new Set();
    const sourcesSet = new Set();
    const skillsMap = {};
    
    rows.forEach(item => {
      if (item.location) {
        const locs = item.location.split(',').map(l => l.trim());
        locs.forEach(l => {
          if (l && l.toLowerCase() !== 'remote' && l.toLowerCase() !== 'work from home') {
            locationsSet.add(l);
          }
        });
      }
      
      if (item.source) {
        sourcesSet.add(item.source);
      }
      
      if (item.skills) {
        const skills_list = item.skills.split(',').map(s => s.trim()).filter(Boolean);
        skills_list.forEach(skill => {
          const sNormalized = skill.toLowerCase();
          skillsMap[sNormalized] = (skillsMap[sNormalized] || 0) + 1;
        });
      }
    });

    const popularSkills = Object.entries(skillsMap)
      .map(([name, count]) => {
        let displayName = name;
        if (name === 'sql') displayName = 'SQL';
        else if (name === 'python') displayName = 'Python';
        else if (name === 'power bi') displayName = 'Power BI';
        else if (name === 'tableau') displayName = 'Tableau';
        else if (name === 'excel') displayName = 'Excel';
        else displayName = name.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
        
        return { name: displayName, count };
      })
      .sort((a, b) => b.count - a.count);

    const resultData = {
      locations: Array.from(locationsSet).sort(),
      sources: Array.from(sourcesSet).sort(),
      skills: popularSkills
    };

    try {
      await redisClient.setex(cacheKey, 600, JSON.stringify(resultData));
    } catch (cacheErr) {
      logger.error('[Redis Cache Write Error - filters]', { error: cacheErr.message });
    }

    res.json(resultData);
  } catch (error) {
    logger.error('Error fetching filter values:', { error: error.message, stack: error.stack });
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// 4. GET /api/stats - Analytics (excludes description, active only)
router.get('/stats', async (req, res) => {
  try {
    const cacheKey = 'stats';
    try {
      const cachedData = await redisClient.get(cacheKey);
      if (cachedData) {
        return res.json(JSON.parse(cachedData));
      }
    } catch (cacheErr) {
      logger.error('[Redis Cache Read Error - stats]', { error: cacheErr.message });
    }

    const [rows] = await pool.query(
      'SELECT company_name, role, role_category, stipend, stipend_numeric, remote, location, source, skills, legitimacy_score, posted_at, created_at FROM internships WHERE is_active = 1'
    );
    
    const totalCount = rows.length;
    const highlyLegit = rows.filter(i => i.legitimacy_score >= 80).length;
    const avgLegitimacy = totalCount > 0 
      ? rows.reduce((sum, i) => sum + i.legitimacy_score, 0) / totalCount 
      : 0;
    
    const [[{ dbTotalCount }]] = await pool.query('SELECT COUNT(*) as dbTotalCount FROM internships');
    
    // Query rejection stats from database
    const [[rejectionRow]] = await pool.query(
      `SELECT 
         COUNT(*) as totalRejected,
         SUM(CASE WHEN reasons LIKE '%relevance%' OR reasons LIKE '%role%' OR reasons LIKE '%exclude%' THEN 1 ELSE 0 END) as rejectedNonTech 
       FROM internship_rejections`
    );
    const totalRejected = rejectionRow ? (rejectionRow.totalRejected || 0) : 0;
    const rejectedNonTech = rejectionRow ? (Number(rejectionRow.rejectedNonTech) || 0) : 0;

    const aiDataCount = rows.filter(i => i.role_category === 'Data/AI').length;
    const softwareCount = rows.filter(i => i.role_category === 'Software').length;

    const skillsCount = {};
    rows.forEach(i => {
      if (i.skills) {
        const skills_list = i.skills.split(',').map(s => s.trim()).filter(Boolean);
        skills_list.forEach(s => {
          const sNorm = s.toLowerCase();
          let sDisplay = s;
          if (sNorm === 'sql') sDisplay = 'SQL';
          else if (sNorm === 'python') sDisplay = 'Python';
          else if (sNorm === 'power bi') sDisplay = 'Power BI';
          else if (sNorm === 'tableau') sDisplay = 'Tableau';
          else if (sNorm === 'excel') sDisplay = 'Excel';
          else sDisplay = s.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
          
          skillsCount[sDisplay] = (skillsCount[sDisplay] || 0) + 1;
        });
      }
    });
    const skillsDemand = Object.entries(skillsCount)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 10);

    const paidListings = rows
      .filter(i => i.stipend_numeric > 0)
      .sort((a, b) => b.stipend_numeric - a.stipend_numeric)
      .slice(0, 8)
      .map(i => ({
        company: i.company_name,
        role: i.role.length > 25 ? i.role.slice(0, 22) + '...' : i.role,
        stipend: i.stipend_numeric,
        stipendText: i.stipend
      }));

    let remoteCount = 0;
    let onsiteCount = 0;
    rows.forEach(i => {
      if (i.remote === 1 || i.remote === true || (i.location && (i.location.toLowerCase().includes('remote') || i.location.toLowerCase().includes('work from home')))) {
        remoteCount++;
      } else {
        onsiteCount++;
      }
    });
    const remoteDistribution = [
      { name: 'Remote', value: remoteCount },
      { name: 'On-site', value: onsiteCount }
    ];

    const sourceCount = {};
    rows.forEach(i => {
      if (i.source) {
        sourceCount[i.source] = (sourceCount[i.source] || 0) + 1;
      }
    });
    const sourceDistribution = Object.entries(sourceCount).map(([name, value]) => ({ name, value }));

    const companyCount = {};
    rows.forEach(i => {
      if (i.company_name) {
        companyCount[i.company_name] = (companyCount[i.company_name] || 0) + 1;
      }
    });
    const topHiringCompanies = Object.entries(companyCount)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);

    const locationCount = {};
    rows.forEach(i => {
      if (i.location) {
        const locClean = i.location.split(',')[0].trim();
        if (locClean && locClean.toLowerCase() !== 'remote' && locClean.toLowerCase() !== 'work from home') {
          locationCount[locClean] = (locationCount[locClean] || 0) + 1;
        }
      }
    });
    const locationDistribution = Object.entries(locationCount)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);

    const stipendByRole = {};
    rows.forEach(i => {
      if (i.stipend_numeric > 0) {
        let roleCat = 'Other';
        const roleLower = (i.role || '').toLowerCase();
        if (roleLower.includes('data scientist') || roleLower.includes('data science')) roleCat = 'Data Science';
        else if (roleLower.includes('data analyst') || roleLower.includes('data analytics')) roleCat = 'Data Analyst';
        else if (roleLower.includes('business analyst') || roleLower.includes('business intelligence') || roleLower.includes('bi ')) roleCat = 'Business Analyst';
        else if (roleLower.includes('analytics') || roleLower.includes('reporting')) roleCat = 'Analytics';
        
        if (!stipendByRole[roleCat]) {
          stipendByRole[roleCat] = { sum: 0, count: 0 };
        }
        stipendByRole[roleCat].sum += i.stipend_numeric;
        stipendByRole[roleCat].count += 1;
      }
    });
    const avgStipendTrend = Object.entries(stipendByRole).map(([name, data]) => ({
      name,
      avgStipend: Math.round(data.sum / data.count)
    })).sort((a, b) => b.avgStipend - a.avgStipend);

    const resultData = {
      metrics: {
        totalScraped: dbTotalCount + totalRejected,
        highlyLegit,
        avgLegitimacy: parseFloat(avgLegitimacy.toFixed(1)),
        aiDataCount,
        softwareCount,
        rejectedNonTech
      },
      charts: {
        skillsDemand,
        topPaying: paidListings,
        remoteDistribution,
        sourceDistribution,
        topCompanies: topHiringCompanies,
        locationDistribution,
        avgStipendTrend
      }
    };

    try {
      await redisClient.setex(cacheKey, 600, JSON.stringify(resultData));
    } catch (cacheErr) {
      logger.error('[Redis Cache Write Error - stats]', { error: cacheErr.message });
    }

    res.json(resultData);
  } catch (error) {
    logger.error('Error fetching statistics:', { error: error.message, stack: error.stack });
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// 5. POST /api/scrapers/run - Queue Playwright scraping in BullMQ
router.post('/scrapers/run', verifyAdminKey, checkRedisConnection, async (req, res) => {
  try {
    const activeJobs = await scraperQueue.getActive();
    const waitingJobs = await scraperQueue.getWaiting();
    
    if (activeJobs.length > 0 || waitingJobs.length > 0) {
      const currentJob = activeJobs[0] || waitingJobs[0];
      const logsObj = await scraperQueue.getJobLogs(currentJob.id, 0, 1000);
      return res.status(400).json({
        status: 'running',
        message: 'A scraper job is already running or waiting.',
        jobId: currentJob.id,
        logs: logsObj ? logsObj.logs : []
      });
    }

    const job = await scraperQueue.add('run-scraper', {}, {
      attempts: 1,
      removeOnComplete: false,
      removeOnFail: false
    });
    
    await redisClient.set('scraper:last_job_id', job.id);
    
    res.json({
      status: 'running',
      message: 'Scraper run queued successfully.',
      jobId: job.id,
      logs: [`[${new Date().toISOString()}] Scraper run queued (Job ID: ${job.id}).\n`]
    });
  } catch (error) {
    logger.error('Error queueing scraper:', { error: error.message, stack: error.stack });
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// 6. GET /api/scrapers/status - Check status of scraper run (with BullMQ)
router.get('/scrapers/status', checkRedisConnection, async (req, res) => {
  try {
    const jobId = req.query.jobId || (await redisClient.get('scraper:last_job_id'));
    if (!jobId) {
      return res.json({ status: 'idle', logs: ['No scraper runs recorded yet.'] });
    }
    
    const job = await scraperQueue.getJob(jobId);
    if (!job) {
      return res.json({ status: 'idle', logs: ['Scraper job not found.'] });
    }
    
    const state = await job.getState();
    const logsObj = await scraperQueue.getJobLogs(jobId, 0, 1000);
    const logs = logsObj ? logsObj.logs : [];
    
    let status = 'idle';
    if (state === 'active' || state === 'waiting' || state === 'delayed') {
      status = 'running';
    } else if (state === 'completed') {
      status = 'completed';
    } else if (state === 'failed') {
      status = 'failed';
    }
    
    res.json({
      status,
      logs,
      jobId
    });
  } catch (error) {
    logger.error('Error fetching scraper status:', { error: error.message, stack: error.stack });
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// Additional Queue routes for manual/worker cleanups and liveness runs
router.post('/scrapers/cleanup', verifyAdminKey, checkRedisConnection, async (req, res) => {
  try {
    const job = await cleanupQueue.add('run-cleanup', {});
    res.json({ message: 'Cleanup job queued.', jobId: job.id });
  } catch (error) {
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

router.post('/scrapers/liveness', verifyAdminKey, checkRedisConnection, async (req, res) => {
  try {
    const job = await livenessQueue.add('run-liveness', {});
    res.json({ message: 'Liveness check job queued.', jobId: job.id });
  } catch (error) {
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// Health Checks
router.get('/live', (req, res) => {
  res.json({ status: 'UP', service: 'liveness', timestamp: new Date().toISOString() });
});

router.get('/ready', async (req, res) => {
  try {
    const connection = await pool.getConnection();
    connection.release();
    res.json({ status: 'UP', service: 'readiness', timestamp: new Date().toISOString() });
  } catch (error) {
    res.status(503).json({ status: 'DOWN', error: error.message });
  }
});

router.get('/health', async (req, res) => {
  const healthData = {
    status: 'HEALTHY',
    timestamp: new Date().toISOString(),
    uptimeSeconds: Math.round(process.uptime()),
    services: {
      db: { status: 'UNKNOWN', latencyMs: 0 },
      redis: { status: 'UNKNOWN' },
      scrapers: [],
      backup: {}
    },
    alerts: []
  };

  // 1. Check MySQL Database Latency & Connection
  const dbStart = Date.now();
  try {
    const connection = await pool.getConnection();
    await connection.query('SELECT 1');
    connection.release();
    healthData.services.db.status = 'UP';
    healthData.services.db.latencyMs = Date.now() - dbStart;
  } catch (dbErr) {
    healthData.status = 'UNHEALTHY';
    healthData.services.db.status = 'DOWN';
    healthData.services.db.error = dbErr.message;
    healthData.alerts.push({ level: 'CRITICAL', service: 'MySQL', message: `Database connection failed: ${dbErr.message}` });
  }

  // 2. Check Redis Status (fail fast, no hang)
  try {
    healthData.services.redis.status = redisClient.status;
    if (redisClient.status !== 'ready') {
      healthData.status = 'UNHEALTHY';
      healthData.alerts.push({ level: 'HIGH', service: 'Redis', message: `Redis connection status is ${redisClient.status}` });
    }
  } catch (redisErr) {
    healthData.status = 'UNHEALTHY';
    healthData.services.redis.status = 'DOWN';
    healthData.alerts.push({ level: 'HIGH', service: 'Redis', message: `Redis query failed: ${redisErr.message}` });
  }

  // 3. Check Scraper Source Health (from database source_health table)
  if (healthData.services.db.status === 'UP') {
    try {
      const [rows] = await pool.query('SELECT * FROM source_health');
      healthData.services.scrapers = rows.map(r => ({
        source: r.source,
        lastSuccessfulScrape: r.last_successful_scrape,
        lastFailure: r.last_failure,
        healthStatus: r.health_status
      }));

      // Generate alerts for unhealthy scrapers
      rows.forEach(r => {
        if (r.health_status === 'UNHEALTHY') {
          healthData.alerts.push({
            level: 'MEDIUM',
            service: `Scraper:${r.source}`,
            message: `Scraper ${r.source} failed in its last run (Failure time: ${r.last_failure})`
          });
        }
      });
    } catch (scraperErr) {
      logger.error('[Health Check Scraper Error]', { error: scraperErr.message });
    }
  }

  // 4. Check Backup Health
  try {
    const backupHealth = checkLatestBackup();
    healthData.services.backup = backupHealth;
    if (backupHealth.status !== 'HEALTHY') {
      healthData.alerts.push({
        level: 'WARNING',
        service: 'Backup',
        message: `Backup health check failed: ${backupHealth.reason}`
      });
    }
  } catch (backupErr) {
    healthData.services.backup = { status: 'UNHEALTHY', error: backupErr.message };
  }

  // Set appropriate status code (503 if any CRITICAL alerts exist)
  const hasCritical = healthData.alerts.some(a => a.level === 'CRITICAL');
  if (hasCritical) {
    res.status(503).json(healthData);
  } else {
    res.json(healthData);
  }
});

export default router;

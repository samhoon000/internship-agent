import express from 'express';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import pool from './db.js';

const router = express.Router();
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(__dirname, '..');

// Helper: Parse stipend string to numeric value
function parseStipend(stipendStr) {
  if (!stipendStr) return 0;
  
  // Clean string: remove commas and rupee/dollar symbols
  const clean = stipendStr.replace(/,/g, '').replace(/[₹$]/g, '');
  
  // Find all sequences of numbers
  const matches = clean.match(/\d+/g);
  if (!matches) return 0;
  
  // If it's a range like "5000-10000", take the average
  const nums = matches.map(Number);
  if (nums.length >= 2) {
    return (nums[0] + nums[1]) / 2;
  }
  return nums[0];
}

// Cache structure for internships to speed up operations and allow complex filtering/sorting
let dbCache = {
  data: [],
  lastUpdated: null
};

// Middleware/Helper to refresh cache if empty or older than 30 seconds
async function getCachedInternships() {
  const now = Date.now();
  if (dbCache.data.length === 0 || !dbCache.lastUpdated || (now - dbCache.lastUpdated > 30000)) {
    try {
      const [rows] = await pool.query('SELECT * FROM internships ORDER BY COALESCE(posted_at, created_at) DESC');
      
      // Process rows to include parsed numeric stipends and clean skills array
      dbCache.data = rows.map(row => {
        const skillsArray = row.skills 
          ? row.skills.split(',').map(s => s.trim()).filter(s => s.length > 0)
          : [];
        return {
          ...row,
          skills_list: skillsArray,
          stipend_numeric: parseStipend(row.stipend)
        };
      });
      dbCache.lastUpdated = now;
      console.log(`[Cache] Reloaded ${dbCache.data.length} internships from database.`);
    } catch (error) {
      console.error('Error fetching internships for cache:', error);
      // Fallback to existing cache if DB fails
    }
  }
  return dbCache.data;
}// 1. GET /api/internships - Search, Filter, Sort, Paginate
router.get('/internships', async (req, res) => {
  try {
    // Extract query parameters (supporting full filter range)
    const {
      search = '',
      location = '',
      remote = '',
      duration = '',
      skills = '',
      stipendMin = '0',
      stipendMax = '',
      source = '',
      legitimacyMin = '60',
      sort = 'newest',
      datePosted = '',
      confidence = '',
      page = '1',
      limit = '10'
    } = req.query;

    const pageNum = parseInt(page, 10) || 1;
    const limitNum = parseInt(limit, 10) || 10;
    const offset = (pageNum - 1) * limitNum;

    let queryParts = [];
    let queryParams = [];

    // Search filter (company, role, skills, location)
    if (search.trim()) {
      const q = `%${search.trim()}%`;
      queryParts.push('(company_name LIKE ? OR role LIKE ? OR skills LIKE ? OR location LIKE ?)');
      queryParams.push(q, q, q, q);
    }

    // Location filter (matches any of the selected locations)
    if (location) {
      const selectedLocations = location.split(',').map(s => s.trim().toLowerCase());
      const locConditions = [];
      selectedLocations.forEach(loc => {
        if (loc === 'remote') {
          locConditions.push('(remote = 1 OR location LIKE "%remote%" OR location LIKE "%work from home%")');
        } else if (loc === 'hybrid') {
          locConditions.push('(location LIKE "%hybrid%")');
        } else {
          locConditions.push('(location LIKE ?)');
          queryParams.push(`%${loc}%`);
        }
      });
      if (locConditions.length > 0) {
        queryParts.push(`(${locConditions.join(' OR ')})`);
      }
    }

    // Remote filter
    if (remote) {
      if (remote === 'remote') {
        queryParts.push('(remote = 1 OR location LIKE "%remote%" OR location LIKE "%work from home%")');
      } else if (remote === 'onsite') {
        queryParts.push('(remote = 0 AND (location NOT LIKE "%hybrid%" OR location IS NULL))');
      } else if (remote === 'hybrid') {
        queryParts.push('(location LIKE "%hybrid%")');
      }
    }

    // Duration filter (matches any of the selected durations)
    if (duration) {
      const selectedDurations = duration.split(',').map(s => s.trim().toLowerCase());
      const durConditions = [];
      selectedDurations.forEach(d => {
        if (d === '6+') {
          durConditions.push("(duration REGEXP '[6-9]|[0-9]{2,}')");
        } else {
          const num = parseInt(d, 10);
          if (!isNaN(num)) {
            durConditions.push(`(duration LIKE ?)`);
            queryParams.push(`%${num}%`);
          }
        }
      });
      if (durConditions.length > 0) {
        queryParts.push(`(${durConditions.join(' OR ')})`);
      }
    }

    // Skills filter (matches ALL selected skills)
    if (skills) {
      const selectedSkills = skills.split(',').map(s => s.trim().toLowerCase());
      selectedSkills.forEach(skill => {
        queryParts.push('skills LIKE ?');
        queryParams.push(`%${skill}%`);
      });
    }

    // Sources filter (matches any of the selected sources)
    if (source) {
      const selectedSources = source.split(',').map(s => s.trim().toLowerCase());
      const srcConditions = [];
      selectedSources.forEach(src => {
        srcConditions.push('LOWER(source) = ?');
        queryParams.push(src);
      });
      if (srcConditions.length > 0) {
        queryParts.push(`(${srcConditions.join(' OR ')})`);
      }
    }

    // Min stipend filter
    const minStip = parseInt(stipendMin, 10) || 0;
    if (minStip > 0) {
      queryParts.push('stipend_numeric >= ?');
      queryParams.push(minStip);
    }

    // Max stipend filter
    if (stipendMax) {
      const maxStip = parseInt(stipendMax, 10);
      if (!isNaN(maxStip)) {
        queryParts.push('stipend_numeric <= ?');
        queryParams.push(maxStip);
      }
    }

    // Min legitimacy filter
    const minLegit = parseInt(legitimacyMin, 10) || 60;
    queryParts.push('legitimacy_score >= ?');
    queryParams.push(minLegit);

    // Date Posted filter
    if (datePosted) {
      if (datePosted === 'today') {
        queryParts.push('COALESCE(posted_at, created_at) >= NOW() - INTERVAL 1 DAY');
      } else if (datePosted === '3days') {
        queryParts.push('COALESCE(posted_at, created_at) >= NOW() - INTERVAL 3 DAY');
      } else if (datePosted === '7days') {
        queryParts.push('COALESCE(posted_at, created_at) >= NOW() - INTERVAL 7 DAY');
      } else if (datePosted === '30days') {
        queryParts.push('COALESCE(posted_at, created_at) >= NOW() - INTERVAL 30 DAY');
      }
    }

    // Confidence filter (matches any of the selected confidences, e.g. HIGH,MEDIUM)
    if (confidence) {
      const selectedConfidences = confidence.split(',').map(s => s.trim().toUpperCase());
      const confConditions = [];
      selectedConfidences.forEach(c => {
        confConditions.push('confidence = ?');
        queryParams.push(c);
      });
      if (confConditions.length > 0) {
        queryParts.push(`(${confConditions.join(' OR ')})`);
      }
    }

    // Construct SQL queries
    let whereClause = '';
    if (queryParts.length > 0) {
      whereClause = 'WHERE ' + queryParts.join(' AND ');
    }

    // Sort mapping
    let orderClause = 'ORDER BY COALESCE(posted_at, created_at) DESC';
    if (sort === 'stipend') {
      orderClause = 'ORDER BY stipend_numeric DESC, COALESCE(posted_at, created_at) DESC';
    } else if (sort === 'legitimacy') {
      orderClause = 'ORDER BY legitimacy_score DESC, COALESCE(posted_at, created_at) DESC';
    } else if (sort === 'recently_added') {
      orderClause = 'ORDER BY created_at DESC';
    }

    // Get Total Count Query
    const countSql = `SELECT COUNT(*) as total FROM internships ${whereClause}`;
    const [countRows] = await pool.query(countSql, queryParams);
    const total = countRows[0].total;

    // Get Paginated Data Query
    const dataSql = `SELECT * FROM internships ${whereClause} ${orderClause} LIMIT ? OFFSET ?`;
    const dataParams = [...queryParams, limitNum, offset];
    const [rows] = await pool.query(dataSql, dataParams);

    // Format rows
    const formattedInternships = rows.map(row => {
      const skillsArray = row.skills 
        ? row.skills.split(',').map(s => s.trim()).filter(s => s.length > 0)
        : [];
      return {
        ...row,
        skills_list: skillsArray
      };
    });

    res.json({
      internships: formattedInternships,
      total,
      page: pageNum,
      limit: limitNum,
      totalPages: Math.ceil(total / limitNum)
    });
  } catch (error) {
    console.error('Error fetching internships:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// 2. GET /api/internships/:applyLink - Specific internship details
// Expected path parameter is URL-safe base64 or URI encoded apply_link
router.get('/internships/:applyLink', async (req, res) => {
  try {
    const rawLink = req.params.applyLink;
    let decodedLink = decodeURIComponent(rawLink);
    
    // Try to decode as Base64 if it looks like it, otherwise use URI decoded
    try {
      const buffer = Buffer.from(rawLink, 'base64');
      const base64Decoded = buffer.toString('utf-8');
      if (base64Decoded.startsWith('http://') || base64Decoded.startsWith('https://')) {
        decodedLink = base64Decoded;
      }
    } catch (e) {
      // Not base64, continue with URI decoded
    }

    const internships = await getCachedInternships();
    const item = internships.find(i => i.apply_link === decodedLink);

    if (!item) {
      return res.status(404).json({ error: 'Internship not found' });
    }

    // Find suggested similar internships
    const similar = internships
      .filter(i => i.apply_link !== decodedLink && (
        (i.role && item.role && i.role.toLowerCase().split(' ')[0] === item.role.toLowerCase().split(' ')[0]) ||
        (i.source === item.source) ||
        (i.skills_list.some(s => item.skills_list.includes(s)))
      ))
      .slice(0, 3);

    res.json({
      internship: item,
      similar
    });
  } catch (error) {
    console.error('Error fetching internship details:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// 3. GET /api/filters - Unique values for populating filter controls
router.get('/filters', async (req, res) => {
  try {
    const internships = await getCachedInternships();
    
    const locationsSet = new Set();
    const sourcesSet = new Set();
    const skillsMap = {};
    
    internships.forEach(item => {
      if (item.location) {
        // clean up locations
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
      
      if (item.skills_list) {
        item.skills_list.forEach(skill => {
          const sNormalized = skill.toLowerCase();
          // Capitalize skill cleanly
          let sDisplay = skill;
          if (sNormalized === 'sql') sDisplay = 'SQL';
          else if (sNormalized === 'python') sDisplay = 'Python';
          else if (sNormalized === 'power bi') sDisplay = 'Power BI';
          else if (sNormalized === 'tableau') sDisplay = 'Tableau';
          else if (sNormalized === 'excel') sDisplay = 'Excel';
          
          skillsMap[sNormalized] = (skillsMap[sNormalized] || 0) + 1;
        });
      }
    });

    // Sort skills by frequency
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

    res.json({
      locations: Array.from(locationsSet).sort(),
      sources: Array.from(sourcesSet).sort(),
      skills: popularSkills
    });
  } catch (error) {
    console.error('Error fetching filter values:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// 4. GET /api/stats - Dynamic charts data for Recharts
router.get('/stats', async (req, res) => {
  try {
    const internships = await getCachedInternships();
    
    // 1. Total & General Metrics
    const totalCount = internships.length;
    const highlyLegit = internships.filter(i => i.legitimacy_score >= 80).length;
    const avgLegitimacy = totalCount > 0 
      ? internships.reduce((sum, i) => sum + i.legitimacy_score, 0) / totalCount 
      : 0;
    
    // 2. Skills demand
    const skillsCount = {};
    internships.forEach(i => {
      if (i.skills_list) {
        i.skills_list.forEach(s => {
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
      .slice(0, 10); // top 10

    // 3. Top paying roles (with stipend > 0)
    const paidListings = internships
      .filter(i => i.stipend_numeric > 0)
      .sort((a, b) => b.stipend_numeric - a.stipend_numeric)
      .slice(0, 8)
      .map(i => ({
        company: i.company_name,
        role: i.role.length > 25 ? i.role.slice(0, 22) + '...' : i.role,
        stipend: i.stipend_numeric,
        stipendText: i.stipend
      }));

    // 4. Remote vs Onsite flex split
    let remoteCount = 0;
    let onsiteCount = 0;
    internships.forEach(i => {
      if (i.remote === 1 || i.remote === true || (i.location && i.location.toLowerCase().includes('remote'))) {
        remoteCount++;
      } else {
        onsiteCount++;
      }
    });
    const remoteDistribution = [
      { name: 'Remote', value: remoteCount },
      { name: 'On-site', value: onsiteCount }
    ];

    // 5. Source platforms split
    const sourceCount = {};
    internships.forEach(i => {
      if (i.source) {
        sourceCount[i.source] = (sourceCount[i.source] || 0) + 1;
      }
    });
    const sourceDistribution = Object.entries(sourceCount).map(([name, value]) => ({ name, value }));

    // 6. Top hiring companies
    const companyCount = {};
    internships.forEach(i => {
      if (i.company_name) {
        companyCount[i.company_name] = (companyCount[i.company_name] || 0) + 1;
      }
    });
    const topHiringCompanies = Object.entries(companyCount)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);

    // 7. Location distribution (top 8)
    const locationCount = {};
    internships.forEach(i => {
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

    // 8. Average stipend by role type
    const stipendByRole = {};
    internships.forEach(i => {
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

    res.json({
      metrics: {
        totalScraped: totalCount,
        highlyLegit,
        avgLegitimacy: parseFloat(avgLegitimacy.toFixed(1))
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
    });
  } catch (error) {
    console.error('Error fetching statistics:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// 5. POST /api/scrapers/run - Run Playwright scrapers in background
let activeScraperProcess = null;
let scraperLogs = [];
let scraperStatus = 'idle'; // idle, running, completed, failed

router.post('/scrapers/run', (req, res) => {
  if (scraperStatus === 'running') {
    return res.status(400).json({ status: 'running', message: 'Scraper cycle is already running.', logs: scraperLogs });
  }

  scraperStatus = 'running';
  scraperLogs = [`[${new Date().toISOString()}] Launching AI Discovery Scrapers...\n`];

  console.log('[Scraper] Triggering python run.py');
  
  // Spawn Python scraper process
  const pythonCmd = 'python';
  const args = ['run.py'];
  
  // Set working directory to ROOT_DIR so python module resolving behaves correctly
  activeScraperProcess = spawn(pythonCmd, args, {
    cwd: ROOT_DIR,
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
  });

  activeScraperProcess.stdout.on('data', (data) => {
    const logStr = data.toString();
    scraperLogs.push(logStr);
    console.log(`[Scraper Output] ${logStr.trim()}`);
  });

  activeScraperProcess.stderr.on('data', (data) => {
    const logStr = data.toString();
    scraperLogs.push(`[ERROR] ${logStr}`);
    console.error(`[Scraper Error] ${logStr.trim()}`);
  });

  activeScraperProcess.on('close', (code) => {
    activeScraperProcess = null;
    if (code === 0) {
      scraperStatus = 'completed';
      scraperLogs.push(`\n[${new Date().toISOString()}] Scraper cycle COMPLETED successfully.\n`);
      // Force cache reload on next request
      dbCache.data = [];
      dbCache.lastUpdated = null;
    } else {
      scraperStatus = 'failed';
      scraperLogs.push(`\n[${new Date().toISOString()}] Scraper cycle FAILED with exit code ${code}.\n`);
    }
    console.log(`[Scraper] Process closed with exit code ${code}`);
  });

  res.json({
    status: 'running',
    message: 'Scraper running in background.',
    logs: scraperLogs
  });
});

// Check status of scraper run
router.get('/scrapers/status', (req, res) => {
  res.json({
    status: scraperStatus,
    logs: scraperLogs
  });
});

export default router;

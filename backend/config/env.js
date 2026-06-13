import logger from '../logger.js';
import dotenv from 'dotenv';

dotenv.config();

const REQUIRED_ENV_VARS = [
  'DB_HOST',
  'DB_USER',
  'DB_NAME',
  'REDIS_HOST',
  'ADMIN_API_KEY',
  'FRONTEND_URL'
];

export function validateEnv() {
  const missing = [];
  
  const hasDatabaseUrl = process.env.DATABASE_URL && process.env.DATABASE_URL.trim() !== '';
  const requiredVars = hasDatabaseUrl
    ? REQUIRED_ENV_VARS.filter((key) => !key.startsWith('DB_'))
    : REQUIRED_ENV_VARS;
  
  requiredVars.forEach((key) => {
    if (!process.env[key] || process.env[key].trim() === '') {
      missing.push(key);
    }
  });

  if (missing.length > 0) {
    logger.error('CRITICAL STARTUP ERROR: Missing required environment variables', { missing });
    console.error(`\n❌ FATAL CONFIGURATION ERROR:\nMissing environment variables: ${missing.join(', ')}\nEnsure these are defined in your .env file.\n`);
    process.exit(1);
  }

  // URL formatting check for FRONTEND_URL
  try {
    new URL(process.env.FRONTEND_URL);
  } catch (urlErr) {
    logger.error('CRITICAL STARTUP ERROR: FRONTEND_URL is not a valid URL', { url: process.env.FRONTEND_URL });
    console.error(`\n❌ FATAL CONFIGURATION ERROR:\nFRONTEND_URL is not a valid absolute URL: ${process.env.FRONTEND_URL}\n`);
    process.exit(1);
  }

  // Warn if default API key is used
  if (process.env.ADMIN_API_KEY === 'super-secret-admin-key') {
    logger.warn('SECURITY WARNING: Using the fallback default ADMIN_API_KEY in production is highly discouraged!');
  }

  logger.info('Environment variables configuration successfully validated.');
}

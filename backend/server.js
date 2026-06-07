import express from 'express';
import cors from 'cors';
import morgan from 'morgan';
import dotenv from 'dotenv';
import apiRouter from './routes.js';
import helmet from 'helmet';
import logger from './logger.js';
import { validateEnv } from './config/env.js';

dotenv.config();
validateEnv();

const app = express();
const PORT = process.env.PORT || 5000;

app.use(helmet());

// Enable CORS for frontend Vite dev server
const allowedOrigins = [
  process.env.FRONTEND_URL || 'http://localhost:5173',
  'http://localhost:5173'
];

app.use(cors({
  origin: (origin, callback) => {
    if (!origin) return callback(null, true);
    if (allowedOrigins.indexOf(origin) === -1) {
      const msg = 'The CORS policy for this site does not allow access from the specified Origin.';
      return callback(new Error(msg), false);
    }
    return callback(null, true);
  },
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Admin-API-Key']
}));

app.use(express.json());

// Redirect HTTP requests to winston logger
app.use(morgan(':method :url :status :res[content-length] - :response-time ms', {
  stream: {
    write: (message) => logger.info(message.trim())
  }
}));

// Mount API routes
app.use('/api', apiRouter);

// Base route status
app.get('/', (req, res) => {
  res.json({
    message: 'Welcome to the Premium Internship Discovery Platform API',
    status: 'online',
    timestamp: new Date().toISOString()
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  logger.error('[Global Error Handler]', { error: err.message, stack: err.stack });
  res.status(err.status || 500).json({
    error: err.message || 'Internal Server Error'
  });
});

// Start Express server
app.listen(PORT, () => {
  logger.info(`Express server running on port: ${PORT}`);
  logger.info(`API Endpoint: http://localhost:${PORT}/api`);
});


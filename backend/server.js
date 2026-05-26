import express from 'express';
import cors from 'cors';
import morgan from 'morgan';
import dotenv from 'dotenv';
import apiRouter from './routes.js';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

// Enable CORS for frontend Vite dev server (usually localhost:5173) and any origin
app.use(cors({
  origin: '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

app.use(express.json());
app.use(morgan('dev'));

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
  console.error('[Global Error Handler]', err);
  res.status(err.status || 500).json({
    error: err.message || 'Internal Server Error'
  });
});

// Start Express server
app.listen(PORT, () => {
  console.log(`=======================================================`);
  console.log(`🚀 Express server running on port: ${PORT}`);
  console.log(`🔗 API Endpoint: http://localhost:${PORT}/api`);
  console.log(`=======================================================`);
});

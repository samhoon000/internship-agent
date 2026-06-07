import winston from 'winston';
import 'winston-daily-rotate-file';

const logFormat = winston.format.combine(
  winston.format.timestamp(),
  winston.format.json()
);

const dailyRotateFileTransport = new winston.transports.DailyRotateFile({
  filename: 'logs/backend-%DATE%.log',
  datePattern: 'YYYY-MM-DD',
  maxSize: '10m',
  maxFiles: '7d',
  level: 'info',
  format: logFormat
});

const errorRotateFileTransport = new winston.transports.DailyRotateFile({
  filename: 'logs/backend-error-%DATE%.log',
  datePattern: 'YYYY-MM-DD',
  maxSize: '10m',
  maxFiles: '14d',
  level: 'error',
  format: logFormat
});

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: logFormat,
  transports: [
    dailyRotateFileTransport,
    errorRotateFileTransport,
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.printf(
          (info) => `${info.timestamp} [${info.level}]: ${typeof info.message === 'object' ? JSON.stringify(info.message) : info.message}`
        )
      )
    })
  ]
});

export default logger;

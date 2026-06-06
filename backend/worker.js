import { Worker } from 'bullmq';
import Redis from 'ioredis';
import dotenv from 'dotenv';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

dotenv.config();

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(__dirname, '..');

const redisHost = process.env.REDIS_HOST || '127.0.0.1';
const redisPort = process.env.REDIS_PORT || 6379;

const redisConfig = {
  host: redisHost,
  port: redisPort,
  maxRetriesPerRequest: null // Required by BullMQ
};

const connection = new Redis(redisConfig);

connection.on('connect', () => {
  console.log(`🚀 Worker successfully connected to Redis at ${redisHost}:${redisPort}`);
});

connection.on('error', (err) => {
  console.error('[Worker Redis Connection Error]', err);
});

// Helper to run python scraper/pipeline scripts
function runPythonScript(args, job) {
  return new Promise((resolve, reject) => {
    console.log(`[Worker] Spawning: python ${args.join(' ')}`);
    job.log(`[Worker] Spawning python run.py with args: ${args.join(' ')}`);

    const pythonProcess = spawn('python', args, {
      cwd: ROOT_DIR,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
    });

    pythonProcess.stdout.on('data', (data) => {
      const chunk = data.toString();
      chunk.split('\n').forEach(line => {
        if (line.trim()) {
          job.log(`[STDOUT] ${line.trim()}`);
          console.log(`[Job ${job.id}] ${line.trim()}`);
        }
      });
    });

    pythonProcess.stderr.on('data', (data) => {
      const chunk = data.toString();
      chunk.split('\n').forEach(line => {
        if (line.trim()) {
          job.log(`[STDERR] ${line.trim()}`);
          console.error(`[Job ${job.id} ERR] ${line.trim()}`);
        }
      });
    });

    pythonProcess.on('close', (code) => {
      if (code === 0) {
        job.log(`[Worker] Process completed successfully (exit code 0).`);
        resolve();
      } else {
        job.log(`[Worker] Process failed with exit code ${code}.`);
        reject(new Error(`Python process exited with code ${code}`));
      }
    });

    pythonProcess.on('error', (err) => {
      job.log(`[Worker] Process error: ${err.message}`);
      reject(err);
    });
  });
}

// Instantiate worker for scraper runs
const scraperWorker = new Worker('scraper-queue', async (job) => {
  console.log(`[Worker] Starting scraper-queue job: ${job.id}`);
  await job.log(`[Worker] Processing job ${job.id} on scraper-queue`);
  // Runs full pipeline by default (which includes scraper, cleanup, and liveness)
  await runPythonScript(['run.py'], job);
  console.log(`[Worker] Completed scraper-queue job: ${job.id}`);
}, { connection });

// Instantiate worker for stale cleanups
const cleanupWorker = new Worker('cleanup-queue', async (job) => {
  console.log(`[Worker] Starting cleanup-queue job: ${job.id}`);
  await job.log(`[Worker] Processing job ${job.id} on cleanup-queue`);
  await runPythonScript(['run.py', '--cleanup'], job);
  console.log(`[Worker] Completed cleanup-queue job: ${job.id}`);
}, { connection });

// Instantiate worker for liveness checks
const livenessWorker = new Worker('liveness-queue', async (job) => {
  console.log(`[Worker] Starting liveness-queue job: ${job.id}`);
  await job.log(`[Worker] Processing job ${job.id} on liveness-queue`);
  await runPythonScript(['run.py', '--liveness'], job);
  console.log(`[Worker] Completed liveness-queue job: ${job.id}`);
}, { connection });

// Helper to clear Redis caches on scraper writes
const clearCache = async () => {
  try {
    const keys = await connection.keys('filters:*');
    if (keys.length > 0) {
      await connection.del(keys);
    }
    await connection.del('stats');
    console.log('[Worker Cache Clear] Successfully cleared stats and filters cache.');
  } catch (err) {
    console.error('[Worker Cache Clear Error]', err);
  }
};

scraperWorker.on('completed', async (job) => {
  console.log(`[Worker] Scraper job ${job.id} completed.`);
  await clearCache();
});

cleanupWorker.on('completed', async (job) => {
  console.log(`[Worker] Cleanup job ${job.id} completed.`);
  await clearCache();
});

livenessWorker.on('completed', async (job) => {
  console.log(`[Worker] Liveness job ${job.id} completed.`);
  await clearCache();
});

scraperWorker.on('failed', (job, err) => {
  console.error(`[Worker] Scraper job ${job.id} failed:`, err);
});

cleanupWorker.on('failed', (job, err) => {
  console.error(`[Worker] Cleanup job ${job.id} failed:`, err);
});

livenessWorker.on('failed', (job, err) => {
  console.error(`[Worker] Liveness job ${job.id} failed:`, err);
});

console.log('👷 Background workers initialized and listening for tasks on Redis...');

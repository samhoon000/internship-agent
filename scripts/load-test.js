import http from 'http';
import { performance } from 'perf_hooks';

const TARGET_URL = process.env.API_URL || 'http://localhost:5000/api/internships';

async function sendRequest(url) {
  const start = performance.now();
  return new Promise((resolve) => {
    http.get(url, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        const duration = performance.now() - start;
        resolve({
          status: res.statusCode,
          duration,
          success: res.statusCode === 200
        });
      });
    }).on('error', (err) => {
      const duration = performance.now() - start;
      resolve({
        status: 0,
        duration,
        success: false,
        error: err.message
      });
    });
  });
}

async function runBenchmark(totalRequests, concurrencyLimit) {
  console.log(`\n==================================================`);
  console.log(`🏃 Starting Benchmark: ${totalRequests} Virtual Users`);
  console.log(`📊 Concurrency Level : ${concurrencyLimit}`);
  console.log(`🔗 Target URL        : ${TARGET_URL}`);
  console.log(`==================================================`);

  const results = [];
  const startTime = performance.now();

  // Process requests in chunked concurrency batches to simulate load without exhausting local sockets
  for (let i = 0; i < totalRequests; i += concurrencyLimit) {
    const batchSize = Math.min(concurrencyLimit, totalRequests - i);
    const batchPromises = Array.from({ length: batchSize }, () => sendRequest(TARGET_URL));
    const batchResults = await Promise.all(batchPromises);
    results.push(...batchResults);
  }

  const totalTime = performance.now() - startTime;
  
  // Parse and aggregate metrics
  const successful = results.filter(r => r.success);
  const failed = results.filter(r => !r.success);
  const durations = results.map(r => r.duration).sort((a, b) => a - b);
  
  const total = results.length;
  const successRate = ((successful.length / total) * 100).toFixed(1);
  const avg = durations.reduce((sum, d) => sum + d, 0) / total;
  const min = durations[0] || 0;
  const max = durations[durations.length - 1] || 0;
  const p95 = durations[Math.floor(total * 0.95)] || 0;
  const p99 = durations[Math.floor(total * 0.99)] || 0;

  console.log(`\nResults:`);
  console.log(`- Total Requests Completed : ${total}`);
  console.log(`- Successful Requests      : ${successful.length} (${successRate}%)`);
  console.log(`- Failed Requests          : ${failed.length}`);
  console.log(`- Min Latency              : ${min.toFixed(1)} ms`);
  console.log(`- Average Latency          : ${avg.toFixed(1)} ms`);
  console.log(`- p95 Latency              : ${p95.toFixed(1)} ms`);
  console.log(`- p99 Latency              : ${p99.toFixed(1)} ms`);
  console.log(`- Max Latency              : ${max.toFixed(1)} ms`);
  console.log(`- Throughput               : ${((total / totalTime) * 1000).toFixed(1)} req/sec`);
  console.log(`- Total Benchmark Time     : ${(totalTime / 1000).toFixed(2)} seconds`);
  console.log(`==================================================\n`);

  return { total, successRate, avg, p95, p99 };
}

async function main() {
  try {
    // 100 users (low concurrency)
    await runBenchmark(100, 20);
    
    // 500 users (medium concurrency)
    await runBenchmark(500, 50);
    
    // 1000 users (high concurrency)
    await runBenchmark(1000, 100);
  } catch (err) {
    console.error('Benchmark execution error:', err);
  }
}

main();

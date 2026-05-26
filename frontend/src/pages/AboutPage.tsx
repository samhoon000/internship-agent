import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Play, Terminal, Info, Cpu, AlertTriangle } from 'lucide-react';
import { runScraper, fetchScraperStatus } from '../api';

export default function AboutPage() {
  const [logs, setLogs] = useState<string[]>([]);
  const [status, setStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');
  const logTerminalRef = useRef<HTMLDivElement>(null);

  // Poll scraper status every 2.5 seconds if it's currently running
  const { data: statusData, refetch: refetchStatus } = useQuery({
    queryKey: ['scraperStatus'],
    queryFn: fetchScraperStatus,
    refetchInterval: (query) => {
      const currentStatus = query.state.data?.status;
      return currentStatus === 'running' ? 2500 : false;
    }
  });

  // Sync state with polled status
  useEffect(() => {
    if (statusData) {
      setStatus(statusData.status);
      setLogs(statusData.logs);
    }
  }, [statusData]);

  // Scroll to bottom of terminal when logs change
  useEffect(() => {
    if (logTerminalRef.current) {
      logTerminalRef.current.scrollTop = logTerminalRef.current.scrollHeight;
    }
  }, [logs]);

  // Trigger scraper mutation
  const runScraperMutation = useMutation({
    mutationFn: runScraper,
    onSuccess: (data) => {
      setStatus('running');
      setLogs(data.logs);
      refetchStatus();
    },
    onError: (err: any) => {
      alert(`Failed to launch scraper: ${err.message}`);
    }
  });

  const handleTriggerScraper = () => {
    if (status === 'running') return;
    if (window.confirm('Triggering the scraper will launch Playwright crawler processes on the server. This may take up to 2-3 minutes. Continue?')) {
      runScraperMutation.mutate();
    }
  };

  const getStatusBadge = (s: string) => {
    switch (s) {
      case 'running': return 'bg-amber-50 text-amber-700 border-amber-200 animate-pulse';
      case 'completed': return 'bg-emerald-50 text-emerald-700 border-emerald-250';
      case 'failed': return 'bg-red-50 text-red-700 border-red-250';
      default: return 'bg-slate-50 text-slate-600 border-slate-200';
    }
  };

  return (
    <div className="space-y-10 max-w-5xl mx-auto pb-16">
      
      {/* Page Header */}
      <div className="border-b border-slate-200 pb-3">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <Info className="w-5 h-5 text-primary-600" />
          <span>About InternLegit</span>
        </h1>
        <p className="text-slate-500 text-xs mt-0.5">
          Learn about our background system architecture, legitimacy scoring rules, and trigger a scraper cycle.
        </p>
      </div>

      {/* 1. Main Platform Overview */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
        
        <div className="md:col-span-2 bg-white border border-slate-200 rounded-xl p-6 sm:p-7 shadow-sm space-y-4 text-slate-600 text-xs sm:text-sm leading-relaxed font-medium">
          <h2 className="text-base font-bold text-slate-900 tracking-tight">The Problem We Solve</h2>
          <p>
            Most student internship portals are cluttered with spam. Listings often lead to broken links, require deposit fees, turn out to be unpaid certificates under the guise of an internship, or are posted by fake companies that don't exist.
          </p>
          <p>
            <strong>InternLegit</strong> was built to solve this. We use automated Python scrapers to crawl top portals, analyze metadata, perform technical verification checks, and pass them through a strict scoring checklist. Listings below the safety threshold of 60% are automatically rejected before entering our database.
          </p>
        </div>

        <div className="bg-slate-900 text-white rounded-xl p-6 sm:p-7 shadow-sm flex flex-col justify-between">
          <div className="space-y-4">
            <Cpu className="w-7 h-7 text-primary-500" />
            <h3 className="text-sm font-bold tracking-tight">Tech Stack Overview</h3>
            <ul className="text-[11px] space-y-2 text-slate-300 font-semibold">
              <li className="flex items-center gap-1.5"><span className="text-emerald-400">✓</span> React, Vite & TypeScript</li>
              <li className="flex items-center gap-1.5"><span className="text-emerald-400">✓</span> Tailwind CSS & Recharts</li>
              <li className="flex items-center gap-1.5"><span className="text-emerald-400">✓</span> Express.js Node API</li>
              <li className="flex items-center gap-1.5"><span className="text-emerald-400">✓</span> MySQL Database Integration</li>
              <li className="flex items-center gap-1.5"><span className="text-emerald-400">✓</span> Playwright Python scrapers</li>
            </ul>
          </div>
          <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider block mt-6">
            Production-Ready Architecture
          </span>
        </div>
      </section>

      {/* 2. Pipeline Architecture Details */}
      <section className="space-y-5">
        <h2 className="text-base font-bold text-slate-900 tracking-tight">System Architecture Flow</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2.5">
            <div className="w-8 h-8 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-center text-slate-700 font-bold text-xs">1</div>
            <h3 className="font-bold text-slate-800 text-xs">Playwright Ingestion</h3>
            <p className="text-slate-500 text-[11px] leading-relaxed">
              Crawlers browse websites like Internshala, Wellfound, YC, and Indeed, bypass antibot structures, and parse raw listings.
            </p>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2.5">
            <div className="w-8 h-8 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-center text-slate-700 font-bold text-xs">2</div>
            <h3 className="font-bold text-slate-800 text-xs">AI Verification Heuristics</h3>
            <p className="text-slate-500 text-[11px] leading-relaxed">
              Every job is audited for a valid stipend, DNS registration on the company domain, and keyword matches (SQL, Python, etc.).
            </p>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2.5">
            <div className="w-8 h-8 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-center text-slate-700 font-bold text-xs">3</div>
            <h3 className="font-bold text-slate-800 text-xs">MySQL Synced Output</h3>
            <p className="text-slate-500 text-[11px] leading-relaxed">
              Clean records are synced into the internships database. Fuzzy matching filters duplicate listings by company + role.
            </p>
          </div>

        </div>
      </section>

      {/* 3. Terminal Scraper Control Panel */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 sm:p-7 shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
          <div className="space-y-0.5">
            <h2 className="text-sm font-bold text-slate-850 tracking-tight flex items-center gap-1.5">
              <Terminal className="w-4 h-4 text-slate-700" />
              <span>Scraper Agent Control Panel</span>
            </h2>
            <p className="text-slate-450 text-[11px] font-semibold">
              Trigger the backend Playwright python script and monitor live stdout logging.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className={`px-2.5 py-0.5 border text-[10px] font-bold rounded uppercase tracking-wider ${getStatusBadge(status)}`}>
              {status}
            </span>

            <button
              onClick={handleTriggerScraper}
              disabled={status === 'running' || runScraperMutation.isPending}
              className="flex items-center justify-center gap-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-slate-100 disabled:text-slate-400 text-white font-bold text-xs rounded-lg shadow-sm transition-colors cursor-pointer disabled:cursor-not-allowed"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>{status === 'running' ? 'Running crawlers...' : 'Trigger Scrapers'}</span>
            </button>
          </div>
        </div>

        {/* Live Terminal Output */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-[10px] text-slate-400 font-semibold px-0.5">
            <span>Terminal stdout Output</span>
            <div className="flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full bg-red-500"></span>
              <span className="inline-block w-2 h-2 rounded-full bg-amber-500"></span>
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>
            </div>
          </div>
          
          <div
            ref={logTerminalRef}
            className="w-full h-80 bg-slate-900 text-slate-200 border border-slate-800 rounded-lg p-4 font-mono text-xs overflow-y-auto leading-relaxed shadow-inner"
          >
            {logs.length === 0 ? (
              <p className="text-slate-500 italic">Terminal idle. Click "Trigger Scrapers" to execute scraping cycle and view active logs.</p>
            ) : (
              logs.map((logLine, idx) => (
                <div key={idx} className="whitespace-pre-wrap select-text">
                  {logLine}
                </div>
              ))
            )}
          </div>
          
          <div className="flex items-center justify-between text-[9px] text-slate-400 font-semibold px-0.5">
            <span className="flex items-center gap-1">
              <Cpu className="w-3 h-3 text-slate-400" />
              <span>Executable: python python_scraper/app.py --run-now</span>
            </span>
            <span>Encoding: UTF-8</span>
          </div>
        </div>

        {/* Warning Note */}
        <div className="p-3.5 bg-amber-50 border border-amber-100 rounded-lg flex items-start gap-2.5 text-xs text-amber-700 font-medium">
          <AlertTriangle className="w-4 h-4 shrink-0 text-amber-500" />
          <p className="leading-relaxed">
            <strong>Server Load Warning:</strong> Spawning scraper crawlers launches Chromium instances in the background via Playwright. Please avoid triggering multiple times simultaneously to prevent local server resource exhaustion.
          </p>
        </div>
      </section>

    </div>
  );
}

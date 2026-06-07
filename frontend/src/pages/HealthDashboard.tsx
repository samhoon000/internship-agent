import { useQuery } from '@tanstack/react-query';
import { 
  Activity, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  Database, 
  Server, 
  RefreshCw, 
  HardDrive, 
  Clock, 
  FileText, 
  FileCheck2, 
  Sparkles,
  Search,
  Bell
} from 'lucide-react';
import { fetchHealth } from '../api';

export default function HealthDashboard() {
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['healthStatus'],
    queryFn: ({ signal }) => fetchHealth(signal),
    refetchInterval: 30000 // Automatically poll every 30 seconds
  });

  const formatBytes = (bytes?: number) => {
    if (!bytes) return 'N/A';
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDuration = (seconds?: number) => {
    if (seconds === undefined) return 'N/A';
    const d = Math.floor(seconds / (3600 * 24));
    const h = Math.floor((seconds % (3600 * 24)) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const parts = [];
    if (d > 0) parts.push(`${d}d`);
    if (h > 0) parts.push(`${h}h`);
    if (m > 0 || parts.length === 0) parts.push(`${m}m`);
    return parts.join(' ');
  };

  const formatDate = (dateString?: string | null) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short'
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-5xl mx-auto py-6">
        <div className="flex justify-between items-center pb-3 border-b border-slate-200">
          <div className="space-y-2">
            <div className="h-6 w-48 bg-slate-100 rounded animate-pulse"></div>
            <div className="h-4 w-72 bg-slate-100 rounded animate-pulse"></div>
          </div>
          <div className="h-10 w-24 bg-slate-100 rounded-lg animate-pulse"></div>
        </div>
        <div className="h-32 rounded-xl bg-white border border-slate-200 shimmer shadow-sm"></div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="h-48 rounded-xl bg-white border border-slate-200 shimmer shadow-sm"></div>
          <div className="h-48 rounded-xl bg-white border border-slate-200 shimmer shadow-sm"></div>
          <div className="h-48 rounded-xl bg-white border border-slate-200 shimmer shadow-sm"></div>
        </div>
        <div className="h-64 rounded-xl bg-white border border-slate-200 shimmer shadow-sm"></div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="max-w-md mx-auto py-16 text-center space-y-4">
        <XCircle className="w-16 h-16 mx-auto text-red-500 animate-pulse" />
        <h3 className="text-xl font-bold text-slate-800">Connection Failed</h3>
        <p className="text-slate-500 text-sm leading-relaxed">
          Unable to establish a connection to the backend health endpoint. Ensure the server is running.
        </p>
        <button
          onClick={() => refetch()}
          className="px-5 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-semibold hover:bg-primary-700 shadow-sm transition-all cursor-pointer inline-flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Retry Connection</span>
        </button>
      </div>
    );
  }

  const overallHealthy = data.status === 'HEALTHY';
  const alerts = data.alerts || [];
  const services = data.services;

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-16">
      {/* Page Header */}
      <div className="border-b border-slate-200 pb-3 flex items-center justify-between">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Activity className="w-6 h-6 text-primary-600 animate-pulse" />
            <span>System Health Dashboard</span>
          </h1>
          <p className="text-slate-500 text-xs mt-0.5">
            Operational statuses, backup verification logs, database metrics, and scraper liveness indices.
          </p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className={`flex items-center gap-1.5 text-xs font-semibold bg-white border border-slate-200 px-3 py-2 rounded-lg shadow-sm hover:bg-slate-50 transition-all cursor-pointer ${
            isFetching ? 'text-slate-400' : 'text-slate-600'
          }`}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />
          <span>{isFetching ? 'Refreshing...' : 'Refresh Status'}</span>
        </button>
      </div>

      {/* Hero Health Banner (Glassmorphism & Vibrant styles) */}
      <div className={`relative overflow-hidden rounded-2xl border p-6 transition-all duration-300 shadow-sm ${
        overallHealthy 
          ? 'bg-gradient-to-br from-emerald-500/10 to-teal-500/5 border-emerald-500/20 text-emerald-950' 
          : 'bg-gradient-to-br from-amber-500/10 to-rose-500/5 border-amber-500/20 text-amber-950'
      }`}>
        <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
          <Sparkles className="w-32 h-32" />
        </div>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className={`p-3 rounded-xl border ${
              overallHealthy 
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-600' 
                : 'bg-amber-500/10 border-amber-500/20 text-amber-600 animate-bounce'
            }`}>
              {overallHealthy ? <CheckCircle2 className="w-7 h-7" /> : <AlertTriangle className="w-7 h-7" />}
            </div>
            <div>
              <h2 className="text-lg font-bold tracking-tight">
                {overallHealthy ? 'All Systems Fully Operational' : 'Action Required: System Warning'}
              </h2>
              <p className="text-xs text-slate-500 mt-1 max-w-xl">
                {overallHealthy 
                  ? 'Database connection latency is optimal. Redis caching state is active. Backup verification reports success, and web crawlers are running on schedule.' 
                  : `One or more components are experiencing degraded states. Review the active alerts below to restore full application capability.`
                }
              </p>
            </div>
          </div>
          <div className="flex flex-row md:flex-col gap-4 text-xs font-medium border-t md:border-t-0 md:border-l border-slate-200/50 pt-4 md:pt-0 md:pl-6">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-400" />
              <span>
                Uptime: <strong className="font-semibold">{formatDuration(data.uptimeSeconds)}</strong>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4 text-slate-400" />
              <span>
                Reported: <strong className="font-semibold">{formatDate(data.timestamp)}</strong>
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Grid of Main Services */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Database Metric Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-sm text-slate-800 flex items-center gap-2">
              <Database className="w-4 h-4 text-slate-500" />
              <span>MySQL Database</span>
            </h3>
            <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full border ${
              services.db.status === 'UP' 
                ? 'bg-emerald-50 text-emerald-600 border-emerald-200' 
                : 'bg-rose-50 text-rose-600 border-rose-200'
            }`}>
              {services.db.status === 'UP' ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>
          
          <div className="mt-4 space-y-3">
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400">Response Latency</span>
              <span className="font-bold text-slate-700">{services.db.status === 'UP' ? `${services.db.latencyMs} ms` : 'N/A'}</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-1.5">
              <div 
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  services.db.latencyMs < 50 ? 'bg-emerald-500 w-full' : services.db.latencyMs < 200 ? 'bg-amber-500 w-2/3' : 'bg-rose-500 w-1/3'
                }`}
              />
            </div>
            {services.db.error && (
              <div className="text-[10px] text-rose-500 bg-rose-50/50 p-2 rounded border border-rose-100 max-h-16 overflow-y-auto font-mono">
                {services.db.error}
              </div>
            )}
          </div>
        </div>

        {/* Redis Cache Status Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-sm text-slate-800 flex items-center gap-2">
              <Server className="w-4 h-4 text-slate-500" />
              <span>Redis Cache Engine</span>
            </h3>
            <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full border ${
              services.redis.status === 'ready' 
                ? 'bg-emerald-50 text-emerald-600 border-emerald-200' 
                : 'bg-amber-50 text-amber-600 border-amber-200'
            }`}>
              {services.redis.status === 'ready' ? 'READY' : 'OFFLINE'}
            </span>
          </div>

          <div className="mt-4 space-y-2 text-xs">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Connection Status</span>
              <span className="font-semibold uppercase font-mono text-slate-700">{services.redis.status}</span>
            </div>
            <p className="text-[10px] text-slate-400 leading-relaxed mt-2 border-t border-slate-100 pt-2">
              {services.redis.status === 'ready'
                ? 'Redis queue, search, and page caches are successfully registered and running.'
                : 'Offline failover active. Requests are queried directly from MySQL to prevent system hangs.'
              }
            </p>
          </div>
        </div>

        {/* Database Backup Status Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-sm text-slate-800 flex items-center gap-2">
              <HardDrive className="w-4 h-4 text-slate-500" />
              <span>System Backups</span>
            </h3>
            <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full border ${
              services.backup.status === 'HEALTHY' 
                ? 'bg-emerald-50 text-emerald-600 border-emerald-200' 
                : 'bg-rose-50 text-rose-600 border-rose-200'
            }`}>
              {services.backup.status === 'HEALTHY' ? 'VERIFIED' : 'STALE / ERROR'}
            </span>
          </div>

          <div className="mt-4 space-y-2 text-xs">
            {services.backup.status === 'HEALTHY' ? (
              <>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">File Name</span>
                  <span className="font-mono text-slate-700 text-[10px] truncate max-w-[140px]" title={services.backup.fileName}>
                    {services.backup.fileName}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Backup Size</span>
                  <span className="font-semibold text-slate-700">{formatBytes(services.backup.sizeBytes)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Backup Age</span>
                  <span className="font-semibold text-slate-700">{services.backup.ageHours} hrs ago</span>
                </div>
              </>
            ) : (
              <div className="space-y-1.5">
                <p className="text-[10px] text-rose-500 bg-rose-50/50 p-2 rounded border border-rose-100 leading-normal font-medium">
                  {services.backup.reason || services.backup.error || 'Backup file check failed.'}
                </p>
                <p className="text-[9px] text-slate-400 leading-normal">
                  Verify the daily database backup volume and docker services.
                </p>
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Active Alerts List */}
      {alerts.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <h3 className="font-bold text-sm text-slate-800 flex items-center gap-2 mb-4 border-b border-slate-100 pb-2">
            <Bell className="w-4 h-4 text-rose-500 animate-swing" />
            <span>Active Diagnostics Alerts ({alerts.length})</span>
          </h3>
          
          <div className="space-y-3">
            {alerts.map((alert: any, idx: number) => {
              const isCritical = alert.level === 'CRITICAL' || alert.level === 'HIGH';
              return (
                <div 
                  key={idx} 
                  className={`flex items-start gap-3 p-3 rounded-lg border text-xs ${
                    isCritical 
                      ? 'bg-rose-50/50 border-rose-100 text-rose-950' 
                      : 'bg-amber-50/50 border-amber-100 text-amber-950'
                  }`}
                >
                  <AlertTriangle className={`w-4.5 h-4.5 shrink-0 mt-0.5 ${
                    isCritical ? 'text-rose-500' : 'text-amber-500'
                  }`} />
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className={`px-1.5 py-0.5 text-[9px] font-bold rounded ${
                        isCritical ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-700'
                      }`}>
                        {alert.level}
                      </span>
                      <strong className="font-semibold text-slate-800">{alert.service}</strong>
                    </div>
                    <p className="text-slate-600 leading-relaxed mt-1">{alert.message}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Individual Scraper Health status list */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <h3 className="font-bold text-sm text-slate-800 flex items-center gap-2 mb-4 border-b border-slate-100 pb-2">
          <Search className="w-4 h-4 text-slate-500" />
          <span>Crawler & Scraper Diagnostics</span>
        </h3>
        
        {services.scrapers && services.scrapers.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-400 font-semibold bg-slate-50/50">
                  <th className="py-2.5 px-4">Scraper Source</th>
                  <th className="py-2.5 px-4">Status</th>
                  <th className="py-2.5 px-4">Last Successful Run</th>
                  <th className="py-2.5 px-4">Last Failure Run</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {services.scrapers.map((s: any, idx: number) => (
                  <tr key={idx} className="hover:bg-slate-50/50 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-800">{s.source}</td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                        s.healthStatus === 'HEALTHY' 
                          ? 'bg-emerald-50 text-emerald-600 border-emerald-100' 
                          : 'bg-rose-50 text-rose-600 border-rose-100'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${s.healthStatus === 'HEALTHY' ? 'bg-emerald-500' : 'bg-rose-500 animate-ping'}`} />
                        {s.healthStatus === 'HEALTHY' ? 'HEALTHY' : 'UNHEALTHY'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">{formatDate(s.lastSuccessfulScrape)}</td>
                    <td className="py-3 px-4 font-mono text-[11px]">
                      {s.lastFailure ? (
                        <span className="text-rose-500 font-medium">{formatDate(s.lastFailure)}</span>
                      ) : (
                        <span className="text-slate-400">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-slate-400 flex flex-col items-center gap-2">
            <FileText className="w-8 h-8 text-slate-300" />
            <p className="text-xs">No scraper status files or records have been logged to the database.</p>
            <p className="text-[10px] text-slate-400">Trigger the scraper once to populate status indices.</p>
          </div>
        )}
      </div>
    </div>
  );
}

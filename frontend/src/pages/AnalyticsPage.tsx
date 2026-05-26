import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area } from 'recharts';
import { ShieldAlert, BarChart2, ShieldCheck, Database, Calendar } from 'lucide-react';
import { fetchAnalytics } from '../api';

export default function AnalyticsPage() {
  // Query data from express /api/stats
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['analyticsStats'],
    queryFn: fetchAnalytics
  });

  const charts = data?.charts;
  const metrics = data?.metrics;

  // Professional Color Palettes
  const PRIMARY_COLOR = '#2563eb'; // Corporate Blue
  const ACCENT_COLOR = '#0284c7';  // Light Corporate Blue
  const DARK_COLOR = '#1e293b';    // Slate 800
  const GRAY_COLOR = '#94a3b8';    // Slate 400
  
  // Clean slate-blue hues for distributions
  const PIE_COLORS = ['#1e3a8a', '#2563eb', '#0284c7', '#38bdf8', '#64748b', '#94a3b8'];

  if (isLoading) {
    return (
      <div className="space-y-6 py-6 max-w-5xl mx-auto">
        <div className="h-6 w-32 bg-slate-100 rounded"></div>
        {/* Metric grids */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 rounded-xl bg-white border border-slate-200 shimmer shadow-sm"></div>
          ))}
        </div>
        {/* Charts grids */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-80 rounded-xl bg-white border border-slate-200 shimmer shadow-sm"></div>
          ))}
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="max-w-md mx-auto py-16 text-center space-y-4">
        <ShieldAlert className="w-14 h-14 mx-auto text-red-500 animate-pulse" />
        <h3 className="text-lg font-bold text-slate-800">Analytics load failed</h3>
        <p className="text-slate-500 text-xs leading-relaxed">
          Ensure the Express server and MySQL database are connected and online.
        </p>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg text-xs font-semibold hover:bg-primary-700 shadow-sm transition-colors cursor-pointer"
        >
          Reload Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-16">
      
      {/* Page Header */}
      <div className="border-b border-slate-200 pb-3 flex items-center justify-between">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <BarChart2 className="w-5 h-5 text-primary-600" />
            <span>Market Analytics Dashboard</span>
          </h1>
          <p className="text-slate-500 text-xs mt-0.5">
            Real-time hiring trends, skills demand, and stipend levels from aggregated tech internships.
          </p>
        </div>
        <div className="hidden sm:flex items-center gap-1.5 text-[10px] text-slate-400 font-semibold bg-white border border-slate-200 px-3 py-1.5 rounded-lg shadow-sm">
          <Calendar className="w-3.5 h-3.5" />
          <span>Last Updated: Real-time</span>
        </div>
      </div>

      {/* Metrics Row (Clean, flat boxes) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex items-center gap-4">
          <div className="p-2.5 bg-slate-50 text-slate-700 border border-slate-200/60 rounded-lg">
            <Database className="w-5 h-5 text-primary-600" />
          </div>
          <div>
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Total Internships</p>
            <p className="text-xl font-bold text-slate-900 mt-0.5 leading-none">{metrics?.totalScraped}</p>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex items-center gap-4">
          <div className="p-2.5 bg-slate-50 text-slate-700 border border-slate-200/60 rounded-lg">
            <ShieldCheck className="w-5 h-5 text-emerald-600" />
          </div>
          <div>
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">High Trust (80+ Score)</p>
            <p className="text-xl font-bold text-slate-900 mt-0.5 leading-none">{metrics?.highlyLegit}</p>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex items-center gap-4">
          <div className="p-2.5 bg-slate-50 text-slate-700 border border-slate-200/60 rounded-lg">
            <ShieldCheck className="w-5 h-5 text-primary-600" />
          </div>
          <div>
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Avg Legitimacy Score</p>
            <p className="text-xl font-bold text-slate-900 mt-0.5 leading-none">{metrics?.avgLegitimacy} / 100</p>
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Chart 1: Top Skills Demand */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col h-80">
          <div className="mb-4">
            <h3 className="font-bold text-slate-800 text-xs tracking-wider uppercase">Top Skills in Demand</h3>
            <p className="text-slate-400 text-[10px] mt-0.5">Most frequently required skills listed across roles.</p>
          </div>
          <div className="flex-1 w-full text-[10px] font-semibold">
            {charts?.skillsDemand && charts.skillsDemand.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts.skillsDemand} layout="vertical" margin={{ left: 10, right: 10, top: 5, bottom: 5 }}>
                  <XAxis type="number" stroke={GRAY_COLOR} />
                  <YAxis dataKey="name" type="category" stroke={GRAY_COLOR} width={65} />
                  <Tooltip cursor={{ fill: 'rgba(37, 99, 235, 0.04)' }} contentStyle={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '11px' }} />
                  <Bar dataKey="value" fill={PRIMARY_COLOR} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400 italic">No skills data available.</div>
            )}
          </div>
        </div>

        {/* Chart 2: Top Paying Internships */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col h-80">
          <div className="mb-4">
            <h3 className="font-bold text-slate-800 text-xs tracking-wider uppercase">Top Paying Internships</h3>
            <p className="text-slate-400 text-[10px] mt-0.5">Highest stipend values captured in current cycles.</p>
          </div>
          <div className="flex-1 w-full text-[9px] font-semibold">
            {charts?.topPaying && charts.topPaying.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts.topPaying} margin={{ top: 10, right: 10, left: 5, bottom: 15 }}>
                  <XAxis dataKey="company" stroke={GRAY_COLOR} />
                  <YAxis stroke={GRAY_COLOR} unit="₹" />
                  <Tooltip contentStyle={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '11px' }} />
                  <Bar dataKey="stipend" fill={ACCENT_COLOR} radius={[4, 4, 0, 0]} label={{ position: 'top', fill: '#475569', fontSize: 9 }} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400 italic">No stipend details available.</div>
            )}
          </div>
        </div>

        {/* Chart 3: Remote Split */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col h-80">
          <div className="mb-4">
            <h3 className="font-bold text-slate-800 text-xs tracking-wider uppercase">Workplace Flexibility Split</h3>
            <p className="text-slate-400 text-[10px] mt-0.5">Distribution of Remote/Work from Home vs. On-site positions.</p>
          </div>
          <div className="flex-grow flex items-center justify-center">
            {charts?.remoteDistribution && charts.remoteDistribution.some(c => c.value > 0) ? (
              <div className="w-full h-full flex flex-col sm:flex-row items-center justify-center gap-6">
                <div className="w-40 h-40">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={charts.remoteDistribution}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={65}
                        paddingAngle={4}
                        dataKey="value"
                      >
                        <Cell fill={ACCENT_COLOR} />
                        <Cell fill={PRIMARY_COLOR} />
                      </Pie>
                      <Tooltip contentStyle={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '11px' }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="space-y-1.5 text-xs font-semibold">
                  {charts.remoteDistribution.map((item, idx) => (
                    <div key={item.name} className="flex items-center gap-2">
                      <span className="w-3 h-3 rounded" style={{ backgroundColor: idx === 0 ? ACCENT_COLOR : PRIMARY_COLOR }}></span>
                      <span className="text-slate-650">{item.name}:</span>
                      <span className="text-slate-800 font-bold">{item.value} postings</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-slate-400 italic">No flexibility details available.</div>
            )}
          </div>
        </div>

        {/* Chart 4: Source Distribution */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col h-80">
          <div className="mb-4">
            <h3 className="font-bold text-slate-800 text-xs tracking-wider uppercase">Source Platforms Split</h3>
            <p className="text-slate-400 text-[10px] mt-0.5">Where our scrapers aggregate listings from.</p>
          </div>
          <div className="flex-grow flex items-center justify-center">
            {charts?.sourceDistribution && charts.sourceDistribution.length > 0 ? (
              <div className="w-full h-full flex flex-col sm:flex-row items-center justify-center gap-6">
                <div className="w-40 h-40">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={charts.sourceDistribution}
                        cx="50%"
                        cy="50%"
                        outerRadius={65}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {charts.sourceDistribution.map((_, index) => (
                          <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '11px' }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="space-y-1.5 text-xs font-semibold">
                  {charts.sourceDistribution.map((item, idx) => (
                    <div key={item.name} className="flex items-center gap-2">
                      <span className="w-3 h-3 rounded" style={{ backgroundColor: PIE_COLORS[idx % PIE_COLORS.length] }}></span>
                      <span className="text-slate-650">{item.name}:</span>
                      <span className="text-slate-800 font-bold">{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-slate-400 italic">No source distribution details.</div>
            )}
          </div>
        </div>

        {/* Chart 5: Top Hiring Companies */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col h-80">
          <div className="mb-4">
            <h3 className="font-bold text-slate-800 text-xs tracking-wider uppercase">Active Hiring Companies</h3>
            <p className="text-slate-400 text-[10px] mt-0.5">Top companies with the most internship listings in our DB.</p>
          </div>
          <div className="flex-1 w-full text-[10px] font-semibold">
            {charts?.topCompanies && charts.topCompanies.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts.topCompanies} margin={{ top: 10, right: 10, left: 5, bottom: 15 }}>
                  <XAxis dataKey="name" stroke={GRAY_COLOR} />
                  <YAxis stroke={GRAY_COLOR} />
                  <Tooltip contentStyle={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '11px' }} />
                  <Bar dataKey="count" fill={DARK_COLOR} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400 italic">No company distribution data.</div>
            )}
          </div>
        </div>

        {/* Chart 6: Average Stipend Trend by Role */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col h-80">
          <div className="mb-4">
            <h3 className="font-bold text-slate-800 text-xs tracking-wider uppercase">Average Stipend by Role Type</h3>
            <p className="text-slate-400 text-[10px] mt-0.5">Comparison of average monthly stipends across role types.</p>
          </div>
          <div className="flex-1 w-full text-[10px] font-semibold">
            {charts?.avgStipendTrend && charts.avgStipendTrend.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={charts.avgStipendTrend} margin={{ top: 10, right: 10, left: 5, bottom: 15 }}>
                  <defs>
                    <linearGradient id="stipendGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={PRIMARY_COLOR} stopOpacity={0.25}/>
                      <stop offset="95%" stopColor={PRIMARY_COLOR} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="name" stroke={GRAY_COLOR} />
                  <YAxis stroke={GRAY_COLOR} unit="₹" />
                  <Tooltip contentStyle={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '11px' }} />
                  <Area type="monotone" dataKey="avgStipend" stroke={PRIMARY_COLOR} strokeWidth={2} fillOpacity={1} fill="url(#stipendGradient)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400 italic">No stipend metrics.</div>
            )}
          </div>
        </div>

      </div>

    </div>
  );
}

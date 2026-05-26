import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Compass, BarChart2, ShieldCheck, Search, Star, Award, Zap, Filter, MapPin } from 'lucide-react';

export default function LandingPage() {
  const navigate = useNavigate();
  const [searchVal, setSearchVal] = useState('');
  const [locationVal, setLocationVal] = useState('');

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const queryParams = new URLSearchParams();
    if (searchVal.trim()) {
      queryParams.append('search', searchVal.trim());
    }
    if (locationVal.trim()) {
      if (locationVal.toLowerCase() === 'remote') {
        queryParams.append('remote', 'true');
      } else {
        queryParams.append('locations', locationVal.trim().toLowerCase());
      }
    }
    navigate(`/explore?${queryParams.toString()}`);
  };

  const trustMetrics = [
    { label: 'Total Tracked', value: '12,000+' },
    { label: 'Update Cycle', value: 'Daily Refresh' },
    { label: 'Scoring Confidence', value: '95% Accuracy' },
    { label: 'Minimum Compensation', value: 'Paid Only' }
  ];

  const features = [
    {
      title: 'Verified Companies',
      desc: 'Only legitimate companies with valid domains, active online footprints, and authentic physical addresses are displayed.',
      icon: Award
    },
    {
      title: 'Paid Internships Only',
      desc: 'Absolutely no unpaid junk or certificate-only training scams. Every listing must offer a valid stipend.',
      icon: Star
    },
    {
      title: 'Legitimacy Scoring',
      desc: 'A robust 100-point validation check scoring company registry data, domain health, and job posting validity.',
      icon: ShieldCheck
    },
    {
      title: 'Smart Tech Filters',
      desc: 'Instant, precise search parameters for core analytics tools: SQL, Excel, Python, Power BI, Tableau, and Statistics.',
      icon: Filter
    },
    {
      title: 'Real-time Aggregator',
      desc: 'Playwright scrapers actively crawl Internshala, Wellfound, YC Startup Jobs, and Indeed daily to find listings first.',
      icon: Zap
    }
  ];

  const companies = [
    'Google', 'Microsoft', 'Deloitte', 'PwC', 'TCS', 'Infosys', 'Accenture', 'KPMG', 'Amazon'
  ];

  const pipelineSteps = [
    {
      num: '01',
      title: 'Crawler Ingestion',
      desc: 'Automated Playwright scrapers scan top platforms daily.'
    },
    {
      num: '02',
      title: 'Legitimacy Check',
      desc: 'DNS resolution, domain age checks, and online checks verify company standing.'
    },
    {
      num: '03',
      title: 'Spam Filtration',
      desc: 'Auto-rejection logic filters unpaid, fee-charging, or low-scoring listings.'
    },
    {
      num: '04',
      title: 'Board Delivery',
      desc: 'Top verified listings are delivered with a visual trust score.'
    }
  ];

  return (
    <div className="space-y-20 pb-16">
      
      {/* 1. Hero Section */}
      <section className="relative pt-8 md:pt-16 max-w-4xl mx-auto text-center space-y-6">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-slate-700 text-xs font-medium">
          <ShieldCheck className="w-3.5 h-3.5 text-primary-600" />
          <span>Active Legitimacy Audit Pipeline</span>
        </div>
        
        <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-slate-900 leading-tight">
          Find Verified, Paid <br className="hidden sm:inline" />
          <span className="text-primary-600">Data Analyst</span> Internships
        </h1>
        
        <p className="text-base sm:text-lg text-slate-500 max-w-xl mx-auto leading-relaxed">
          Discover vetted data analyst, data science, and business intelligence internships from validated companies and top startup hubs.
        </p>

        {/* Structured Multi-Field Search Bar (LinkedIn/Indeed Style) */}
        <form onSubmit={handleSearchSubmit} className="max-w-3xl mx-auto pt-6 px-4">
          <div className="flex flex-col md:flex-row items-center bg-white rounded-xl border border-slate-250 shadow-sm focus-within:border-slate-400 divide-y md:divide-y-0 md:divide-x divide-slate-200 overflow-hidden">
            <div className="flex items-center flex-1 w-full px-3 py-3">
              <Search className="w-4 h-4 text-slate-400 shrink-0 ml-1" />
              <input
                type="text"
                placeholder="Job title, keywords, or skills (SQL, Python...)"
                value={searchVal}
                onChange={(e) => setSearchVal(e.target.value)}
                className="w-full px-3 py-1 bg-transparent text-sm text-slate-800 placeholder-slate-450 outline-none"
              />
            </div>
            <div className="flex items-center flex-1 w-full px-3 py-3">
              <MapPin className="w-4 h-4 text-slate-400 shrink-0 ml-1" />
              <input
                type="text"
                placeholder="Location, country or 'Remote'"
                value={locationVal}
                onChange={(e) => setLocationVal(e.target.value)}
                className="w-full px-3 py-1 bg-transparent text-sm text-slate-800 placeholder-slate-450 outline-none"
              />
            </div>
            <button
              type="submit"
              className="w-full md:w-auto px-6 py-4 font-semibold text-white bg-primary-600 hover:bg-primary-700 transition-colors shrink-0 text-sm cursor-pointer"
            >
              Search Jobs
            </button>
          </div>
        </form>

        {/* CTA Buttons */}
        <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
          <Link
            to="/explore"
            className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-lg text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 shadow-sm transition-colors"
          >
            <Compass className="w-4 h-4" />
            <span>Explore All Internships</span>
          </Link>
          <Link
            to="/analytics"
            className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-lg text-sm font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 shadow-sm transition-colors"
          >
            <BarChart2 className="w-4 h-4" />
            <span>Market Dashboard</span>
          </Link>
        </div>
      </section>

      {/* 2. Trust Metrics Grid (Flat, divided board style) */}
      <section className="max-w-5xl mx-auto">
        <div className="bg-white border border-slate-200 rounded-xl py-6 px-4 grid grid-cols-2 md:grid-cols-4 gap-6 shadow-sm divide-y md:divide-y-0 md:divide-x divide-slate-100">
          {trustMetrics.map((metric, i) => (
            <div key={i} className="text-center px-4 first:pt-0 pt-4 md:pt-0">
              <p className="text-2xl sm:text-3xl font-extrabold text-slate-900">
                {metric.value}
              </p>
              <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mt-1">
                {metric.label}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* 3. Features Section (Clean, flat cards) */}
      <section className="space-y-8 max-w-5xl mx-auto">
        <div className="text-center space-y-2">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Built for Data Analysts
          </h2>
          <p className="text-slate-500 max-w-lg mx-auto text-sm">
            We clean, verify, and score listings. No certificate scams or unpaid training positions.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {features.slice(0, 3).map((feat, i) => {
            const Icon = feat.icon;
            return (
              <div key={i} className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm hover:border-slate-350 transition-colors flex flex-col items-start space-y-3">
                <div className="p-2 rounded-lg bg-slate-50 text-slate-700 border border-slate-200/60">
                  <Icon className="w-5 h-5 text-primary-600" />
                </div>
                <h3 className="text-base font-bold text-slate-900">{feat.title}</h3>
                <p className="text-slate-500 text-xs leading-relaxed">{feat.desc}</p>
              </div>
            );
          })}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 max-w-4xl mx-auto">
          {features.slice(3, 5).map((feat, i) => {
            const Icon = feat.icon;
            return (
              <div key={i} className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm hover:border-slate-350 transition-colors flex flex-col items-start space-y-3">
                <div className="p-2 rounded-lg bg-slate-50 text-slate-700 border border-slate-200/60">
                  <Icon className="w-5 h-5 text-primary-600" />
                </div>
                <h3 className="text-base font-bold text-slate-900">{feat.title}</h3>
                <p className="text-slate-500 text-xs leading-relaxed">{feat.desc}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* 4. Top Companies Section (Subtle text logo list) */}
      <section className="border-y border-slate-200/65 py-10 -mx-4 sm:-mx-6 lg:-mx-8 px-8 bg-slate-50/50">
        <div className="max-w-5xl mx-auto space-y-5">
          <p className="text-center text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            Tracking listings across major platforms & top tech firms
          </p>
          <div className="flex flex-wrap items-center justify-center gap-x-10 gap-y-4 text-sm font-semibold text-slate-400">
            {companies.map((company, i) => (
              <span key={i} className="hover:text-slate-600 transition-colors select-none">
                {company}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* 5. How It Works Section */}
      <section className="space-y-12 max-w-5xl mx-auto">
        <div className="text-center space-y-2">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            How The Discovery Pipeline Works
          </h2>
          <p className="text-slate-500 max-w-lg mx-auto text-sm">
            Our automated agent pipeline runs daily, scoring and filtering listings before they hit our website.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {pipelineSteps.map((step, i) => (
            <div key={i} className="relative space-y-2 p-5 bg-white border border-slate-200 rounded-xl shadow-sm">
              <span className="text-xs font-bold text-primary-600 font-mono tracking-wider">
                STEP {step.num}
              </span>
              <h3 className="text-sm font-bold text-slate-900">{step.title}</h3>
              <p className="text-slate-500 text-[11px] leading-relaxed">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 6. CTA Banner (Flat slate block) */}
      <section className="max-w-5xl mx-auto">
        <div className="bg-slate-900 rounded-xl p-8 sm:p-10 text-center text-white space-y-5 shadow-sm relative overflow-hidden">
          <h2 className="text-2xl sm:text-4xl font-extrabold tracking-tight max-w-xl mx-auto leading-tight">
            Ready to find your next verified internship?
          </h2>
          <p className="text-slate-400 text-xs sm:text-sm max-w-md mx-auto leading-relaxed">
            Apply with confidence. Only verified, high confidence roles matching SQL, Python, Excel, and Power BI tools.
          </p>
          <div className="pt-2">
            <Link
              to="/explore"
              className="inline-flex items-center px-5 py-2.5 rounded-lg font-bold bg-white text-slate-900 hover:bg-slate-50 shadow-sm transition-colors text-sm cursor-pointer"
            >
              Explore Job Board
            </Link>
          </div>
        </div>
      </section>

    </div>
  );
}

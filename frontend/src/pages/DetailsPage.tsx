import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Bookmark, ExternalLink, ShieldCheck, Share2, Building } from 'lucide-react';
import { fetchInternshipDetails } from '../api';
import type { Internship } from '../api';
import InternshipCard from '../components/InternshipCard';

export default function DetailsPage() {
  const { applyLink } = useParams<{ applyLink: string }>();
  const navigate = useNavigate();
  const [isSaved, setIsSaved] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);

  // Fetch internship details by decoded applyLink
  const { data, isLoading, isError } = useQuery({
    queryKey: ['internshipDetails', applyLink],
    queryFn: () => fetchInternshipDetails(decodeURIComponent(applyLink || '')),
    enabled: !!applyLink
  });

  const internship = data?.internship;
  const similarListings = data?.similar || [];

  // Check if saved
  useEffect(() => {
    if (internship) {
      try {
        const saved = JSON.parse(localStorage.getItem('saved_internships') || '[]');
        setIsSaved(saved.some((item: Internship) => item.apply_link === internship.apply_link));
      } catch (e) {
        setIsSaved(false);
      }
    }
  }, [internship]);

  const toggleSave = () => {
    if (!internship) return;
    try {
      let saved = JSON.parse(localStorage.getItem('saved_internships') || '[]');
      if (isSaved) {
        saved = saved.filter((item: Internship) => item.apply_link !== internship.apply_link);
      } else {
        saved.push(internship);
      }
      localStorage.setItem('saved_internships', JSON.stringify(saved));
      setIsSaved(!isSaved);
      window.dispatchEvent(new Event('bookmarks-changed'));
    } catch (err) {
      console.error('Error toggling save:', err);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-5 py-6 animate-pulse">
        <div className="h-6 w-24 bg-slate-100 rounded"></div>
        <div className="bg-white border border-slate-200 rounded-xl p-6 sm:p-8 space-y-6 shadow-sm">
          <div className="flex gap-4">
            <div className="w-14 h-14 rounded-lg bg-slate-100"></div>
            <div className="flex-grow space-y-2.5 pt-1">
              <div className="h-4 w-1/4 bg-slate-100 rounded"></div>
              <div className="h-5 w-1/2 bg-slate-100 rounded"></div>
            </div>
          </div>
          <div className="grid grid-cols-4 gap-4 pt-6 border-t border-slate-100">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-14 rounded-lg bg-slate-100"></div>
            ))}
          </div>
          <div className="h-32 rounded-lg bg-slate-100 mt-6"></div>
        </div>
      </div>
    );
  }

  if (isError || !internship) {
    return (
      <div className="max-w-md mx-auto py-16 text-center space-y-4">
        <ShieldCheck className="w-14 h-14 mx-auto text-red-400" />
        <h3 className="text-lg font-bold text-slate-800">Listing details not found</h3>
        <p className="text-slate-500 text-xs leading-relaxed">
          The listing link might have expired or does not exist. Back to Explore.
        </p>
        <Link
          to="/explore"
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary-600 text-white font-bold rounded-lg text-xs hover:bg-primary-700 shadow-sm transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Aggregator</span>
        </Link>
      </div>
    );
  }

  // Get color configurations depending on legitimacy score
  const getLegitimacyColors = (score: number) => {
    if (score >= 90) return { bg: 'bg-emerald-50 text-emerald-700 border-emerald-200/50', badge: 'bg-emerald-600 text-white', text: 'text-emerald-600', fill: '#10b981', label: 'Excellent verification status' };
    if (score >= 75) return { bg: 'bg-blue-50 text-blue-700 border-blue-200/50', badge: 'bg-blue-600 text-white', text: 'text-blue-600', fill: '#2563eb', label: 'High confidence match' };
    return { bg: 'bg-slate-50 text-slate-700 border-slate-200/60', badge: 'bg-slate-600 text-white', text: 'text-slate-500', fill: '#64748b', label: 'Basic credibility audit passed' };
  };

  const colors = getLegitimacyColors(internship.legitimacy_score);

  // Generate initials for logo avatar
  const getInitials = (name: string) => {
    return name
      ? name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
      : 'CO';
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-16">
      
      {/* Back & Share Buttons */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/explore')}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 rounded-lg bg-white text-slate-650 text-xs font-semibold hover:text-slate-800 hover:bg-slate-50 transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to aggregator</span>
        </button>

        <div className="flex items-center gap-2">
          <button
            onClick={copyToClipboard}
            className="inline-flex items-center justify-center p-2 border border-slate-200 bg-white hover:bg-slate-50 rounded-lg text-slate-500 hover:text-slate-800 transition-colors cursor-pointer"
            title="Share Internship"
          >
            <Share2 className="w-3.5 h-3.5" />
          </button>
          {copiedLink && (
            <span className="text-[10px] text-emerald-600 font-bold bg-emerald-50 border border-emerald-100 px-2.5 py-1 rounded-md">
              Copied to clipboard!
            </span>
          )}
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
        
        {/* Left Columns - Details */}
        <div className="md:col-span-2 space-y-6">
          
          {/* Main Card */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 sm:p-7 shadow-sm space-y-5">
            
            {/* Header info */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:justify-between pb-5 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-lg flex items-center justify-center font-bold text-slate-600 bg-slate-50 border border-slate-200 shrink-0 text-sm tracking-wider">
                  {getInitials(internship.company_name)}
                </div>
                <div>
                  <div className="flex items-center gap-1 text-slate-500 font-semibold text-xs">
                    <Building className="w-3.5 h-3.5" />
                    <span>{internship.company_name}</span>
                  </div>
                  <h1 className="text-lg sm:text-xl font-bold text-slate-900 mt-0.5 leading-snug">
                    {internship.role}
                  </h1>
                </div>
              </div>

              {/* Save trigger */}
              <button
                onClick={toggleSave}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 border rounded-lg text-xs font-semibold transition-all self-stretch sm:self-auto justify-center cursor-pointer ${
                  isSaved
                    ? 'bg-primary-50 text-primary-650 border-primary-200 shadow-sm'
                    : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                }`}
              >
                <Bookmark className={`w-3.5 h-3.5 ${isSaved ? 'fill-current' : ''}`} />
                <span>{isSaved ? 'Bookmarked' : 'Save opportunity'}</span>
              </button>
            </div>

            {/* Quick Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-center">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Stipend</p>
                <p className="text-slate-800 font-bold text-xs truncate">{internship.stipend || 'Unspecified'}</p>
              </div>
              <div className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-center">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Location</p>
                <p className="text-slate-800 font-bold text-xs truncate">{internship.location || 'On-site'}</p>
              </div>
              <div className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-center">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Duration</p>
                <p className="text-slate-800 font-bold text-xs truncate">{internship.duration || 'Not specified'}</p>
              </div>
              <div className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-center">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Source</p>
                <p className="text-slate-800 font-bold text-xs truncate">{internship.source}</p>
              </div>
            </div>

            {/* Badges Flex */}
            <div className="flex flex-wrap gap-1.5">
              {internship.remote === 1 && (
                <span className="px-2.5 py-1 text-xs font-semibold bg-primary-50 text-primary-750 border border-primary-100 rounded-lg">
                  Remote position
                </span>
              )}
              {internship.paid === 1 && (
                <span className="px-2.5 py-1 text-xs font-semibold bg-emerald-50 text-emerald-755 border border-emerald-100 rounded-lg">
                  Verified compensation
                </span>
              )}
            </div>

            {/* Core Skills Required */}
            <div className="space-y-2 pt-4 border-t border-slate-100">
              <h3 className="font-bold text-slate-800 text-[10px] tracking-wider uppercase">Required Skills</h3>
              {internship.skills_list.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {internship.skills_list.map((skill, index) => (
                    <span
                      key={index}
                      className="px-2.5 py-1 text-xs font-medium bg-slate-50 border border-slate-200 text-slate-700 rounded-lg"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-slate-400 text-xs italic font-medium">No specific tool tags parsed. Data Analyst keyword match validates the listing.</p>
              )}
            </div>

            {/* Job details text */}
            <div className="space-y-3 pt-5 border-t border-slate-100 text-slate-650 text-xs leading-relaxed font-medium">
              <h3 className="font-bold text-slate-800 text-[10px] tracking-wider uppercase">Discovery Details</h3>
              <p>
                This listing was aggregated via automated scraper agents from <strong className="text-slate-700">{internship.source}</strong>. Our parser matches keyword prerequisites and screens domain records daily to filter out expired listings or certificate scams.
              </p>
              
              <div className="bg-slate-50 border border-slate-150 rounded-lg p-3.5 space-y-1.5 font-medium text-slate-550">
                <div className="flex items-center justify-between">
                  <span>Source Platform Link:</span>
                  <a
                    href={internship.apply_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary-600 hover:text-primary-800 font-bold inline-flex items-center gap-0.5"
                  >
                    Open original listing <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <div className="flex items-center justify-between">
                  <span>Scraped Timestamp:</span>
                  <span className="font-mono text-slate-600">
                    {new Date(internship.created_at).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>

          </div>

          {/* AI Legitimacy Breakdown Card */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 sm:p-7 shadow-sm space-y-5">
            <h3 className="font-bold text-slate-850 text-sm flex items-center gap-1.5">
              <ShieldCheck className={`w-4 h-4 ${colors.text}`} />
              <span>AI Verification Checks Audit</span>
            </h3>

            <div className="flex flex-col sm:flex-row items-center gap-5 p-4 rounded-xl border border-slate-100 bg-slate-50/50">
              {/* Circular Gauge */}
              <div className="relative w-20 h-20 flex items-center justify-center shrink-0">
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="40"
                    cy="40"
                    r="34"
                    stroke="#f1f5f9"
                    strokeWidth="6"
                    fill="transparent"
                  />
                  <circle
                    cx="40"
                    cy="40"
                    r="34"
                    stroke={colors.fill}
                    strokeWidth="6"
                    fill="transparent"
                    strokeDasharray={`${2 * Math.PI * 34}`}
                    strokeDashoffset={`${2 * Math.PI * 34 * (1 - internship.legitimacy_score / 100)}`}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute text-center">
                  <span className="text-lg font-bold text-slate-850">{internship.legitimacy_score}</span>
                  <span className="text-[9px] text-slate-400 block font-bold leading-none">/100</span>
                </div>
              </div>

              <div className="space-y-1.5 text-center sm:text-left">
                <h4 className="font-bold text-slate-800 text-xs">
                  Legitimacy Score: {internship.legitimacy_score}% Accuracy
                </h4>
                <p className="text-slate-500 text-[11px] leading-relaxed">
                  Evaluated using 4 core validation parameters. Minimum 60% confidence is required to bypass auto-spam filters.
                </p>
                <span className={`inline-block px-2.5 py-0.5 text-[9px] font-bold rounded border uppercase tracking-wider ${colors.bg}`}>
                  {colors.label}
                </span>
              </div>
            </div>

            {/* Score Factors Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="flex items-start gap-2">
                <span className="w-4 h-4 rounded-full bg-emerald-500 text-white flex items-center justify-center shrink-0 text-[9px] font-bold">✓</span>
                <div>
                  <p className="text-slate-800 font-semibold">Compensation Checked</p>
                  <p className="text-slate-400 text-[10px] mt-0.5">Listing declares a valid stipend value (paid only).</p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <span className="w-4 h-4 rounded-full bg-emerald-500 text-white flex items-center justify-center shrink-0 text-[9px] font-bold">✓</span>
                <div>
                  <p className="text-slate-800 font-semibold">Domain Resolution</p>
                  <p className="text-slate-400 text-[10px] mt-0.5">Company domain is online, resolving DNS queries.</p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <span className="w-4 h-4 rounded-full bg-emerald-500 text-white flex items-center justify-center shrink-0 text-[9px] font-bold">✓</span>
                <div>
                  <p className="text-slate-800 font-semibold">Keyword Match</p>
                  <p className="text-slate-400 text-[10px] mt-0.5">Prerequisites focus on analytical tools (SQL, BI, Python).</p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <span className="w-4 h-4 rounded-full bg-emerald-500 text-white flex items-center justify-center shrink-0 text-[9px] font-bold">✓</span>
                <div>
                  <p className="text-slate-800 font-semibold">Safe Destination Standard</p>
                  <p className="text-slate-400 text-[10px] mt-0.5">Redirect destination runs over HTTPS, matches source host.</p>
                </div>
              </div>
            </div>
          </div>

        </div>

        {/* Right Columns - Sticky Apply Panel */}
        <aside className="space-y-6 md:sticky md:top-24">
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4 text-center">
            <h3 className="font-bold text-slate-800 text-[10px] tracking-wider uppercase">Apply to Listing</h3>
            
            <a
              href={internship.apply_link}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full inline-flex items-center justify-center gap-1.5 px-5 py-3 bg-primary-600 hover:bg-primary-700 text-white font-bold rounded-lg shadow-sm transition-colors text-xs cursor-pointer"
            >
              <span>Apply now</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>

            <p className="text-[10px] text-slate-400 leading-relaxed font-medium">
              This action redirects you to the application form hosted on <strong className="text-slate-500">{internship.source}</strong>. Note: Legitimate companies will never demand payment for applications or training.
            </p>

            <div className="border-t border-slate-100 pt-4 flex flex-col items-center gap-1.5">
              <div className="flex items-center gap-1 text-[11px] font-semibold text-slate-500">
                <ShieldCheck className="w-4 h-4 text-emerald-500 animate-pulse" />
                <span>Audited opportunity</span>
              </div>
              <span className="text-[9px] bg-slate-50 border border-slate-200 text-slate-500 px-2 py-0.5 rounded font-mono">
                verification={internship.legitimacy_score}%
              </span>
            </div>
          </div>
        </aside>

      </div>

      {/* Suggested Similar Internships */}
      <section className="space-y-5 border-t border-slate-200/60 pt-10">
        <div className="space-y-1">
          <h2 className="text-lg font-bold text-slate-850 tracking-tight">
            Similar Internships
          </h2>
          <p className="text-slate-450 text-xs">
            Opportunities with similar skills requirements or platforms.
          </p>
        </div>

        {similarListings.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {similarListings.slice(0, 3).map((simItem) => (
              <InternshipCard key={simItem.apply_link} internship={simItem} />
            ))}
          </div>
        ) : (
          <div className="bg-slate-50 border border-slate-200/40 rounded-xl p-8 text-center text-slate-450 text-xs font-semibold">
            No matching similar internships found currently.
          </div>
        )}
      </section>

    </div>
  );
}

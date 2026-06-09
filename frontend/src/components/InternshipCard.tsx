import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Bookmark, MapPin, DollarSign, IndianRupee, Banknote, Calendar, ExternalLink, ShieldCheck } from 'lucide-react';
import type { Internship } from '../api';
import { formatStipend } from '../utils/formatters';

interface InternshipCardProps {
  internship: Internship;
  onBookmarkChanged?: () => void;
}

function InternshipCard({ internship, onBookmarkChanged }: InternshipCardProps) {
  const [isSaved, setIsSaved] = useState(false);
  const [showMatchTooltip, setShowMatchTooltip] = useState(false);
  const [showLegitTooltip, setShowLegitTooltip] = useState(false);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('saved_internships') || '[]');
      setIsSaved(saved.some((item: Internship) => item.apply_link === internship.apply_link));
    } catch {
      setIsSaved(false);
    }
  }, [internship.apply_link]);

  const toggleSave = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      let saved = JSON.parse(localStorage.getItem('saved_internships') || '[]');
      if (isSaved) {
        saved = saved.filter((item: Internship) => item.apply_link !== internship.apply_link);
      } else {
        saved.push(internship);
      }
      localStorage.setItem('saved_internships', JSON.stringify(saved));
      setIsSaved(!isSaved);
      
      // Dispatch custom events to notify other components
      window.dispatchEvent(new Event('bookmarks-changed'));
      if (onBookmarkChanged) onBookmarkChanged();
    } catch (err) {
      console.error('Error toggling save:', err);
    }
  };

  // Get color configurations depending on score
  const getScoreColors = (score: number | undefined) => {
    if (score === undefined) {
      return { bg: 'bg-slate-50 text-slate-600 border-slate-200/65', iconClass: 'text-slate-500', focus: 'focus:ring-slate-500' };
    }
    if (score >= 90) {
      return { bg: 'bg-emerald-50 text-emerald-700 border-emerald-200/65', iconClass: 'text-emerald-600', focus: 'focus:ring-emerald-500' };
    }
    if (score >= 70) {
      return { bg: 'bg-amber-50 text-amber-800 border-amber-200/65', iconClass: 'text-amber-600', focus: 'focus:ring-amber-500' };
    }
    return { bg: 'bg-rose-50 text-rose-700 border-rose-200/65', iconClass: 'text-rose-600', focus: 'focus:ring-rose-500' };
  };

  const legitColors = getScoreColors(internship.legitimacy_score);
  const matchColors = getScoreColors(internship.match_score);

  // Generate initials for logo avatar
  const getInitials = (name: string) => {
    return name
      ? name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
      : 'CO';
  };

  // Format stipend using centralized utility
  const stipendInfo = formatStipend(internship.stipend);

  const renderStipendIcon = () => {
    if (stipendInfo.currency === 'INR') {
      return <IndianRupee className="w-3.5 h-3.5 text-slate-400 shrink-0" aria-hidden="true" />;
    }
    if (stipendInfo.currency === 'USD') {
      return <DollarSign className="w-3.5 h-3.5 text-slate-400 shrink-0" aria-hidden="true" />;
    }
    return <Banknote className="w-3.5 h-3.5 text-slate-400 shrink-0" aria-hidden="true" />;
  };

  return (
    <div className="group relative bg-white border border-slate-250/70 rounded-xl p-5 hover:border-slate-350 hover:shadow-sm transition-all duration-150 flex flex-col h-full justify-between focus-within:ring-2 focus-within:ring-primary-650 focus-within:ring-offset-2">
      {/* Save Button */}
      <button
        onClick={toggleSave}
        className={`absolute top-5 right-5 p-1.5 rounded-lg border transition-colors duration-150 z-10 focus:outline-none focus:ring-2 focus:ring-primary-500 ${
          isSaved
            ? 'bg-primary-50 text-primary-600 border-primary-200'
            : 'bg-transparent text-slate-400 border-transparent hover:text-slate-600 hover:bg-slate-50'
        }`}
        aria-label={isSaved ? 'Remove from Saved' : 'Save Internship'}
        title={isSaved ? 'Remove from Saved' : 'Save Internship'}
      >
        <Bookmark className="w-4 h-4 fill-current" />
      </button>

      {/* Main card link structure */}
      <Link 
        to={`/internships/${encodeURIComponent(internship.apply_link)}`} 
        className="flex flex-col flex-grow justify-between h-full outline-none focus:outline-none"
        aria-label={`View details for ${internship.role} at ${internship.company_name}`}
      >
        <div className="space-y-3 flex-grow">
          <div className="flex items-start gap-3">
            {/* Company Logo Avatar (Minimalist box) */}
            <div className="w-10 h-10 rounded-lg flex items-center justify-center font-semibold text-slate-600 bg-slate-50 border border-slate-200 shrink-0 text-xs tracking-wider">
              {getInitials(internship.company_name)}
            </div>

            <div className="flex-1 min-w-0 pr-6">
              <h3 
                className="text-sm font-semibold text-slate-900 group-hover:text-primary-600 transition-colors line-clamp-2 min-h-[2.5rem] leading-snug" 
                title={internship.role}
              >
                {internship.role}
              </h3>
              <p className="text-xs text-slate-500 font-medium truncate mt-0.5" title={internship.company_name}>
                {internship.company_name}
              </p>
            </div>
          </div>

          {/* Details Flex Row */}
          <div className="flex flex-wrap items-center gap-y-1.5 gap-x-4 text-xs text-slate-500">
            <div className="flex items-center gap-1 truncate" title={`Location: ${internship.location || 'On-site'}`}>
              <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" aria-hidden="true" />
              <span className="truncate">{internship.location || 'On-site'}</span>
            </div>

            <div className="flex items-center gap-1 truncate" title={`Stipend: ${stipendInfo.formatted}`}>
              {renderStipendIcon()}
              <span className="font-semibold text-slate-700 truncate">{stipendInfo.formatted}</span>
            </div>

            {internship.duration && (
              <div className="flex items-center gap-1 truncate" title={`Duration: ${internship.duration}`}>
                <Calendar className="w-3.5 h-3.5 text-slate-400 shrink-0" aria-hidden="true" />
                <span className="truncate">{internship.duration}</span>
              </div>
            )}
          </div>

          {/* Dynamic Flexibility/Paid & Platform Badges */}
          <div className="flex flex-wrap gap-1">
            {internship.remote === 1 && (
              <span className="px-2 py-0.5 text-[10px] font-semibold bg-primary-50 text-primary-700 border border-primary-100 rounded">
                Remote
              </span>
            )}
            {internship.paid === 1 && (
              <span className="px-2 py-0.5 text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100 rounded">
                Paid
              </span>
            )}
            <span className="px-2 py-0.5 text-[10px] font-semibold bg-slate-50 text-slate-500 border border-slate-200/60 rounded">
              {internship.source}
            </span>
            {internship.confidence === 'MEDIUM_CONFIDENCE' || internship.confidence === 'MEDIUM' ? (
              <span className="px-2 py-0.5 text-[10px] font-semibold bg-blue-50 text-blue-700 border-blue-100 rounded">
                Potential Match
              </span>
            ) : internship.confidence === 'LOW_CONFIDENCE' || internship.confidence === 'LOW' ? (
              <span className="px-2 py-0.5 text-[10px] font-semibold bg-slate-50 text-slate-600 border-slate-200 rounded">
                Possible Match
              </span>
            ) : (
              <span className="px-2 py-0.5 text-[10px] font-semibold bg-emerald-50 text-emerald-700 border-emerald-100 rounded">
                Highly Relevant
              </span>
            )}
          </div>

          {/* Skills Chips */}
          {internship.skills_list.length > 0 && (
            <div className="flex flex-wrap items-center gap-1 pt-0.5">
              {internship.skills_list.slice(0, 3).map((skill, index) => (
                <span key={index} className="px-1.5 py-0.5 text-[10px] font-medium bg-slate-100 text-slate-650 rounded truncate max-w-[80px]" title={skill}>
                  {skill}
                </span>
              ))}
              {internship.skills_list.length > 3 && (
                <span className="text-[10px] text-slate-400 font-medium pl-0.5">
                  +{internship.skills_list.length - 3}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Footer info: Display BOTH Match & Legitimacy Scores */}
        <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs mt-4 shrink-0">
          <div className="flex flex-wrap items-center gap-1.5">
            {/* Match Score Badge */}
            <div className="relative">
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setShowMatchTooltip(!showMatchTooltip);
                  setShowLegitTooltip(false);
                }}
                onMouseEnter={() => {
                  setShowMatchTooltip(true);
                  setShowLegitTooltip(false);
                }}
                onMouseLeave={() => setShowMatchTooltip(false)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    e.stopPropagation();
                    setShowMatchTooltip(!showMatchTooltip);
                    setShowLegitTooltip(false);
                  }
                }}
                className={`text-[9px] sm:text-[10px] font-semibold px-1.5 py-0.5 rounded border transition-colors cursor-help flex items-center gap-0.5 focus:outline-none focus:ring-2 focus:ring-offset-1 ${matchColors.focus} ${matchColors.bg}`}
                aria-label="Match score detail tooltip button"
                aria-expanded={showMatchTooltip}
              >
                <span>Match Score: {internship.match_score !== undefined ? `${internship.match_score}%` : 'N/A'}</span>
                <span className="text-[8px] opacity-75">ⓘ</span>
              </button>
              
              {showMatchTooltip && (
                <div 
                  role="tooltip"
                  className="absolute bottom-full left-0 mb-2 w-52 bg-slate-900 text-white text-[10px] rounded-lg p-2.5 shadow-xl z-20 leading-relaxed font-normal animate-fade-in"
                  onClick={(e) => e.stopPropagation()}
                >
                  <p className="font-bold text-[11px] mb-1 text-primary-400">Match Score</p>
                  <p className="text-slate-300">Skill relevance. Measures how well the internship requirements match your profile and resume skills.</p>
                  <div className="absolute top-full left-4 w-2 h-2 bg-slate-900 transform rotate-45 -translate-y-1"></div>
                </div>
              )}
            </div>

            {/* Legitimacy Score Badge */}
            <div className="relative">
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setShowLegitTooltip(!showLegitTooltip);
                  setShowMatchTooltip(false);
                }}
                onMouseEnter={() => {
                  setShowLegitTooltip(true);
                  setShowMatchTooltip(false);
                }}
                onMouseLeave={() => setShowLegitTooltip(false)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    e.stopPropagation();
                    setShowLegitTooltip(!showLegitTooltip);
                    setShowMatchTooltip(false);
                  }
                }}
                className={`text-[9px] sm:text-[10px] font-semibold px-1.5 py-0.5 rounded border transition-colors cursor-help flex items-center gap-0.5 focus:outline-none focus:ring-2 focus:ring-offset-1 ${legitColors.focus} ${legitColors.bg}`}
                aria-label="Legitimacy score detail tooltip button"
                aria-expanded={showLegitTooltip}
              >
                <ShieldCheck className="w-3 h-3 shrink-0" aria-hidden="true" />
                <span>Legitimacy Score: {internship.legitimacy_score}%</span>
                <span className="text-[8px] opacity-75">ⓘ</span>
              </button>
              
              {showLegitTooltip && (
                <div 
                  role="tooltip"
                  className="absolute bottom-full left-0 mb-2 w-52 bg-slate-900 text-white text-[10px] rounded-lg p-2.5 shadow-xl z-20 leading-relaxed font-normal animate-fade-in"
                  onClick={(e) => e.stopPropagation()}
                >
                  <p className="font-bold text-[11px] mb-1 text-primary-400">Legitimacy Score</p>
                  <p className="text-slate-300">Confidence internship is genuine. Confidence listing is active, verified, and not a duplicate.</p>
                  <div className="absolute top-full left-4 w-2 h-2 bg-slate-900 transform rotate-45 -translate-y-1"></div>
                </div>
              )}
            </div>
          </div>
          
          <span className="text-[10px] font-semibold text-slate-400 inline-flex items-center gap-0.5 group-hover:text-primary-650 transition-colors">
            Details <ExternalLink className="w-2.5 h-2.5" />
          </span>
        </div>
      </Link>
    </div>
  );
}

export default React.memo(InternshipCard);

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Bookmark, MapPin, DollarSign, Calendar, ExternalLink, ShieldCheck } from 'lucide-react';
import type { Internship } from '../api';

interface InternshipCardProps {
  internship: Internship;
  onBookmarkChanged?: () => void;
}

export default function InternshipCard({ internship, onBookmarkChanged }: InternshipCardProps) {
  const [isSaved, setIsSaved] = useState(false);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('saved_internships') || '[]');
      setIsSaved(saved.some((item: Internship) => item.apply_link === internship.apply_link));
    } catch (e) {
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

  // Get color configurations depending on legitimacy score
  const getLegitimacyColors = (score: number) => {
    if (score >= 90) return { bg: 'bg-emerald-50 text-emerald-700 border-emerald-200/50', iconClass: 'text-emerald-600' };
    if (score >= 75) return { bg: 'bg-blue-50 text-blue-700 border-blue-200/50', iconClass: 'text-blue-600' };
    return { bg: 'bg-slate-50 text-slate-700 border-slate-200/60', iconClass: 'text-slate-500' };
  };

  const legitColors = getLegitimacyColors(internship.legitimacy_score);

  // Generate initials for logo avatar
  const getInitials = (name: string) => {
    return name
      ? name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
      : 'CO';
  };

  return (
    <div className="group relative bg-white border border-slate-250/70 rounded-xl p-5 hover:border-slate-350 hover:shadow-sm transition-all duration-150">
      {/* Save Button */}
      <button
        onClick={toggleSave}
        className={`absolute top-5 right-5 p-1.5 rounded-lg border transition-colors duration-150 ${
          isSaved
            ? 'bg-primary-50 text-primary-600 border-primary-200'
            : 'bg-transparent text-slate-400 border-transparent hover:text-slate-600 hover:bg-slate-50'
        }`}
        title={isSaved ? 'Remove from Saved' : 'Save Internship'}
      >
        <Bookmark className="w-4 h-4 fill-current" />
      </button>

      {/* Main card link structure */}
      <Link to={`/internships/${encodeURIComponent(internship.apply_link)}`} className="block space-y-3">
        <div className="flex items-start gap-3">
          {/* Company Logo Avatar (Minimalist box) */}
          <div className="w-10 h-10 rounded-lg flex items-center justify-center font-semibold text-slate-600 bg-slate-50 border border-slate-200 shrink-0 text-xs tracking-wider">
            {getInitials(internship.company_name)}
          </div>

          <div className="flex-1 min-w-0 pr-6">
            <h3 className="text-sm font-semibold text-slate-900 group-hover:text-primary-600 transition-colors truncate">
              {internship.role}
            </h3>
            <p className="text-xs text-slate-500 font-medium truncate mt-0.5">
              {internship.company_name}
            </p>
          </div>
        </div>

        {/* Details Flex Row */}
        <div className="flex flex-wrap items-center gap-y-1.5 gap-x-4 text-xs text-slate-500">
          <div className="flex items-center gap-1 truncate">
            <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span className="truncate">{internship.location || 'On-site'}</span>
          </div>

          <div className="flex items-center gap-1 truncate">
            <DollarSign className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span className="font-semibold text-slate-700 truncate">{internship.stipend || 'Unspecified'}</span>
          </div>

          {internship.duration && (
            <div className="flex items-center gap-1 truncate">
              <Calendar className="w-3.5 h-3.5 text-slate-400 shrink-0" />
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
          {internship.confidence === 'MEDIUM' ? (
            <span className="px-2 py-0.5 text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-100 rounded">
              Potential Match
            </span>
          ) : internship.confidence === 'LOW' ? (
            <span className="px-2 py-0.5 text-[10px] font-semibold bg-slate-50 text-slate-600 border border-slate-200 rounded">
              Possible Match
            </span>
          ) : (
            <span className="px-2 py-0.5 text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100 rounded">
              Highly Relevant
            </span>
          )}
        </div>

        {/* Skills Chips */}
        {internship.skills_list.length > 0 && (
          <div className="flex flex-wrap items-center gap-1 pt-0.5">
            {internship.skills_list.slice(0, 3).map((skill, index) => (
              <span key={index} className="px-1.5 py-0.5 text-[10px] font-medium bg-slate-100 text-slate-600 rounded">
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

        {/* Footer info: Legitimacy Score Check */}
        <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className={`w-3.5 h-3.5 ${legitColors.iconClass}`} />
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${legitColors.bg}`}>
              {internship.legitimacy_score}% Match
            </span>
          </div>
          
          <span className="text-[10px] font-semibold text-slate-400 inline-flex items-center gap-0.5 group-hover:text-primary-600 transition-colors">
            Details <ExternalLink className="w-2.5 h-2.5" />
          </span>
        </div>
      </Link>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Search, SlidersHorizontal, Shield, RotateCcw, ChevronLeft, ChevronRight, Check, X } from 'lucide-react';
import { fetchInternships } from '../api';
import InternshipCard from '../components/InternshipCard';

function getPaginationPages(currentPage: number, totalPages: number): (number | string)[] {
  const pages: (number | string)[] = [];
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) {
      pages.push(i);
    }
    return pages;
  }
  
  pages.push(1);
  const leftRange = Math.max(2, currentPage - 1);
  const rightRange = Math.min(totalPages - 1, currentPage + 1);
  
  if (leftRange > 2) {
    pages.push('...');
  }
  
  for (let i = leftRange; i <= rightRange; i++) {
    pages.push(i);
  }
  
  if (rightRange < totalPages - 1) {
    pages.push('...');
  }
  
  pages.push(totalPages);
  return pages;
}

export default function ExplorePage() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Parse all query params from URL
  const search = searchParams.get('search') || '';
  const selectedLocations = searchParams.get('location') ? searchParams.get('location')!.split(',') : [];
  const remote = searchParams.get('remote') || '';
  const selectedDurations = searchParams.get('duration') ? searchParams.get('duration')!.split(',') : [];
  const selectedSkills = searchParams.get('skills') ? searchParams.get('skills')!.split(',') : [];
  const selectedSources = searchParams.get('source') ? searchParams.get('source')!.split(',') : [];
  const stipendMin = searchParams.get('stipendMin') || '0';
  const stipendMax = searchParams.get('stipendMax') || '';
  const legitimacyMin = searchParams.get('legitimacyMin') || '60';
  const datePosted = searchParams.get('datePosted') || '';
  const sort = searchParams.get('sort') || 'newest';
  const page = searchParams.get('page') || '1';

  // Debounce state
  const [localSearch, setLocalSearch] = useState(search);
  const [showMobileFilters, setShowMobileFilters] = useState(false);

  // Local state for sliders to prevent drag query lag
  const [localStipendMin, setLocalStipendMin] = useState(stipendMin);
  const [localStipendMax, setLocalStipendMax] = useState(stipendMax || '60000');
  const [localLegitimacyMin, setLocalLegitimacyMin] = useState(legitimacyMin);

  // Sync local states when query parameters change externally
  useEffect(() => {
    setLocalStipendMin(stipendMin);
  }, [stipendMin]);

  useEffect(() => {
    setLocalStipendMax(stipendMax || '60000');
  }, [stipendMax]);

  useEffect(() => {
    setLocalLegitimacyMin(legitimacyMin);
  }, [legitimacyMin]);

  // Sync local search input when URL search param changes
  useEffect(() => {
    setLocalSearch(search);
  }, [search]);

  // Debounce search update
  useEffect(() => {
    const timer = setTimeout(() => {
      if (localSearch !== search) {
        updateQueryParams({
          search: localSearch || null,
          page: '1'
        });
      }
    }, 450);
    return () => clearTimeout(timer);
  }, [localSearch]);

  // Premium feature: Resume Matching State
  const [resumeText, setResumeText] = useState('');
  const [resumeSkillsMatched, setResumeSkillsMatched] = useState<string[]>([]);
  const [isMatchingResume, setIsMatchingResume] = useState(false);

  // Premium feature: Alerts Modal State
  const [showAlertModal, setShowAlertModal] = useState(false);
  const [alertEmail, setAlertEmail] = useState('');
  const [alertSuccess, setAlertSuccess] = useState(false);

  // Premium feature: AI Recommendations State
  const [aiRecommendations, setAiRecommendations] = useState<any[]>([]);

  // Filter checklists
  const standardSkills = ['Python', 'SQL', 'Power BI', 'Excel', 'Tableau', 'Machine Learning', 'Statistics', 'Pandas', 'Data Visualization'];
  const locationsList = ['Bangalore', 'Mumbai', 'Delhi', 'Hyderabad', 'Pune', 'Chennai'];
  const sourcesList = ['Internshala', 'LinkedIn', 'Wellfound', 'Indeed', 'Company Website'];
  const durationsList = [
    { value: '1', label: '1 Month' },
    { value: '2', label: '2 Months' },
    { value: '3', label: '3 Months' },
    { value: '6', label: '6 Months' },
    { value: '6+', label: '6+ Months' }
  ];


  const handleResumeMatch = () => {
    if (!resumeText.trim()) return;
    setIsMatchingResume(true);
    
    // Simulate smart matching extraction
    setTimeout(() => {
      const text = resumeText.toLowerCase();
      const matched = standardSkills.filter(skill => {
        const sLower = skill.toLowerCase();
        const regex = new RegExp(`\\b${sLower}\\b`, 'i');
        return regex.test(text) || text.includes(sLower);
      });
      
      setResumeSkillsMatched(matched);
      setIsMatchingResume(false);
      
      if (matched.length > 0) {
        updateQueryParams({
          skills: matched.map(s => s.toLowerCase()).join(','),
          page: '1'
        });
      } else {
        alert("No core analytical skills found in the resume. We scanned for skills like Python, SQL, Excel, and Power BI. Please paste more detailed skills!");
      }
    }, 800);
  };

  const handleCreateAlertSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!alertEmail.trim()) return;
    
    // Store mock alert subscription
    try {
      const alerts = JSON.parse(localStorage.getItem('internship_alerts') || '[]');
      alerts.push({
        email: alertEmail,
        search,
        skills: selectedSkills,
        location: selectedLocations,
        created_at: new Date().toISOString()
      });
      localStorage.setItem('internship_alerts', JSON.stringify(alerts));
      
      setAlertSuccess(true);
      setTimeout(() => {
        setAlertSuccess(false);
        setShowAlertModal(false);
        setAlertEmail('');
      }, 1800);
    } catch (err) {
      console.error(err);
    }
  };

  // Prepare full query params for API request
  const queryParams = {
    search,
    location: selectedLocations.join(','),
    remote,
    duration: selectedDurations.join(','),
    skills: selectedSkills.join(','),
    source: selectedSources.join(','),
    stipendMin,
    stipendMax,
    legitimacyMin,
    sort,
    datePosted,
    page,
    limit: '8'
  };

  // Fetch listings from backend
  const { data: listingsData, isLoading, isError, refetch } = useQuery({
    queryKey: ['internships', queryParams],
    queryFn: () => fetchInternships(queryParams),
    placeholderData: (prev) => prev
  });

  // AI Recommendations logic: recommend jobs sharing skills with user's bookmarks
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('saved_internships') || '[]');
      if (saved.length > 0 && listingsData?.internships) {
        const savedSkills = saved.flatMap((i: any) => i.skills_list || []).map((s: string) => s.toLowerCase());
        const savedLinks = saved.map((i: any) => i.apply_link);
        
        // Find listings matching saved skills, excluding already saved
        const recs = listingsData.internships.filter((item: any) => {
          if (savedLinks.includes(item.apply_link)) return false;
          return item.skills_list.some((s: string) => savedSkills.includes(s.toLowerCase()));
        }).slice(0, 3);
        
        setAiRecommendations(recs);
      } else {
        setAiRecommendations([]);
      }
    } catch (e) {
      setAiRecommendations([]);
    }
  }, [listingsData, showAlertModal]); // update recommendations when page loads/updates

  // Helper to update query parameters in URL
  const updateQueryParams = (updates: Record<string, string | null>) => {
    const params = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value === null || value === '' || value === 'false') {
        params.delete(key);
      } else {
        params.set(key, value);
      }
    });
    setSearchParams(params);
  };

  // Helper to toggle array filter values
  const toggleArrayFilter = (key: string, list: string[], value: string) => {
    const index = list.indexOf(value);
    let newList = [...list];
    if (index > -1) {
      newList.splice(index, 1);
    } else {
      newList.push(value);
    }
    updateQueryParams({
      [key]: newList.length > 0 ? newList.join(',') : null,
      page: '1'
    });
  };

  const resetAllFilters = () => {
    setSearchParams(new URLSearchParams());
    setLocalSearch('');
    setLocalStipendMin('0');
    setLocalStipendMax('60000');
    setLocalLegitimacyMin('60');
    setResumeText('');
    setResumeSkillsMatched([]);
  };

  // Helper to remove a single active filter chip
  const removeFilterChip = (key: string, value?: string) => {
    const updates: Record<string, string | null> = { page: '1' };

    if (key === 'search') {
      setLocalSearch('');
      updates['search'] = null;
    } else if (key === 'remote') {
      updates['remote'] = null;
    } else if (key === 'stipendMin') {
      setLocalStipendMin('0');
      updates['stipendMin'] = null;
    } else if (key === 'stipendMax') {
      setLocalStipendMax('60000');
      updates['stipendMax'] = null;
    } else if (key === 'legitimacyMin') {
      setLocalLegitimacyMin('60');
      updates['legitimacyMin'] = null;
    } else if (key === 'datePosted') {
      updates['datePosted'] = null;
    } else if (value) {
      const currentList = searchParams.get(key) ? searchParams.get(key)!.split(',') : [];
      const updatedList = currentList.filter(item => item !== value);
      updates[key] = updatedList.length > 0 ? updatedList.join(',') : null;
    }

    updateQueryParams(updates);
  };

  // Check if any filters are active
  const hasActiveFilters = 
    search || 
    selectedLocations.length > 0 || 
    remote || 
    selectedDurations.length > 0 || 
    selectedSkills.length > 0 || 
    selectedSources.length > 0 || 
    stipendMin !== '0' || 
    stipendMax || 
    legitimacyMin !== '60' || 
    datePosted;

  return (
    <div className="space-y-4">
      
      {/* Search & Header Section */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 bg-white border border-slate-200 rounded-xl p-3.5 shadow-sm">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-3 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search role, company, or skills..."
            value={localSearch}
            onChange={(e) => setLocalSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-205 rounded-lg outline-none focus:border-primary-400 focus:bg-white text-sm transition-all"
          />
        </div>
        
        <div className="flex items-center gap-2">
          {/* Mobile Filter Button */}
          <button
            onClick={() => setShowMobileFilters(!showMobileFilters)}
            className="md:hidden flex items-center justify-center gap-1.5 px-4 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-700 font-semibold text-sm hover:bg-slate-50 cursor-pointer"
          >
            <SlidersHorizontal className="w-4 h-4" />
            <span>Filters</span>
          </button>

          {/* Sort Dropdown */}
          <select
            value={sort}
            onChange={(e) => {
              updateQueryParams({
                sort: e.target.value,
                page: '1'
              });
            }}
            className="px-3.5 py-2.5 bg-white border border-slate-205 rounded-lg text-slate-700 font-medium text-sm outline-none cursor-pointer hover:bg-slate-50 transition-colors"
          >
            <option value="newest">Newest First</option>
            <option value="stipend">Highest Stipend</option>
            <option value="legitimacy">Highest Legitimacy</option>
            <option value="recently_added">Recently Added</option>
          </select>
          
          {/* Reset Filters */}
          <button
            onClick={resetAllFilters}
            className="p-2.5 bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-500 rounded-lg hover:text-slate-800 transition-colors cursor-pointer"
            title="Reset All Filters"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Active Filters Bar */}
      {hasActiveFilters && (
        <div className="flex flex-wrap items-center gap-1.5 p-3 bg-slate-50 border border-slate-200/80 rounded-lg text-xs text-slate-660 font-medium">
          <span className="text-slate-400 font-semibold mr-1">Active filters:</span>
          
          {search && (
            <span className="inline-flex items-center gap-1 bg-white border border-slate-200 text-slate-700 px-2 py-0.5 rounded-md">
              Search: "{search}"
              <button onClick={() => removeFilterChip('search')} className="text-slate-400 hover:text-slate-600 cursor-pointer">
                <X className="w-3 h-3" />
              </button>
            </span>
          )}

          {selectedLocations.map(loc => (
            <span key={loc} className="inline-flex items-center gap-1 bg-white border border-slate-200 text-slate-700 px-2 py-0.5 rounded-md uppercase text-[9px] tracking-wide font-bold">
              {loc}
              <button onClick={() => removeFilterChip('location', loc)} className="text-slate-400 hover:text-slate-600 cursor-pointer">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}

          {remote && (
            <span className="inline-flex items-center gap-1 bg-white border border-slate-200 text-slate-700 px-2 py-0.5 rounded-md capitalize">
              Type: {remote}
              <button onClick={() => removeFilterChip('remote')} className="text-slate-400 hover:text-slate-600 cursor-pointer">
                <X className="w-3 h-3" />
              </button>
            </span>
          )}

          {selectedDurations.map(dur => (
            <span key={dur} className="inline-flex items-center gap-1 bg-white border border-slate-200 text-slate-700 px-2 py-0.5 rounded-md">
              {dur === '6+' ? '6+ Months' : `${dur} Month${dur !== '1' ? 's' : ''}`}
              <button onClick={() => removeFilterChip('duration', dur)} className="text-slate-400 hover:text-slate-600 cursor-pointer">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}

          {selectedSkills.map(skill => (
            <span key={skill} className="inline-flex items-center gap-1 bg-white border border-slate-200 text-slate-700 px-2 py-0.5 rounded-md">
              Skill: {skill}
              <button onClick={() => removeFilterChip('skills', skill)} className="text-slate-400 hover:text-slate-600 cursor-pointer">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}

          {selectedSources.map(src => (
            <span key={src} className="inline-flex items-center gap-1 bg-white border border-slate-200 text-slate-700 px-2 py-0.5 rounded-md">
              {src}
              <button onClick={() => removeFilterChip('source', src)} className="text-slate-400 hover:text-slate-600 cursor-pointer">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}

          {stipendMin !== '0' && (
            <span className="inline-flex items-center gap-1 bg-white border border-slate-200 text-slate-700 px-2 py-0.5 rounded-md">
              Min Stipend: ₹{parseInt(stipendMin).toLocaleString()}
              <button onClick={() => removeFilterChip('stipendMin')} className="text-slate-400 hover:text-slate-600 cursor-pointer">
                <X className="w-3 h-3" />
              </button>
            </span>
          )}

          {stipendMax && (
            <span className="inline-flex items-center gap-1 bg-white border border-slate-200 text-slate-700 px-2 py-0.5 rounded-md">
              Max Stipend: ₹{parseInt(stipendMax).toLocaleString()}
              <button onClick={() => removeFilterChip('stipendMax')} className="text-slate-400 hover:text-slate-600 cursor-pointer">
                <X className="w-3 h-3" />
              </button>
            </span>
          )}

          {legitimacyMin !== '60' && (
            <span className="inline-flex items-center gap-1 bg-white border border-slate-200 text-slate-700 px-2 py-0.5 rounded-md">
              Legitimacy Score &ge; {legitimacyMin}%
              <button onClick={() => removeFilterChip('legitimacyMin')} className="text-slate-400 hover:text-slate-600 cursor-pointer">
                <X className="w-3 h-3" />
              </button>
            </span>
          )}

          {datePosted && (
            <span className="inline-flex items-center gap-1 bg-white border border-slate-200 text-slate-700 px-2 py-0.5 rounded-md">
              Posted: {datePosted === 'today' ? 'Today' : datePosted === '3days' ? 'Last 3 Days' : datePosted === '7days' ? 'Last 7 Days' : 'Last 30 Days'}
              <button onClick={() => removeFilterChip('datePosted')} className="text-slate-400 hover:text-slate-600 cursor-pointer">
                <X className="w-3 h-3" />
              </button>
            </span>
          )}

          <button onClick={resetAllFilters} className="ml-auto text-primary-600 hover:underline hover:text-primary-800 font-bold text-[10px] tracking-tight cursor-pointer">
            Clear all filters
          </button>
        </div>
      )}

      {/* Main Board Layout */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-start">
        
        {/* Left Filters Sidebar - Desktop */}
        <aside className="hidden md:block bg-white border border-slate-200 rounded-xl p-5 shadow-sm sticky top-20 max-h-[85vh] overflow-y-auto space-y-6">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 className="font-bold text-slate-800 text-xs flex items-center gap-1.5">
              <SlidersHorizontal className="w-4 h-4 text-primary-600" />
              <span>Filters</span>
            </h3>
            <button onClick={resetAllFilters} className="text-xs text-primary-600 hover:text-primary-850 font-semibold transition-colors cursor-pointer">
              Clear all
            </button>
          </div>

          {/* Internship Alerts Button */}
          <button
            onClick={() => setShowAlertModal(true)}
            className="w-full py-2 bg-slate-905 hover:bg-slate-900 text-white font-bold rounded-lg text-xs transition-all duration-150 shadow-sm cursor-pointer flex items-center justify-center gap-1.5 border border-slate-900 hover:border-slate-800"
          >
            <span>🔔 Create Alert</span>
          </button>

          {/* AI Resume Matcher */}
          <div className="space-y-2 border-t border-slate-100 pt-4">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400">AI Resume Matcher</h4>
              {resumeSkillsMatched.length > 0 && (
                <span className="text-[9px] bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold px-1.5 py-0.5 rounded">
                  {resumeSkillsMatched.length} matched
                </span>
              )}
            </div>
            <textarea
              placeholder="Paste resume skills or summary here..."
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
              className="w-full h-20 p-2 bg-slate-50 border border-slate-200 rounded-lg text-[11px] outline-none focus:border-primary-400 focus:bg-white resize-none"
            />
            <button
              onClick={handleResumeMatch}
              disabled={isMatchingResume || !resumeText.trim()}
              className="w-full py-1.5 bg-primary-600 hover:bg-primary-700 disabled:bg-slate-200 disabled:text-slate-400 text-white font-bold rounded-lg text-xs transition-colors shadow-sm cursor-pointer"
            >
              {isMatchingResume ? 'Matching Resume...' : 'Match Resume'}
            </button>
          </div>

          {/* Remote Type */}
          <div className="space-y-2.5 border-t border-slate-100 pt-4">
            <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400">Remote Type</h4>
            <div className="flex flex-col gap-1.5">
              {[
                { value: '', label: 'All Positions' },
                { value: 'remote', label: 'Remote' },
                { value: 'onsite', label: 'On-site' },
                { value: 'hybrid', label: 'Hybrid' }
              ].map(opt => {
                const id = `remote-${opt.value || 'all'}`;
                return (
                  <label key={opt.value} htmlFor={id} className="flex items-center gap-2 text-xs text-slate-650 hover:text-slate-900 cursor-pointer font-medium">
                    <input
                      id={id}
                      type="radio"
                      name="remoteOpt"
                      checked={remote === opt.value}
                      onChange={() => {
                        updateQueryParams({
                          remote: opt.value || null,
                          page: '1'
                        });
                      }}
                      className="w-3.5 h-3.5 text-primary-600 border-slate-350 focus:ring-primary-500/20"
                    />
                    <span>{opt.label}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Locations Checklist */}
          <div className="space-y-2.5 border-t border-slate-100 pt-4">
            <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400">Locations</h4>
            <div className="max-h-32 overflow-y-auto space-y-1.5 pr-1">
              {locationsList.map((loc) => {
                const id = `loc-${loc.toLowerCase()}`;
                return (
                  <label key={loc} htmlFor={id} className="flex items-center gap-2 text-xs text-slate-650 hover:text-slate-900 cursor-pointer font-medium">
                    <input
                      id={id}
                      type="checkbox"
                      checked={selectedLocations.includes(loc.toLowerCase())}
                      onChange={() => toggleArrayFilter('location', selectedLocations, loc.toLowerCase())}
                      className="w-3.5 h-3.5 rounded text-primary-600 border-slate-350 focus:ring-primary-500/20"
                    />
                    <span>{loc}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Minimum Stipend */}
          <div className="space-y-2 border-t border-slate-100 pt-4">
            <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400">
              <label htmlFor="stipend-min-slider" className="cursor-pointer">Min Stipend (₹/mo)</label>
              <span className="text-slate-755 text-xs font-extrabold bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                {localStipendMin === '0' ? 'Any' : `₹${parseInt(localStipendMin).toLocaleString()}`}
              </span>
            </div>
            <input
              id="stipend-min-slider"
              type="range"
              min="0"
              max="40000"
              step="2500"
              value={localStipendMin}
              onChange={(e) => setLocalStipendMin(e.target.value)}
              onMouseUp={() => updateQueryParams({ stipendMin: localStipendMin === '0' ? null : localStipendMin, page: '1' })}
              onTouchEnd={() => updateQueryParams({ stipendMin: localStipendMin === '0' ? null : localStipendMin, page: '1' })}
              className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
            />
          </div>

          {/* Maximum Stipend */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400">
              <label htmlFor="stipend-max-slider" className="cursor-pointer">Max Stipend (₹/mo)</label>
              <span className="text-slate-755 text-xs font-extrabold bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                {localStipendMax === '60000' ? 'No Limit' : `₹${parseInt(localStipendMax).toLocaleString()}`}
              </span>
            </div>
            <input
              id="stipend-max-slider"
              type="range"
              min="5000"
              max="60000"
              step="5000"
              value={localStipendMax}
              onChange={(e) => setLocalStipendMax(e.target.value)}
              onMouseUp={() => updateQueryParams({ stipendMax: localStipendMax === '60000' ? null : localStipendMax, page: '1' })}
              onTouchEnd={() => updateQueryParams({ stipendMax: localStipendMax === '60000' ? null : localStipendMax, page: '1' })}
              className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
            />
          </div>

          {/* Durations */}
          <div className="space-y-2.5 border-t border-slate-100 pt-4">
            <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400">Duration</h4>
            <div className="space-y-1.5">
              {durationsList.map((dur) => {
                const id = `dur-${dur.value.replace('+', 'plus')}`;
                return (
                  <label key={dur.value} htmlFor={id} className="flex items-center gap-2 text-xs text-slate-650 hover:text-slate-900 cursor-pointer font-medium">
                    <input
                      id={id}
                      type="checkbox"
                      checked={selectedDurations.includes(dur.value)}
                      onChange={() => toggleArrayFilter('duration', selectedDurations, dur.value)}
                      className="w-3.5 h-3.5 rounded text-primary-600 border-slate-350 focus:ring-primary-500/20"
                    />
                    <span>{dur.label}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Core Skills */}
          <div className="space-y-3 border-t border-slate-100 pt-4">
            <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400 font-sans">Core Skills</h4>
            <div className="flex flex-wrap gap-1.5">
              {standardSkills.map((skill) => {
                const sLower = skill.toLowerCase();
                const isSelected = selectedSkills.includes(sLower);
                return (
                  <button
                    key={skill}
                    onClick={() => toggleArrayFilter('skills', selectedSkills, sLower)}
                    className={`px-2.5 py-1.5 text-[10px] font-semibold rounded-lg border transition-all duration-205 ease-in-out cursor-pointer ${
                      isSelected
                        ? 'bg-primary-600 text-white border-primary-600 shadow-sm ring-2 ring-primary-500/20'
                        : 'bg-slate-50 text-slate-600 border-slate-300 hover:bg-slate-100 hover:border-slate-400 hover:text-slate-900'
                    }`}
                  >
                    {skill}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Sources Platforms */}
          <div className="space-y-2.5 border-t border-slate-100 pt-4">
            <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400">Platform</h4>
            <div className="space-y-1.5">
              {sourcesList.map((src) => {
                const id = `source-${src.toLowerCase().replace(' ', '-')}`;
                return (
                  <label key={src} htmlFor={id} className="flex items-center gap-2 text-xs text-slate-650 hover:text-slate-900 cursor-pointer font-medium">
                    <input
                      id={id}
                      type="checkbox"
                      checked={selectedSources.includes(src.toLowerCase())}
                      onChange={() => toggleArrayFilter('source', selectedSources, src.toLowerCase())}
                      className="w-3.5 h-3.5 rounded text-primary-600 border-slate-350 focus:ring-primary-500/20"
                    />
                    <span>{src}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Minimum Legitimacy */}
          <div className="space-y-2 border-t border-slate-100 pt-4">
            <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400">
              <label htmlFor="legitimacy-min-slider" className="cursor-pointer">Min Legitimacy Score</label>
              <span className="text-slate-755 text-xs font-extrabold bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                {localLegitimacyMin}% Match
              </span>
            </div>
            <input
              id="legitimacy-min-slider"
              type="range"
              min="60"
              max="100"
              step="5"
              value={localLegitimacyMin}
              onChange={(e) => setLocalLegitimacyMin(e.target.value)}
              onMouseUp={() => updateQueryParams({ legitimacyMin: localLegitimacyMin === '60' ? null : localLegitimacyMin, page: '1' })}
              onTouchEnd={() => updateQueryParams({ legitimacyMin: localLegitimacyMin === '60' ? null : localLegitimacyMin, page: '1' })}
              className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
            />
          </div>

          {/* Date Posted */}
          <div className="space-y-2.5 border-t border-slate-100 pt-4">
            <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400">Date Posted</h4>
            <div className="space-y-1.5">
              {[
                { value: '', label: 'Anytime' },
                { value: 'today', label: 'Today (Past 24h)' },
                { value: '3days', label: 'Past 3 Days' },
                { value: '7days', label: 'Past Week' },
                { value: '30days', label: 'Past Month' }
              ].map(opt => {
                const id = `posted-${opt.value || 'anytime'}`;
                return (
                  <label key={opt.value} htmlFor={id} className="flex items-center gap-2 text-xs text-slate-650 hover:text-slate-900 cursor-pointer font-medium">
                    <input
                      id={id}
                      type="radio"
                      name="datePostedOpt"
                      checked={datePosted === opt.value}
                      onChange={() => {
                        updateQueryParams({
                          datePosted: opt.value || null,
                          page: '1'
                        });
                      }}
                      className="w-3.5 h-3.5 text-primary-600 border-slate-350 focus:ring-primary-500/20"
                    />
                    <span>{opt.label}</span>
                  </label>
                );
              })}
            </div>
          </div>
        </aside>

        {/* Right Listings Board */}
        <div className="md:col-span-3 space-y-4">
          
          {/* Results count summary */}
          <div className="flex items-center justify-between text-xs text-slate-550 px-1">
            <span>
              {isLoading ? (
                'Loading internships...'
              ) : (
                <>
                  Found <strong className="text-slate-850 font-bold">{listingsData?.total || 0}</strong> internships
                  {search && <span> for "<span className="text-primary-600 font-semibold">{search}</span>"</span>}
                </>
              )}
            </span>
          </div>

          {/* AI Recommended Listings */}
          {aiRecommendations.length > 0 && (
            <div className="bg-gradient-to-r from-primary-50/40 via-emerald-50/20 to-blue-50/10 border border-primary-100/60 rounded-xl p-5 space-y-3.5 shadow-sm animate-fade-in">
              <h3 className="font-extrabold text-slate-800 text-xs tracking-wider uppercase flex items-center gap-1.5">
                <span>✨ Recommended For You</span>
                <span className="text-[10px] text-slate-400 font-semibold normal-case">(Based on bookmark history)</span>
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {aiRecommendations.map((internship) => (
                  <InternshipCard key={`rec-${internship.apply_link}`} internship={internship} />
                ))}
              </div>
            </div>
          )}

          {/* Listings Grid */}
          {isLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="bg-white border border-slate-205 rounded-xl p-5 space-y-4 shadow-sm animate-pulse">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-lg bg-slate-100 shrink-0"></div>
                    <div className="flex-1 space-y-2 pt-1">
                      <div className="h-3 w-1/3 bg-slate-100 rounded"></div>
                      <div className="h-4 w-3/4 bg-slate-100 rounded"></div>
                    </div>
                  </div>
                  <div className="h-3.5 w-5/6 bg-slate-100 rounded"></div>
                  <div className="h-3 w-2/3 bg-slate-100 rounded"></div>
                  <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                    <div className="h-4 w-1/4 bg-slate-100 rounded"></div>
                    <div className="h-3 w-1/5 bg-slate-100 rounded"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : isError ? (
            <div className="bg-red-50 border border-red-100 text-red-700 p-8 rounded-xl text-center space-y-3">
              <Shield className="w-10 h-10 mx-auto text-red-500" />
              <h3 className="font-bold text-sm">Failed to load listings</h3>
              <p className="text-xs text-red-655">
                Ensure the local Node.js backend is running.
              </p>
              <button
                onClick={() => refetch()}
                className="px-4 py-2 bg-red-600 text-white rounded-lg text-xs font-semibold hover:bg-red-700 shadow-sm transition-colors cursor-pointer"
              >
                Retry Request
              </button>
            </div>
          ) : !listingsData || listingsData.internships.length === 0 ? (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center space-y-4 shadow-sm max-w-md mx-auto mt-6">
              <Search className="w-10 h-10 mx-auto text-slate-350" />
              <h3 className="font-bold text-base text-slate-800">No internships found</h3>
              <p className="text-slate-500 text-xs max-w-xs mx-auto leading-relaxed">
                We couldn't find any opportunities matching your filters. Try clearing some tags, reducing minimum stipend, or resetting filters.
              </p>
              <button
                onClick={resetAllFilters}
                className="px-4 py-2 bg-primary-600 text-white font-bold rounded-lg text-xs hover:bg-primary-700 shadow-sm transition-colors cursor-pointer"
              >
                Clear All Filters
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {listingsData.internships.map((internship) => (
                <InternshipCard key={internship.apply_link} internship={internship} />
              ))}
            </div>
          )}

          {/* Pagination Row */}
          {listingsData && listingsData.totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-slate-200 pt-6 mt-8 px-1">
              <button
                disabled={listingsData.page <= 1}
                onClick={() => updateQueryParams({ page: (listingsData.page - 1).toString() })}
                className="flex items-center gap-1 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-700 text-xs font-semibold hover:bg-slate-50 disabled:opacity-50 disabled:hover:bg-white disabled:cursor-not-allowed transition-colors cursor-pointer"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Prev</span>
              </button>
              
              <div className="hidden sm:flex items-center gap-1 text-xs font-semibold text-slate-500">
                {getPaginationPages(listingsData.page, listingsData.totalPages).map((pNum, index) => {
                  if (pNum === '...') {
                    return (
                      <span key={`ellipse-${index}`} className="w-8 h-8 flex items-center justify-center text-slate-400">
                        ...
                      </span>
                    );
                  }
                  const isCurrent = listingsData.page === pNum;
                  return (
                    <button
                      key={`page-${pNum}`}
                      onClick={() => updateQueryParams({ page: pNum.toString() })}
                      className={`w-8 h-8 rounded-lg flex items-center justify-center border transition-all cursor-pointer ${
                        isCurrent
                          ? 'bg-primary-600 text-white border-primary-600 shadow-sm'
                          : 'bg-white border-slate-200 text-slate-655 hover:bg-slate-50'
                      }`}
                    >
                      {pNum}
                    </button>
                  );
                })}
              </div>

              <div className="sm:hidden text-xs font-semibold text-slate-500">
                Page {listingsData.page} of {listingsData.totalPages}
              </div>

              <button
                disabled={listingsData.page >= listingsData.totalPages}
                onClick={() => updateQueryParams({ page: (listingsData.page + 1).toString() })}
                className="flex items-center gap-1 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-700 text-xs font-semibold hover:bg-slate-50 disabled:opacity-50 disabled:hover:bg-white disabled:cursor-not-allowed transition-colors cursor-pointer"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

        </div>
      </div>

      {/* Alerts Modal Popup */}
      {showAlertModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center animate-fade-in">
          <div onClick={() => setShowAlertModal(false)} className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-all"></div>
          <div className="relative bg-white rounded-xl p-6 shadow-xl border border-slate-200 max-w-md w-full mx-4 space-y-4 z-10 animate-scale-in">
            <button onClick={() => setShowAlertModal(false)} className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 cursor-pointer">
              <X className="w-4 h-4" />
            </button>
            <div className="text-center space-y-1 pt-2">
              <h3 className="font-bold text-base text-slate-900 flex items-center justify-center gap-1.5">
                <span>🔔 Create Internship Alert</span>
              </h3>
              <p className="text-xs text-slate-500 max-w-xs mx-auto leading-relaxed">
                Stay updated with jobs matching your current search options:
              </p>
            </div>
            
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs space-y-1.5 text-slate-650 font-medium">
              {search && <div>• Keywords: <span className="font-semibold text-slate-800">"{search}"</span></div>}
              {selectedSkills.length > 0 && <div>• Required Skills: <span className="font-semibold text-slate-800">{selectedSkills.join(', ')}</span></div>}
              {selectedLocations.length > 0 && <div>• Locations: <span className="font-semibold text-slate-800">{selectedLocations.join(', ')}</span></div>}
              {remote && <div>• Type: <span className="font-semibold text-slate-800">{remote}</span></div>}
              {!search && selectedSkills.length === 0 && selectedLocations.length === 0 && !remote && (
                <div>• All new analytical internships</div>
              )}
            </div>
            
            {alertSuccess ? (
              <div className="bg-emerald-50 border border-emerald-100 text-emerald-800 p-4 rounded-lg text-center font-bold text-xs animate-fade-in flex items-center justify-center gap-1.5">
                <Check className="w-4 h-4 text-emerald-600" />
                <span>Alert setup completed successfully!</span>
              </div>
            ) : (
              <form onSubmit={handleCreateAlertSubmit} className="space-y-3">
                <input
                  type="email"
                  required
                  placeholder="Enter your email address"
                  value={alertEmail}
                  onChange={(e) => setAlertEmail(e.target.value)}
                  className="w-full px-3.5 py-2 bg-slate-50 border border-slate-205 rounded-lg outline-none focus:border-primary-400 focus:bg-white text-xs"
                />
                <button
                  type="submit"
                  className="w-full py-2 bg-primary-600 hover:bg-primary-700 text-white font-bold rounded-lg text-xs transition-colors shadow-sm cursor-pointer"
                >
                  Subscribe to Alerts
                </button>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Slide-out Mobile Filters Overlay */}
      {showMobileFilters && (
        <div className="fixed inset-0 z-50 md:hidden flex justify-end">
          {/* Overlay background */}
          <div
            onClick={() => setShowMobileFilters(false)}
            className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-all"
          ></div>
          
          {/* Filter container */}
          <div className="relative w-72 max-w-[90vw] h-full bg-white shadow-xl flex flex-col p-5 space-y-4.5 overflow-y-auto animate-slide-in">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-800 text-sm">Mobile Filters</h3>
              <button
                onClick={() => setShowMobileFilters(false)}
                className="p-1 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 cursor-pointer"
              >
                <Check className="w-4 h-4" />
              </button>
            </div>

            {/* Remote Type */}
            <div className="space-y-2">
              <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400">Remote Type</h4>
              <div className="flex flex-col gap-1.5">
                {[
                  { value: '', label: 'All Positions' },
                  { value: 'remote', label: 'Remote' },
                  { value: 'onsite', label: 'On-site' },
                  { value: 'hybrid', label: 'Hybrid' }
                ].map(opt => {
                  const id = `mobile-remote-${opt.value || 'all'}`;
                  return (
                    <label key={opt.value} htmlFor={id} className="flex items-center gap-2 text-xs text-slate-650 hover:text-slate-900 cursor-pointer font-medium">
                      <input
                        id={id}
                        type="radio"
                        name="mobileRemoteOpt"
                        checked={remote === opt.value}
                        onChange={() => updateQueryParams({ remote: opt.value || null, page: '1' })}
                        className="w-3.5 h-3.5 text-primary-600 border-slate-350"
                      />
                      <span>{opt.label}</span>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Locations */}
            <div className="space-y-2 border-t border-slate-100 pt-3">
              <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400">Locations</h4>
              <div className="max-h-32 overflow-y-auto space-y-1.5 pr-1">
                {locationsList.map((loc) => {
                  const id = `mobile-loc-${loc.toLowerCase()}`;
                  return (
                    <label key={loc} htmlFor={id} className="flex items-center gap-2 text-xs text-slate-650 hover:text-slate-900 cursor-pointer font-medium">
                      <input
                        id={id}
                        type="checkbox"
                        checked={selectedLocations.includes(loc.toLowerCase())}
                        onChange={() => toggleArrayFilter('location', selectedLocations, loc.toLowerCase())}
                        className="w-3.5 h-3.5 rounded text-primary-600 border-slate-350"
                      />
                      <span>{loc}</span>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Stipend sliders */}
            <div className="space-y-2 border-t border-slate-100 pt-3">
              <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400">
                <label htmlFor="mobile-stipend-min" className="cursor-pointer">Min Stipend (₹/mo)</label>
                <span className="text-slate-700 text-xs font-bold">
                  {stipendMin === '0' ? 'Any' : `₹${parseInt(stipendMin).toLocaleString()}`}
                </span>
              </div>
              <input
                id="mobile-stipend-min"
                type="range"
                min="0"
                max="40000"
                step="2500"
                value={stipendMin}
                onChange={(e) => updateQueryParams({ stipendMin: e.target.value === '0' ? null : e.target.value, page: '1' })}
                className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400">
                <label htmlFor="mobile-stipend-max" className="cursor-pointer">Max Stipend (₹/mo)</label>
                <span className="text-slate-700 text-xs font-bold">
                  {!stipendMax ? 'No Limit' : `₹${parseInt(stipendMax).toLocaleString()}`}
                </span>
              </div>
              <input
                id="mobile-stipend-max"
                type="range"
                min="5000"
                max="60000"
                step="5000"
                value={stipendMax || '60000'}
                onChange={(e) => updateQueryParams({ stipendMax: e.target.value === '60000' ? null : e.target.value, page: '1' })}
                className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
              />
            </div>

            {/* Duration */}
            <div className="space-y-2 border-t border-slate-100 pt-3">
              <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400">Duration</h4>
              <div className="space-y-1.5">
                {durationsList.map((dur) => {
                  const id = `mobile-dur-${dur.value.replace('+', 'plus')}`;
                  return (
                    <label key={dur.value} htmlFor={id} className="flex items-center gap-2 text-xs text-slate-650 hover:text-slate-900 cursor-pointer font-medium">
                      <input
                        id={id}
                        type="checkbox"
                        checked={selectedDurations.includes(dur.value)}
                        onChange={() => toggleArrayFilter('duration', selectedDurations, dur.value)}
                        className="w-3.5 h-3.5 rounded text-primary-600 border-slate-350"
                      />
                      <span>{dur.label}</span>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Skills */}
            <div className="space-y-2 border-t border-slate-100 pt-3">
              <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400 font-sans">Core Skills</h4>
              <div className="flex flex-wrap gap-1">
                {standardSkills.map((skill) => {
                  const sLower = skill.toLowerCase();
                  const isSelected = selectedSkills.includes(sLower);
                  return (
                    <button
                      key={skill}
                      onClick={() => toggleArrayFilter('skills', selectedSkills, sLower)}
                      className={`px-2 py-1 text-[10px] font-semibold rounded border transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-primary-600 text-white border-primary-600 shadow-sm'
                          : 'bg-white text-slate-655 border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      {skill}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Platform Platform */}
            <div className="space-y-2 border-t border-slate-100 pt-3">
              <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400">Platform</h4>
              <div className="space-y-1.5">
                {sourcesList.map((src) => {
                  const id = `mobile-source-${src.toLowerCase().replace(' ', '-')}`;
                  return (
                    <label key={src} htmlFor={id} className="flex items-center gap-2 text-xs text-slate-650 hover:text-slate-900 cursor-pointer font-medium">
                      <input
                        id={id}
                        type="checkbox"
                        checked={selectedSources.includes(src.toLowerCase())}
                        onChange={() => toggleArrayFilter('source', selectedSources, src.toLowerCase())}
                        className="w-3.5 h-3.5 rounded text-primary-600 border-slate-350"
                      />
                      <span>{src}</span>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Legitimacy */}
            <div className="space-y-2 border-t border-slate-100 pt-3">
              <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400">
                <label htmlFor="mobile-legitimacy-min" className="cursor-pointer">Min Legitimacy Score</label>
                <span className="text-slate-700 text-xs font-bold">
                  {legitimacyMin}% Match
                </span>
              </div>
              <input
                id="mobile-legitimacy-min"
                type="range"
                min="60"
                max="100"
                step="5"
                value={legitimacyMin}
                onChange={(e) => updateQueryParams({ legitimacyMin: e.target.value === '60' ? null : e.target.value, page: '1' })}
                className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
              />
            </div>

            {/* Date Posted */}
            <div className="space-y-2 border-t border-slate-100 pt-3">
              <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400">Date Posted</h4>
              <div className="space-y-1.5">
                {[
                  { value: '', label: 'Anytime' },
                  { value: 'today', label: 'Today (Past 24h)' },
                  { value: '3days', label: 'Past 3 Days' },
                  { value: '7days', label: 'Past Week' },
                  { value: '30days', label: 'Past Month' }
                ].map(opt => {
                  const id = `mobile-posted-${opt.value || 'anytime'}`;
                  return (
                    <label key={opt.value} htmlFor={id} className="flex items-center gap-2 text-xs text-slate-650 hover:text-slate-900 cursor-pointer font-medium">
                      <input
                        id={id}
                        type="radio"
                        name="mobileDatePostedOpt"
                        checked={datePosted === opt.value}
                        onChange={() => updateQueryParams({ datePosted: opt.value || null, page: '1' })}
                        className="w-3.5 h-3.5 text-primary-600 border-slate-350"
                      />
                      <span>{opt.label}</span>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Clear All button */}
            <button
              onClick={() => {
                resetAllFilters();
                setShowMobileFilters(false);
              }}
              className="mt-4 w-full py-2.5 border border-slate-200 rounded-lg text-slate-700 text-xs font-bold hover:bg-slate-50 transition-colors cursor-pointer animate-fade-in"
            >
              Clear All Filters
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Search, SlidersHorizontal, Shield, RotateCcw, ChevronLeft, ChevronRight, Check } from 'lucide-react';
import { fetchInternships, fetchFilters } from '../api';
import InternshipCard from '../components/InternshipCard';

export default function ExplorePage() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Filter States synced with URL query params
  const search = searchParams.get('search') || '';
  const paidOnly = searchParams.get('paid') === 'true';
  const remoteOnly = searchParams.get('remote') === 'true';
  const minLegit = searchParams.get('minLegitimacy') || '60';
  const minStipend = searchParams.get('minStipend') || '0';
  const selectedSkills = searchParams.get('skills') ? searchParams.get('skills')!.split(',') : [];
  const selectedSources = searchParams.get('sources') ? searchParams.get('sources')!.split(',') : [];
  const selectedLocations = searchParams.get('locations') ? searchParams.get('locations')!.split(',') : [];
  const selectedRoles = searchParams.get('roleTypes') ? searchParams.get('roleTypes')!.split(',') : [];
  const sortField = searchParams.get('sortField') || 'created_at';
  const sortOrder = searchParams.get('sortOrder') || 'desc';
  const page = searchParams.get('page') || '1';

  // Search input local state for debouncing
  const [localSearch, setLocalSearch] = useState(search);
  const [showMobileFilters, setShowMobileFilters] = useState(false);

  // Sync local search input with URL search param changes
  useEffect(() => {
    setLocalSearch(search);
  }, [search]);

  // Debounce search update
  useEffect(() => {
    const timer = setTimeout(() => {
      if (localSearch !== search) {
        updateQueryParam('search', localSearch);
        updateQueryParam('page', '1'); // reset page on search
      }
    }, 450);
    return () => clearTimeout(timer);
  }, [localSearch]);

  // Fetch filter metadata (locations, sources, skills)
  const { data: filterMeta } = useQuery({
    queryKey: ['filterMetadata'],
    queryFn: fetchFilters,
    staleTime: 300000 // 5 minutes
  });

  // Fetch internships with current filter params
  const queryParams = {
    search,
    paid: paidOnly ? 'true' : '',
    remote: remoteOnly ? 'true' : '',
    minLegitimacy: minLegit,
    minStipend,
    skills: selectedSkills.join(','),
    sources: selectedSources.join(','),
    locations: selectedLocations.join(','),
    roleTypes: selectedRoles.join(','),
    sortField,
    sortOrder,
    page,
    limit: '8'
  };

  const { data: listingsData, isLoading, isError, refetch } = useQuery({
    queryKey: ['internships', queryParams],
    queryFn: () => fetchInternships(queryParams),
    placeholderData: (prev) => prev
  });

  // Helper to update query parameters in URL
  const updateQueryParam = (key: string, value: string | null) => {
    const params = new URLSearchParams(searchParams);
    if (value === null || value === '' || value === 'false') {
      params.delete(key);
    } else {
      params.set(key, value);
    }
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
    updateQueryParam(key, newList.length > 0 ? newList.join(',') : null);
    updateQueryParam('page', '1');
  };

  const resetAllFilters = () => {
    setSearchParams(new URLSearchParams());
    setLocalSearch('');
  };

  // Standard skills to pin in filters
  const standardSkills = ['SQL', 'Excel', 'Power BI', 'Python', 'Tableau', 'Statistics'];
  // Standard roles
  const standardRoles = [
    { key: 'data analyst', label: 'Data Analyst' },
    { key: 'business analyst', label: 'Business Analyst' },
    { key: 'analytics', label: 'Analytics' },
    { key: 'bi', label: 'BI / Power BI' },
    { key: 'data science', label: 'Data Science' }
  ];

  return (
    <div className="space-y-6">
      
      {/* Search & Header Section */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 bg-white border border-slate-200 rounded-xl p-3.5 shadow-sm">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-3 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search role, company, or skills..."
            value={localSearch}
            onChange={(e) => setLocalSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg outline-none focus:border-primary-400 focus:bg-white text-sm transition-all"
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
            value={`${sortField}-${sortOrder}`}
            onChange={(e) => {
              const [field, order] = e.target.value.split('-');
              updateQueryParam('sortField', field);
              updateQueryParam('sortOrder', order);
            }}
            className="px-3.5 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-700 font-medium text-sm outline-none cursor-pointer hover:bg-slate-50 transition-colors"
          >
            <option value="created_at-desc">Newest First</option>
            <option value="created_at-asc">Oldest First</option>
            <option value="legitimacy_score-desc">Highest Legitimacy</option>
            <option value="stipend_numeric-desc">Highest Stipend</option>
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

      {/* Main Board Layout */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-start">
        
        {/* Left Filters Sidebar - Desktop */}
        <aside className="hidden md:block bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-5 sticky top-24 max-h-[85vh] overflow-y-auto">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 className="font-bold text-slate-800 text-sm flex items-center gap-1.5">
              <SlidersHorizontal className="w-4 h-4 text-primary-600" />
              <span>Filters</span>
            </h3>
            <button onClick={resetAllFilters} className="text-xs text-primary-600 hover:text-primary-800 font-semibold transition-colors cursor-pointer">
              Clear all
            </button>
          </div>

          {/* Filter: Role Type */}
          <div className="space-y-2">
            <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400">Role Categories</h4>
            <div className="space-y-1.5">
              {standardRoles.map((role) => (
                <label key={role.key} className="flex items-center gap-2 text-xs text-slate-600 hover:text-slate-900 cursor-pointer font-medium">
                  <input
                    type="checkbox"
                    checked={selectedRoles.includes(role.key)}
                    onChange={() => toggleArrayFilter('roleTypes', selectedRoles, role.key)}
                    className="w-3.5 h-3.5 rounded text-primary-600 border-slate-350 focus:ring-primary-500/20"
                  />
                  <span>{role.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Filter: Location (Remote Toggle) */}
          <div className="space-y-2.5 border-t border-slate-100 pt-3">
            <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400">Work Flexibility</h4>
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-xs font-semibold text-slate-700">Remote Only</span>
              <input
                type="checkbox"
                checked={remoteOnly}
                onChange={(e) => {
                  updateQueryParam('remote', e.target.checked ? 'true' : null);
                  updateQueryParam('page', '1');
                }}
                className="w-8 h-4.5 bg-slate-200 rounded-full appearance-none checked:bg-primary-600 relative cursor-pointer before:absolute before:h-3.5 before:w-3.5 before:bg-white before:rounded-full before:top-0.5 before:left-0.5 checked:before:translate-x-3.5 before:transition-transform duration-200 border border-slate-300"
              />
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-xs font-semibold text-slate-700">Paid Only</span>
              <input
                type="checkbox"
                checked={paidOnly}
                onChange={(e) => {
                  updateQueryParam('paid', e.target.checked ? 'true' : null);
                  updateQueryParam('page', '1');
                }}
                className="w-8 h-4.5 bg-slate-200 rounded-full appearance-none checked:bg-primary-600 relative cursor-pointer before:absolute before:h-3.5 before:w-3.5 before:bg-white before:rounded-full before:top-0.5 before:left-0.5 checked:before:translate-x-3.5 before:transition-transform duration-200 border border-slate-300"
              />
            </label>
          </div>

          {/* Filter: Skills Pills */}
          <div className="space-y-2 border-t border-slate-100 pt-3">
            <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400">Core Skills</h4>
            <div className="flex flex-wrap gap-1">
              {standardSkills.map((skill) => {
                const sLower = skill.toLowerCase();
                const isSelected = selectedSkills.includes(sLower);
                return (
                  <button
                    key={skill}
                    onClick={() => toggleArrayFilter('skills', selectedSkills, sLower)}
                    className={`px-2 py-1 text-[10px] font-semibold rounded border transition-all duration-150 cursor-pointer ${
                      isSelected
                        ? 'bg-primary-600 text-white border-primary-600 shadow-sm'
                        : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    {skill}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Filter: Minimum Stipend Slider */}
          <div className="space-y-2 border-t border-slate-100 pt-3">
            <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400">
              <span>Min Stipend (₹/mo)</span>
              <span className="text-slate-700 text-xs font-bold">
                {minStipend === '0' ? 'Any' : `₹${parseInt(minStipend).toLocaleString()}+`}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="30000"
              step="2000"
              value={minStipend}
              onChange={(e) => updateQueryParam('minStipend', e.target.value === '0' ? null : e.target.value)}
              className="w-full h-1 bg-slate-250 rounded-lg appearance-none cursor-pointer accent-primary-600"
            />
          </div>

          {/* Filter: Legitimacy Score */}
          <div className="space-y-2 border-t border-slate-100 pt-3">
            <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400">
              <span>Min Legitimacy Score</span>
              <span className="text-slate-700 text-xs font-bold">
                {minLegit}% Match
              </span>
            </div>
            <input
              type="range"
              min="60"
              max="105"
              step="5"
              value={minLegit}
              onChange={(e) => updateQueryParam('minLegitimacy', e.target.value)}
              className="w-full h-1 bg-slate-250 rounded-lg appearance-none cursor-pointer accent-primary-600"
            />
            <p className="text-slate-450 text-[9px] leading-tight">
              Filters listings based on verification check markers. A minimum score of 60% is recommended.
            </p>
          </div>

          {/* Filter: Locations Checkboxes */}
          {filterMeta?.locations && filterMeta.locations.length > 0 && (
            <div className="space-y-2 border-t border-slate-100 pt-3">
              <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400">Top Locations</h4>
              <div className="max-h-32 overflow-y-auto space-y-1.5 pr-2">
                {filterMeta.locations.slice(0, 15).map((loc) => (
                  <label key={loc} className="flex items-center gap-2 text-xs text-slate-600 hover:text-slate-900 cursor-pointer font-medium truncate">
                    <input
                      type="checkbox"
                      checked={selectedLocations.includes(loc.toLowerCase())}
                      onChange={() => toggleArrayFilter('locations', selectedLocations, loc.toLowerCase())}
                      className="w-3.5 h-3.5 rounded text-primary-600 border-slate-350 focus:ring-primary-500/20"
                    />
                    <span className="truncate">{loc}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Filter: Sources */}
          {filterMeta?.sources && filterMeta.sources.length > 0 && (
            <div className="space-y-2 border-t border-slate-100 pt-3">
              <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400">Platforms</h4>
              <div className="space-y-1.5">
                {filterMeta.sources.map((src) => (
                  <label key={src} className="flex items-center gap-2 text-xs text-slate-600 hover:text-slate-900 cursor-pointer font-medium">
                    <input
                      type="checkbox"
                      checked={selectedSources.includes(src.toLowerCase())}
                      onChange={() => toggleArrayFilter('sources', selectedSources, src.toLowerCase())}
                      className="w-3.5 h-3.5 rounded text-primary-600 border-slate-350 focus:ring-primary-500/20"
                    />
                    <span>{src}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </aside>

        {/* Right Listings Board */}
        <div className="md:col-span-3 space-y-4">
          
          {/* Listings count and current search term summary */}
          <div className="flex items-center justify-between text-xs text-slate-500 px-1">
            <span>
              {isLoading ? (
                'Loading internships...'
              ) : (
                <>
                  Found <strong className="text-slate-800 font-bold">{listingsData?.total || 0}</strong> internships
                  {search && <span> for "<span className="text-primary-600 font-semibold">{search}</span>"</span>}
                </>
              )}
            </span>
          </div>

          {/* Listings Grid */}
          {isLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="bg-white border border-slate-200 rounded-xl p-5 space-y-4 shadow-sm animate-pulse">
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
              <p className="text-xs text-red-650">
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
              <p className="text-slate-505 text-xs max-w-xs mx-auto leading-relaxed">
                We couldn't find any opportunities matching your filters. Try clearing some tags, reducing minimum stipend, or lowering legitimacy threshold.
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
                onClick={() => updateQueryParam('page', (listingsData.page - 1).toString())}
                className="flex items-center gap-1 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-700 text-xs font-semibold hover:bg-slate-50 disabled:opacity-50 disabled:hover:bg-white disabled:cursor-not-allowed transition-colors cursor-pointer"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Prev</span>
              </button>
              
              <div className="hidden sm:flex items-center gap-1 text-xs font-semibold text-slate-500">
                {[...Array(listingsData.totalPages)].map((_, index) => {
                  const pNum = index + 1;
                  const isCurrent = listingsData.page === pNum;
                  return (
                    <button
                      key={pNum}
                      onClick={() => updateQueryParam('page', pNum.toString())}
                      className={`w-8 h-8 rounded-lg flex items-center justify-center border transition-all cursor-pointer ${
                        isCurrent
                          ? 'bg-primary-600 text-white border-primary-600 shadow-sm'
                          : 'bg-white border-slate-200 text-slate-650 hover:bg-slate-50'
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
                onClick={() => updateQueryParam('page', (listingsData.page + 1).toString())}
                className="flex items-center gap-1 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-700 text-xs font-semibold hover:bg-slate-50 disabled:opacity-50 disabled:hover:bg-white disabled:cursor-not-allowed transition-colors cursor-pointer"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

        </div>
      </div>

      {/* Slide-out Mobile Filters Overlay */}
      {showMobileFilters && (
        <div className="fixed inset-0 z-50 md:hidden flex justify-end">
          {/* Overlay background */}
          <div
            onClick={() => setShowMobileFilters(false)}
            className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-all"
          ></div>
          
          {/* Filter container */}
          <div className="relative w-72 max-w-[90vw] h-full bg-white shadow-xl flex flex-col p-5 space-y-5 overflow-y-auto animate-slide-in">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-800 text-sm">Mobile Filters</h3>
              <button
                onClick={() => setShowMobileFilters(false)}
                className="p-1 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 cursor-pointer"
              >
                <Check className="w-4 h-4" />
              </button>
            </div>

            {/* Filter: Role Type */}
            <div className="space-y-2">
              <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400">Role Categories</h4>
              <div className="space-y-1.5">
                {standardRoles.map((role) => (
                  <label key={role.key} className="flex items-center gap-2 text-xs text-slate-600 hover:text-slate-900 cursor-pointer font-medium">
                    <input
                      type="checkbox"
                      checked={selectedRoles.includes(role.key)}
                      onChange={() => toggleArrayFilter('roleTypes', selectedRoles, role.key)}
                      className="w-3.5 h-3.5 rounded text-primary-600 border-slate-350"
                    />
                    <span>{role.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Filter: Remote / Paid Toggles */}
            <div className="space-y-2.5 border-t border-slate-100 pt-3">
              <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400">Work Flexibility</h4>
              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-xs font-semibold text-slate-700">Remote Only</span>
                <input
                  type="checkbox"
                  checked={remoteOnly}
                  onChange={(e) => updateQueryParam('remote', e.target.checked ? 'true' : null)}
                  className="w-8 h-4.5 bg-slate-200 rounded-full appearance-none checked:bg-primary-600 relative cursor-pointer before:absolute before:h-3.5 before:w-3.5 before:bg-white before:rounded-full before:top-0.5 before:left-0.5 checked:before:translate-x-3.5 before:transition-transform border"
                />
              </label>
              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-xs font-semibold text-slate-700">Paid Only</span>
                <input
                  type="checkbox"
                  checked={paidOnly}
                  onChange={(e) => updateQueryParam('paid', e.target.checked ? 'true' : null)}
                  className="w-8 h-4.5 bg-slate-200 rounded-full appearance-none checked:bg-primary-600 relative cursor-pointer before:absolute before:h-3.5 before:w-3.5 before:bg-white before:rounded-full before:top-0.5 before:left-0.5 checked:before:translate-x-3.5 before:transition-transform border"
                />
              </label>
            </div>

            {/* Filter: Skills Pills */}
            <div className="space-y-2 border-t border-slate-100 pt-3">
              <h4 className="font-bold text-[10px] uppercase tracking-wider text-slate-400">Core Skills</h4>
              <div className="flex flex-wrap gap-1">
                {standardSkills.map((skill) => {
                  const sLower = skill.toLowerCase();
                  const isSelected = selectedSkills.includes(sLower);
                  return (
                    <button
                      key={skill}
                      onClick={() => toggleArrayFilter('skills', selectedSkills, sLower)}
                      className={`px-2 py-1 text-[10px] font-semibold rounded border cursor-pointer ${
                        isSelected
                          ? 'bg-primary-600 text-white border-primary-600'
                          : 'bg-white text-slate-600 border-slate-200'
                      }`}
                    >
                      {skill}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Filter: Minimum Stipend Slider */}
            <div className="space-y-2 border-t border-slate-100 pt-3">
              <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400">
                <span>Min Stipend (₹/mo)</span>
                <span className="text-slate-700 text-xs font-bold">
                  {minStipend === '0' ? 'Any' : `₹${parseInt(minStipend).toLocaleString()}+`}
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="30000"
                step="2000"
                value={minStipend}
                onChange={(e) => updateQueryParam('minStipend', e.target.value === '0' ? null : e.target.value)}
                className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
              />
            </div>

            {/* Filter: Legitimacy Score */}
            <div className="space-y-2 border-t border-slate-100 pt-3">
              <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400">
                <span>Min Legitimacy Score</span>
                <span className="text-slate-700 text-xs font-bold">
                  {minLegit}% Match
                </span>
              </div>
              <input
                type="range"
                min="60"
                max="100"
                step="5"
                value={minLegit}
                onChange={(e) => updateQueryParam('minLegitimacy', e.target.value)}
                className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
              />
            </div>

            {/* Clear All button */}
            <button
              onClick={() => {
                resetAllFilters();
                setShowMobileFilters(false);
              }}
              className="mt-6 w-full py-2.5 border border-slate-200 rounded-lg text-slate-700 text-xs font-bold hover:bg-slate-50 transition-colors cursor-pointer"
            >
              Clear All Filters
            </button>
          </div>
        </div>
      )}

    </div>
  );
}

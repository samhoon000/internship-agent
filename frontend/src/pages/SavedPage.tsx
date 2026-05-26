import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Bookmark, Trash2, ArrowRight } from 'lucide-react';
import type { Internship } from '../api';
import InternshipCard from '../components/InternshipCard';

export default function SavedPage() {
  const [savedList, setSavedList] = useState<Internship[]>([]);

  const loadSaved = () => {
    try {
      const saved = JSON.parse(localStorage.getItem('saved_internships') || '[]');
      setSavedList(saved);
    } catch (e) {
      setSavedList([]);
    }
  };

  useEffect(() => {
    loadSaved();
    
    // Listen for bookmarks updates
    window.addEventListener('bookmarks-changed', loadSaved);
    return () => {
      window.removeEventListener('bookmarks-changed', loadSaved);
    };
  }, []);

  const clearAllBookmarks = () => {
    if (window.confirm('Are you sure you want to clear all saved internships?')) {
      localStorage.setItem('saved_internships', '[]');
      setSavedList([]);
      window.dispatchEvent(new Event('bookmarks-changed'));
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-16">
      
      {/* Header Panel */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Bookmark className="w-5 h-5 text-primary-600 fill-current" />
            <span>Saved Internships</span>
          </h1>
          <p className="text-slate-500 text-xs mt-0.5">
            Manage your bookmarked listings. Bookmarks are saved locally in your browser storage.
          </p>
        </div>

        {savedList.length > 0 && (
          <button
            onClick={clearAllBookmarks}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-red-600 hover:text-red-700 bg-red-50 border border-red-100 hover:bg-red-100 rounded-lg transition-colors cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear Bookmarks</span>
          </button>
        )}
      </div>

      {/* Bookmarks Grid */}
      {savedList.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-10 text-center space-y-4 max-w-md mx-auto mt-10 shadow-sm">
          <div className="w-12 h-12 bg-slate-50 border border-slate-200 text-slate-400 rounded-lg flex items-center justify-center mx-auto">
            <Bookmark className="w-6 h-6" />
          </div>
          <div className="space-y-1.5">
            <h3 className="font-bold text-base text-slate-800">No Bookmarks Yet</h3>
            <p className="text-slate-500 text-xs max-w-xs mx-auto leading-relaxed">
              Start searching for Data Analyst, Business Analyst, or Data Science internships and save them for quick access later.
            </p>
          </div>
          <div className="pt-1.5">
            <Link
              to="/explore"
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white text-xs font-bold rounded-lg shadow-sm transition-colors cursor-pointer"
            >
              <span>Browse Internships</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
          {savedList.map((item) => (
            <InternshipCard
              key={item.apply_link}
              internship={item}
              onBookmarkChanged={loadSaved}
            />
          ))}
        </div>
      )}

    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Shield, Bookmark, BarChart2, Info, Compass, Menu, X, Database } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const [savedCount, setSavedCount] = useState(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Sync saved count from localStorage
  const updateSavedCount = () => {
    try {
      const saved = JSON.parse(localStorage.getItem('saved_internships') || '[]');
      setSavedCount(saved.length);
    } catch (e) {
      setSavedCount(0);
    }
  };

  useEffect(() => {
    updateSavedCount();
    // Listen for custom events or storage updates
    window.addEventListener('storage', updateSavedCount);
    window.addEventListener('bookmarks-changed', updateSavedCount);
    return () => {
      window.removeEventListener('storage', updateSavedCount);
      window.removeEventListener('bookmarks-changed', updateSavedCount);
    };
  }, []);

  const navLinks = [
    { name: 'Explore', path: '/explore', icon: Compass },
    { name: 'Saved', path: '/saved', icon: Bookmark, badge: savedCount },
    { name: 'Analytics', path: '/analytics', icon: BarChart2 },
    { name: 'About', path: '/about', icon: Info }
  ];

  return (
    <div className="flex flex-col min-h-screen bg-[#f8fafc]">
      {/* Sticky Navbar */}
      <header className="sticky top-0 z-50 w-full bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            
            {/* Logo */}
            <Link to="/" className="flex items-center space-x-2 group">
              <div className="bg-slate-900 p-2 rounded-lg text-primary-500 group-hover:bg-slate-800 transition-colors duration-150">
                <Shield className="w-5 h-5 text-primary-500" />
              </div>
              <span className="font-bold text-lg tracking-tight text-slate-900">
                Intern<span className="text-primary-600 font-bold">Legit</span>
              </span>
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center space-x-1">
              {navLinks.map((link) => {
                const Icon = link.icon;
                const isActive = location.pathname === link.path;
                return (
                  <Link
                    key={link.path}
                    to={link.path}
                    className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                      isActive
                        ? 'bg-slate-100 text-slate-900'
                        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{link.name}</span>
                    {link.badge !== undefined && link.badge > 0 && (
                      <span className="ml-1 px-1.5 py-0.5 text-[10px] font-bold bg-primary-600 text-white rounded-full">
                        {link.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
              
              <Link
                to="/explore"
                className="ml-4 inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-lg text-sm font-semibold text-white bg-primary-600 hover:bg-primary-700 shadow-sm transition-colors duration-150"
              >
                Find Internships
              </Link>
            </nav>

            {/* Mobile menu button */}
            <div className="md:hidden">
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="inline-flex items-center justify-center p-2 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 focus:outline-none transition-colors"
              >
                {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </button>
            </div>

          </div>
        </div>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-white border-t border-slate-200 shadow-inner px-4 pt-2 pb-4 space-y-1">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = location.pathname === link.path;
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                    isActive
                      ? 'bg-slate-100 text-slate-900'
                      : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="flex-1">{link.name}</span>
                  {link.badge !== undefined && link.badge > 0 && (
                    <span className="px-1.5 py-0.5 text-[10px] font-bold bg-primary-600 text-white rounded-full">
                      {link.badge}
                    </span>
                  )}
                </Link>
              );
            })}
            <Link
              to="/explore"
              onClick={() => setMobileMenuOpen(false)}
              className="mt-4 w-full flex items-center justify-center px-4 py-2.5 border border-transparent rounded-lg text-sm font-bold text-white bg-primary-600 hover:bg-primary-700 shadow-sm"
            >
              Find Internships
            </Link>
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Modern Footer */}
      <footer className="bg-white border-t border-slate-200 py-12 mt-auto text-slate-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="md:col-span-2 space-y-4">
              <Link to="/" className="flex items-center space-x-2">
                <div className="bg-slate-900 p-2 rounded-lg text-primary-500">
                  <Shield className="w-5 h-5 text-primary-500" />
                </div>
                <span className="font-bold text-lg tracking-tight text-slate-900">
                  Intern<span className="text-primary-600 font-bold">Legit</span>
                </span>
              </Link>
              <p className="text-slate-500 text-sm max-w-sm leading-relaxed">
                Legitimacy-scored Data Analyst, Data Science, and Analytics internships. Discover high-quality, verified opportunities and skip the spam.
              </p>
            </div>
            
            <div>
              <h3 className="font-bold text-sm text-slate-800 tracking-wider uppercase mb-4">Platform</h3>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link to="/explore" className="text-slate-500 hover:text-primary-600 transition-colors">
                    Explore Internships
                  </Link>
                </li>
                <li>
                  <Link to="/analytics" className="text-slate-500 hover:text-primary-600 transition-colors">
                    Analytics Dashboard
                  </Link>
                </li>
                <li>
                  <Link to="/about" className="text-slate-500 hover:text-primary-600 transition-colors">
                    How it Works
                  </Link>
                </li>
              </ul>
            </div>

            <div>
              <h3 className="font-bold text-sm text-slate-800 tracking-wider uppercase mb-4">Tech Details</h3>
              <div className="flex items-center space-x-2 text-slate-500 text-sm">
                <Database className="w-4 h-4 text-accent-500" />
                <span>MySQL Connected</span>
              </div>
              <p className="text-xs text-slate-400 mt-2">
                Playwright crawers scan once daily. Low confidence listings are auto-filtered out.
              </p>
            </div>
          </div>
          
          <div className="border-t border-slate-100 mt-12 pt-6 flex flex-col sm:flex-row items-center justify-between">
            <p className="text-xs text-slate-400">
              &copy; {new Date().getFullYear()} InternLegit. All rights reserved.
            </p>
            <div className="flex space-x-4 mt-4 sm:mt-0 text-xs text-slate-400">
              <span>Recruiter-Impressive Portfolio Project</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

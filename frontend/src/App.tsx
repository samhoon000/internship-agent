import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';

// Lazy-load page components for optimized bundle splitting
const LandingPage = lazy(() => import('./pages/LandingPage'));
const ExplorePage = lazy(() => import('./pages/ExplorePage'));
const DetailsPage = lazy(() => import('./pages/DetailsPage'));
const SavedPage = lazy(() => import('./pages/SavedPage'));
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage'));
const AboutPage = lazy(() => import('./pages/AboutPage'));
const HealthDashboard = lazy(() => import('./pages/HealthDashboard'));

// Initialize TanStack React Query Client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false, // Prevents aggressive background refetches
      retry: 1,                    // Limit retries on network failures
      staleTime: 60000             // Cache query results for 60 seconds
    }
  }
});

// CSS-based Spinner for route lazy-loading
const LoadingSpinner = () => (
  <div className="flex items-center justify-center min-h-[50vh]">
    <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
  </div>
);

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Layout>
          <Suspense fallback={<LoadingSpinner />}>
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/explore" element={<ExplorePage />} />
              <Route path="/saved" element={<SavedPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/about" element={<AboutPage />} />
              <Route path="/health" element={<HealthDashboard />} />
              <Route path="/internships/:applyLink" element={<DetailsPage />} />
              {/* Fallback route */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </Layout>
      </Router>
    </QueryClientProvider>
  );
}

export default App;

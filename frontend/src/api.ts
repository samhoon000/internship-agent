export interface Internship {
  apply_link: string;
  company_name: string;
  role: string;
  stipend: string | null;
  paid: boolean | number;
  location: string | null;
  remote: boolean | number;
  duration: string | null;
  skills: string | null;
  skills_list: string[];
  stipend_numeric: number;
  source: string;
  legitimacy_score: number;
  confidence?: string;
  created_at: string;
}

export interface InternshipResponse {
  internships: Internship[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

export interface PopularSkill {
  name: string;
  count: number;
}

export interface FilterResponse {
  locations: string[];
  sources: string[];
  skills: PopularSkill[];
}

export interface AnalyticsResponse {
  metrics: {
    totalScraped: number;
    highlyLegit: number;
    avgLegitimacy: number;
  };
  charts: {
    skillsDemand: { name: string; value: number }[];
    topPaying: { company: string; role: string; stipend: number; stipendText: string }[];
    remoteDistribution: { name: string; value: number }[];
    sourceDistribution: { name: string; value: number }[];
    topCompanies: { name: string; count: number }[];
    locationDistribution: { name: string; count: number }[];
    avgStipendTrend: { name: string; avgStipend: number }[];
  };
}

export interface ScraperStatusResponse {
  status: 'idle' | 'running' | 'completed' | 'failed';
  logs: string[];
}

const API_BASE_URL = 'http://localhost:5000/api';

export async function fetchInternships(params: Record<string, any>): Promise<InternshipResponse> {
  const queryParams = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '') {
      queryParams.append(key, val);
    }
  });
  
  const res = await fetch(`${API_BASE_URL}/internships?${queryParams.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch internships');
  return res.json();
}

export async function fetchInternshipDetails(applyLink: string): Promise<{ internship: Internship; similar: Internship[] }> {
  // Base64 encode the applyLink for the URL parameter
  const base64Link = btoa(unescape(encodeURIComponent(applyLink)));
  const res = await fetch(`${API_BASE_URL}/internships/${base64Link}`);
  if (!res.ok) throw new Error('Failed to fetch internship details');
  return res.json();
}

export async function fetchFilters(): Promise<FilterResponse> {
  const res = await fetch(`${API_BASE_URL}/filters`);
  if (!res.ok) throw new Error('Failed to fetch filters');
  return res.json();
}

export async function fetchAnalytics(): Promise<AnalyticsResponse> {
  const res = await fetch(`${API_BASE_URL}/stats`);
  if (!res.ok) throw new Error('Failed to fetch analytics');
  return res.json();
}

export async function runScraper(): Promise<{ status: string; message: string; logs: string[] }> {
  const res = await fetch(`${API_BASE_URL}/scrapers/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  if (!res.ok) throw new Error('Failed to trigger scraper');
  return res.json();
}

export async function fetchScraperStatus(): Promise<ScraperStatusResponse> {
  const res = await fetch(`${API_BASE_URL}/scrapers/status`);
  if (!res.ok) throw new Error('Failed to fetch scraper status');
  return res.json();
}

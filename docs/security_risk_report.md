# Production Launch Security Risk Report

This document outlines the security posture, risk assessment, and mitigation controls implemented for the Internship Discovery Platform prior to public launch.

---

## 1. Authentication & Route Authorization

### Vulnerability / Risk
Unauthorized access to administrative triggers (such as launching data crawlers or clearing database records) could lead to resource exhaustion, API abuse, or server denial of service.

### Security Controls
- **API Key Authorization**: All administrative endpoints (`POST /api/scrapers/run`, `POST /api/scrapers/cleanup`, `POST /api/scrapers/liveness`) are protected by a custom `verifyAdminKey` middleware.
- **Key Validation**: The middleware extracts the client request key from either the `X-Admin-API-Key` request header or the URL query parameter `apiKey` and strictly validates it against the cryptographically random `ADMIN_API_KEY` defined in the environment.
- **Default Key Prevention**: Startup validation in `env.js` issues warning alerts if the default developer fallback key `super-secret-admin-key` is used in production.

---

## 2. Cross-Origin Resource Sharing (CORS)

### Vulnerability / Risk
Lax CORS policies allow arbitrary external web origins to make requests to API endpoints, potentially exposing search history or saved bookmarks if browser authentication cookies are in use, or causing unsolicited traffic.

### Security Controls
- **Explicit Origin Whitelisting**: CORS is configured using the `cors` package in Express, limiting API request origins to the Vite development port (`http://localhost:5173`) and the production site location defined via the `FRONTEND_URL` environment variable.
- **Dynamic Origin Check**: If an origin is not in the whitelist, the middleware blocks the preflight or standard request immediately with a standard CORS exception message.

---

## 3. Rate Limiting & DDoS Prevention

### Vulnerability / Risk
Brute-forcing or massive automated polling of endpoints can degrade database performance and cause API latency to spike, denying service to legitimate students.

### Security Controls
- **Global Rate Limiting**: The Express backend mounts the `express-rate-limit` middleware on all API routes (`/api/*`).
- **Policy Configuration**:
  - **Window**: 15 minutes (`15 * 60 * 1000` ms).
  - **Limit**: Maximum 100 requests per IP address.
  - **Headers**: Exposes standard rate-limiting metadata headers (`RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset`).
  - **Payload**: Rejects requests exceeding the limit with a HTTP `429 Too Many Requests` status code and a structured JSON payload: `{ "error": "Too many requests from this IP..." }`.

---

## 4. SQL Injection Prevention

### Vulnerability / Risk
User-provided inputs in query parameters (such as search queries, locations, stipends, or page indices) can be manipulated to run arbitrary SQL commands, compromising DB integrity.

### Security Controls
- **Parameterized SQL Queries**: All queries executed against MySQL are done through the `mysql2/promise` pool using prepended statements and parameter placeholder syntax (`?`).
- **Typing Casts**: Search parameters (like page index `page` and listing limits `limit`) are strictly cast to numbers (`parseInt()`) in the route controllers before running query executions.
- **Base64 Link Parsing**: The unique identifier for detail fetching (`/api/internships/:applyLink`) is a Base64-encoded URL. The backend decodes it and runs a parameterized query, ensuring raw SQL constructs cannot be executed in the URL path parameters.

---

## 5. Cross-Site Scripting (XSS) & Input Sanitization

### Vulnerability / Risk
Malicious internship descriptions or titles containing `<script>` blocks or inline event handlers could execute code in the browser of users viewing listings.

### Security Controls
- **HTML Sanitization**: The backend uses the `sanitize-html` library to process data incoming from scraper runs before insertion.
- **Sanitized Fields**: Scraper results strip script elements, frames, inline styles, and unapproved HTML tags to guarantee only plain text or safe tags are rendered.

---

## 6. Security HTTP Headers (Helmet)

### Vulnerability / Risk
Clickjacking, MIME-sniffing, cross-site scripting (XSS) via lack of Content Security Policy, and HTTP Downgrade attacks can occur if server response headers are not properly configured.

### Security Controls
- **Helmet Middleware Integration**: Express mounts `helmet()` globally at startup.
- **Default Headers Set**:
  - `Content-Security-Policy`: Restricts resource loading locations.
  - `X-Frame-Options`: Set to `SAMEORIGIN` to prevent clickjacking.
  - `Strict-Transport-Security`: Forces HTTP over SSL/TLS.
  - `X-Content-Type-Options`: Disables MIME type sniffing.
  - `Referrer-Policy`: Controls referrer information passed in headers.

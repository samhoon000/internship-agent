# Production Deployment Guide

This document describes how to deploy the Internship Discovery Platform in production, detail security hardening, and set up environmental dependencies.

---

## Option A: Virtual Private Server (VPS) via Docker Compose (Recommended)

This option is highly cost-effective and runs the entire application within Docker containers on a single Linux VPS (Ubuntu 20.04/22.04 LTS).

### 1. Prerequisites
- Docker & Docker Compose installed:
  ```bash
  sudo apt update
  sudo apt install -y docker.io docker-compose
  ```
- Domain name pointed to the VPS IP (e.g. `internships.yourdomain.com`).

### 2. Deployment Setup
1. Clone the repository on the VPS:
   ```bash
   git clone https://github.com/samhoon000/internship-agent.git /opt/internship-tracker
   cd /opt/internship-tracker
   ```
2. Create the production `.env` file at the root:
   ```env
   # Database & Redis Settings (Internal Docker Hostnames)
   DB_HOST=db
   DB_USER=root
   DB_PASSWORD=your_secure_db_password
   DB_NAME=internship
   REDIS_HOST=redis
   REDIS_PORT=6379
   DATABASE_URL=mysql+pymysql://root:your_secure_db_password@db/internship
   
   # App Settings
   PORT=5000
   FRONTEND_URL=https://internships.yourdomain.com
   ADMIN_API_KEY=your_cryptographically_secure_admin_key
   PLAYWRIGHT_HEADLESS=True
   ```
3. Boot the environment using Docker Compose:
   ```bash
   docker-compose up -d --build
   ```

### 3. Reverse Proxy & SSL Setup (Nginx + Certbot)
To serve the frontend over HTTPS on port 443, run Nginx on the host VPS:
1. Install Nginx and Certbot:
   ```bash
   sudo apt install -y nginx certbot python3-certbot-nginx
   ```
2. Configure `/etc/nginx/sites-available/internship` to route traffic:
   ```nginx
   server {
       listen 80;
       server_name internships.yourdomain.com;

       # Frontend Routing
       location / {
           proxy_pass http://localhost:5173; # Maps to frontend container
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }

       # Backend API Routing
       location /api/ {
           proxy_pass http://localhost:5000/api/; # Maps to backend container
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```
3. Enable configuration and generate SSL:
   ```bash
   sudo ln -s /etc/nginx/sites-available/internship /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   sudo certbot --nginx -d internships.yourdomain.com
   ```

### 4. Firewall Hardening (UFW)
Ensure MySQL and Redis ports are blocked from external public access:
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP Nginx
sudo ufw allow 443/tcp   # HTTPS Nginx
sudo ufw enable
```

---

## Option B: Managed Platform-as-a-Service (PaaS - Render / Railway)

This option provides zero-downtime deployments, managed databases, and requires no infrastructure management.

### 1. Provision Databases
- **MySQL Database**: Provision a managed MySQL instance (Railway MySQL or Render Database). Copy the connection URL.
- **Redis Instance**: Provision a managed Redis instance (Railway Redis or Upstash). Copy the connection details.

### 2. Deploy Services
1. **Backend Service**:
   - Create a Web Service pointed to your GitHub repository.
   - Set the Build Command/Start Command to use `Dockerfile.backend` (Render automatically detects this or configure it under service settings).
   - Set Env Variables:
     - `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `REDIS_HOST`, `REDIS_PORT` (from managed DB details).
     - `ADMIN_API_KEY`, `FRONTEND_URL` (production domain).
2. **Worker Service**:
   - Create a Private/Background Service.
   - Use `Dockerfile.scraper` to run the background BullMQ consumer.
   - Set matching database and Redis environment variables.
3. **Frontend Service**:
   - Create a Static Site (Render) or Web Service (Railway).
   - Use `Dockerfile.frontend` to build and serve the static files with the built-in Nginx router.
   - Point its API URL configs to the deployed backend service URL.

---

## Option C: Cloud Enterprise Deployment (AWS ECS & RDS)

This option is suited for enterprise scaling, high availability, and isolated VPC networks.

### 1. Networking (VPC)
- Create a VPC with 2 public subnets (routing internet traffic) and 2 private subnets.
- Private subnets will host the databases (RDS & ElastiCache) and container tasks.

### 2. Managed Databases
- **Amazon RDS (MySQL)**: Set up a Multi-AZ MySQL RDS instance inside the private database subnet group. Configure Security Groups to allow incoming traffic on port 3306 only from the ECS tasks security group.
- **Amazon ElastiCache (Redis)**: Provision a Redis cluster in the private subnets. Restrict port 6379 access to the ECS tasks group.

### 3. Application Orchestration (AWS ECS + Fargate)
- Create an ECS Cluster.
- **Backend Task Definition**:
  - Define container properties using the `Dockerfile.backend` image (hosted in AWS ECR).
  - Map port 5000. Configure AWS CloudWatch logs group.
- **Worker Task Definition**:
  - Define container properties using the `Dockerfile.scraper` image.
  - Set entrypoint or start command to execute the worker process (`npm run worker`).
- **Load Balancer (ALB)**:
  - Create an Application Load Balancer in the public subnets.
  - Configure target groups and route `/api/*` requests to the Backend ECS Task on port 5000.
  - Secure the ALB with an SSL certificate from AWS Certificate Manager (ACM).

### 4. Frontend CDN (AWS S3 & CloudFront)
- **AWS S3**: Create a private S3 bucket. Upload the built frontend client assets (the output of `npm run build` from Vite).
- **AWS CloudFront**: Create a CloudFront Distribution pointing to the S3 bucket.
  - Configure **Origin Access Control (OAC)** to block direct public S3 URL access.
  - Configure **Custom Error Responses**: Map `404: Not Found` error codes to return `/index.html` with a status code of `200` to support SPA routing fallback.
  - Add Route rules to forward `/api/*` requests to the Application Load Balancer.

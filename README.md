# BRP Parts Portal

A secure, multi-user web application for managing automotive parts data from multiple suppliers. Built for customs compliance tracking including weights, values, country of origin, and material content.

<img src="https://customer-assets.emergentagent.com/job_de62b586-37dc-482e-9f01-b4c01458fc65/artifacts/h5zfso2l_BRP_inc_logo.svg.png"
     alt="BRP Logo"
     width="150">
 
---

## Table of Contents

1. [Features](#features)
2. [Tech Stack](#tech-stack)
3. [Prerequisites](#prerequisites)
4. [Database Setup (MongoDB)](#database-setup-mongodb)
5. [Environment Variables](#environment-variables)
6. [Local Development](#local-development)
7. [Production Deployment](#production-deployment)
8. [Security Considerations](#security-considerations)
9. [Maintenance & Monitoring](#maintenance--monitoring)
10. [Support](#support)

---

## Features

### For Suppliers
- ✅ View and manage assigned parts (Parent SKUs)
- ✅ Add/Edit/Delete child components
- ✅ Upload supporting documents (PDF, images, Excel)
- ✅ Excel import/export for bulk data updates
- ✅ Track customs compliance data:
  - Country of origin
  - Weight (kg/lbs)
  - Value (USD)
  - Aluminum/Steel content percentages
  - Russian content declaration

### For Administrators
- ✅ Manage supplier accounts (create, edit, deactivate)
- ✅ View all parts across all suppliers
- ✅ Full audit log with filtering and export
- ✅ Create and delete Parent SKUs

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Frontend** | React 18, TailwindCSS, shadcn/ui |
| **Backend** | Python FastAPI |
| **Database** | MongoDB |
| **Authentication** | JWT (JSON Web Tokens) |
| **File Storage** | Local filesystem (can be configured for S3) |

---

## Prerequisites

Before deploying, ensure you have:

- [ ] **Node.js** v18+ (for frontend)
- [ ] **Python** 3.11+ (for backend)
- [ ] **MongoDB** account or self-hosted instance
- [ ] **Domain name** (for production)
- [ ] **SSL certificate** (for HTTPS)

---

## Database Setup (MongoDB)

### Option A: MongoDB Atlas (Recommended for Production)

MongoDB Atlas is a fully managed cloud database service. **No PostgreSQL needed** - this application uses MongoDB.

#### Step 1: Create MongoDB Atlas Account
1. Go to [https://www.mongodb.com/atlas](https://www.mongodb.com/atlas)
2. Click "Try Free" and create an account
3. Verify your email

#### Step 2: Create a Cluster
1. Click "Build a Database"
2. Choose your plan:
   - **Free Tier (M0)**: Good for testing (512MB storage)
   - **Dedicated (M10+)**: Recommended for production ($57+/month)
3. Select cloud provider (AWS, GCP, or Azure)
4. Choose region closest to your users
5. Click "Create Cluster" (takes 3-5 minutes)

#### Step 3: Configure Database Access
1. Go to "Database Access" in left sidebar
2. Click "Add New Database User"
3. Choose "Password" authentication
4. Enter username: `brp_parts_admin`
5. Click "Autogenerate Secure Password" and **save this password**
6. Set privileges to "Read and write to any database"
7. Click "Add User"

#### Step 4: Configure Network Access
1. Go to "Network Access" in left sidebar
2. Click "Add IP Address"
3. For production, add your server's IP address
4. For testing, you can click "Allow Access from Anywhere" (0.0.0.0/0)
   - ⚠️ **Not recommended for production**
5. Click "Confirm"

#### Step 5: Get Connection String
1. Go to "Database" in left sidebar
2. Click "Connect" on your cluster
3. Choose "Connect your application"
4. Select Driver: Python, Version: 3.11 or later
5. Copy the connection string, it looks like:
   ```
   mongodb+srv://brp_parts_admin:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
6. Replace `<password>` with your database user password

### Option B: Self-Hosted MongoDB

If you prefer to host MongoDB yourself:

```bash
# Ubuntu/Debian
sudo apt-get install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod

# Connection string for local MongoDB
mongodb://localhost:27017
```

---

## Environment Variables

### Backend (`/backend/.env`)

```env
# MongoDB Connection
MONGO_URL=mongodb+srv://brp_parts_admin:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
DB_NAME=brp_parts_portal

# Security
JWT_SECRET=your-super-secure-random-string-minimum-32-characters
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Optional: File upload limits
MAX_UPLOAD_SIZE=10485760  # 10MB in bytes
```

### Frontend (`/frontend/.env`)

```env
# Backend API URL (your production domain)
REACT_APP_BACKEND_URL=https://api.yourdomain.com
```

### Generating a Secure JWT Secret

```bash
# Linux/Mac
openssl rand -hex 32

# Or using Python
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Local Development

### 1. Clone and Install Dependencies

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend
yarn install
```

### 2. Configure Environment Variables

```bash
# Copy example env files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Edit with your values
nano backend/.env
nano frontend/.env
```

### 3. Start Development Servers

```bash
# Terminal 1: Backend
cd backend
uvicorn server:app --reload --port 8001

# Terminal 2: Frontend
cd frontend
yarn start
```

### 4. Create Initial Admin User

```bash
# Call the seed endpoint to create demo users
curl -X POST http://localhost:8001/api/seed-data
```

**Demo Credentials:**
- Admin: `admin@rvparts.com` / `admin123`
- Supplier: `supplier1@metalworks.com` / `supplier123`

---

## Production Deployment

### Option 1: Cloud Platform (Recommended)

#### Deploy on AWS

##### A. Backend (AWS Elastic Beanstalk or ECS)

1. **Create ECR Repository**
   ```bash
   aws ecr create-repository --repository-name brp-parts-backend
   ```

2. **Build and Push Docker Image**
   ```bash
   # Create Dockerfile in /backend
   docker build -t brp-parts-backend .
   docker tag brp-parts-backend:latest YOUR_AWS_ACCOUNT.dkr.ecr.REGION.amazonaws.com/brp-parts-backend:latest
   docker push YOUR_AWS_ACCOUNT.dkr.ecr.REGION.amazonaws.com/brp-parts-backend:latest
   ```

3. **Deploy to ECS/Elastic Beanstalk**
   - Configure environment variables in AWS Console
   - Set up Application Load Balancer with SSL

##### B. Frontend (AWS S3 + CloudFront)

1. **Build Production Bundle**
   ```bash
   cd frontend
   yarn build
   ```

2. **Create S3 Bucket**
   ```bash
   aws s3 mb s3://brp-parts-frontend
   aws s3 website s3://brp-parts-frontend --index-document index.html --error-document index.html
   ```

3. **Upload Build Files**
   ```bash
   aws s3 sync build/ s3://brp-parts-frontend --acl public-read
   ```

4. **Configure CloudFront**
   - Create distribution pointing to S3 bucket
   - Add SSL certificate (AWS Certificate Manager)
   - Set up custom domain

#### Deploy on DigitalOcean (Simpler)

1. **Create Droplet** (Ubuntu 22.04, $12/month minimum)
2. **Install Dependencies**
   ```bash
   sudo apt update
   sudo apt install -y python3-pip nodejs npm nginx certbot
   ```

3. **Clone and Configure**
   ```bash
   git clone YOUR_REPO /var/www/brp-parts
   cd /var/www/brp-parts
   # Configure .env files
   ```

4. **Set Up Nginx**
   ```nginx
   # /etc/nginx/sites-available/brp-parts
   server {
       listen 80;
       server_name yourdomain.com;
       
       location / {
           root /var/www/brp-parts/frontend/build;
           try_files $uri $uri/ /index.html;
       }
       
       location /api {
           proxy_pass http://localhost:8001;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }
   }
   ```

5. **Enable SSL**
   ```bash
   sudo certbot --nginx -d yourdomain.com
   ```

6. **Set Up Process Manager**
   ```bash
   sudo pip install supervisor
   # Configure supervisor for backend process
   ```

### Option 2: Docker Deployment

#### Docker Compose (Recommended for Self-Hosting)

Create `docker-compose.yml` in project root:

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8001:8001"
    environment:
      - MONGO_URL=${MONGO_URL}
      - DB_NAME=${DB_NAME}
      - JWT_SECRET=${JWT_SECRET}
      - CORS_ORIGINS=${CORS_ORIGINS}
    volumes:
      - ./uploads:/app/uploads
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - backend
      - frontend
    restart: unless-stopped
```

#### Backend Dockerfile (`/backend/Dockerfile`)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
```

#### Frontend Dockerfile (`/frontend/Dockerfile`)

```dockerfile
FROM node:18-alpine as build

WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile

COPY . .
RUN yarn build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

#### Deploy with Docker

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## Security Considerations

### 1. Environment Variables
- ❌ Never commit `.env` files to Git
- ✅ Use environment variable management (AWS Secrets Manager, HashiCorp Vault)
- ✅ Rotate JWT_SECRET periodically

### 2. Database Security
- ✅ Use strong, unique passwords
- ✅ Restrict IP access to known servers only
- ✅ Enable MongoDB authentication
- ✅ Regular backups (MongoDB Atlas does this automatically)

### 3. HTTPS/SSL
- ✅ Always use HTTPS in production
- ✅ Use Let's Encrypt for free SSL certificates
- ✅ Set up auto-renewal for certificates

### 4. Application Security
- ✅ JWT tokens expire after 24 hours
- ✅ Passwords are hashed with bcrypt
- ✅ CORS is configured to allow only your domain
- ✅ All API endpoints require authentication

### 5. File Upload Security
- ✅ File type validation
- ✅ File size limits
- ⚠️ Consider virus scanning for uploaded files
- ⚠️ Consider moving file storage to S3 with signed URLs

---

## Maintenance & Monitoring

### Database Backups

#### MongoDB Atlas (Automatic)
- Continuous backups included in paid tiers
- Point-in-time recovery available

#### Self-Hosted MongoDB
```bash
# Manual backup
mongodump --uri="mongodb://localhost:27017/brp_parts_portal" --out=/backups/$(date +%Y%m%d)

# Restore
mongorestore --uri="mongodb://localhost:27017" /backups/20240115
```

### Monitoring Recommendations

1. **Application Monitoring**
   - [Sentry](https://sentry.io) for error tracking
   - [New Relic](https://newrelic.com) for APM

2. **Infrastructure Monitoring**
   - [Datadog](https://www.datadoghq.com)
   - [AWS CloudWatch](https://aws.amazon.com/cloudwatch/)

3. **Uptime Monitoring**
   - [UptimeRobot](https://uptimerobot.com) (free tier available)
   - [Pingdom](https://www.pingdom.com)

### Log Management

```bash
# View backend logs
tail -f /var/log/brp-parts/backend.log

# View nginx access logs
tail -f /var/log/nginx/access.log
```

---

## Deployment Checklist

Before going live, ensure:

- [ ] MongoDB Atlas cluster is created and configured
- [ ] Database user created with proper permissions
- [ ] IP whitelist configured for production servers
- [ ] `.env` files configured with production values
- [ ] JWT_SECRET is a strong, random string
- [ ] CORS_ORIGINS set to your production domain only
- [ ] SSL certificate installed and working
- [ ] Initial admin user created
- [ ] Backup strategy in place
- [ ] Monitoring and alerting configured
- [ ] Test all features in staging environment

---

## Cost Estimates

### Minimum Production Setup (~$70-100/month)

| Service | Provider | Cost |
|---------|----------|------|
| Database | MongoDB Atlas M10 | $57/month |
| Server | DigitalOcean Droplet | $12/month |
| Domain | Namecheap | $10/year |
| SSL | Let's Encrypt | Free |
| **Total** | | **~$70/month** |

### Recommended Production Setup (~$200-300/month)

| Service | Provider | Cost |
|---------|----------|------|
| Database | MongoDB Atlas M20 | $140/month |
| Backend | AWS ECS/Fargate | $50/month |
| Frontend | AWS S3 + CloudFront | $10/month |
| Monitoring | Datadog | $15/month |
| **Total** | | **~$215/month** |

---

## Support

For technical support or questions:

- 📧 Email: support@yourcompany.com
- 📖 Documentation: https://docs.yourcompany.com
- 🐛 Issues: https://github.com/yourcompany/brp-parts-portal/issues

---

## License

Copyright © 2024 BRP Inc. All rights reserved.

This software is proprietary and confidential.

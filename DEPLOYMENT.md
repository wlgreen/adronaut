# Deployment Guide

This guide covers deployment options for the Adronaut MVP with recommended configurations for production.

## 🚀 Recommended Deployment Strategy

### **Frontend**: Vercel
### **Backend**: Railway
### **Database**: Supabase (hosted)

This combination provides:
- ✅ No timeout limits for AutoGen workflows
- ✅ Automatic scaling and zero-downtime deployments
- ✅ Easy environment management
- ✅ Cost-effective for MVP/production

---

## 🚂 Railway Backend Deployment

Railway is perfect for the AutoGen service because it supports long-running processes without timeout limits.

### Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Repository**: Your code should be in a GitHub repo
3. **Environment Variables**: Prepare your API keys

### Step 1: Deploy via GitHub

1. **Connect Repository**:
   ```bash
   # Go to railway.app
   # Click "Deploy from GitHub repo"
   # Select your adronaut repository
   # Choose the /service folder as root directory
   ```

2. **Railway will automatically detect**:
   - Python application
   - `requirements.txt` for dependencies
   - `railway.toml` for configuration

### Step 2: Configure Environment Variables

In your Railway dashboard, add these environment variables:

```env
# Required Environment Variables
OPENAI_API_KEY=sk-your-openai-api-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-service-role-key
PORT=8000
DEBUG=False

# Optional
PYTHONPATH=/app
PYTHONUNBUFFERED=1
```

### Step 3: Deploy

Railway will automatically:
1. Build your application using the Dockerfile
2. Install dependencies from `requirements.txt`
3. Start the service with `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Provide you with a public URL (e.g., `https://your-service.railway.app`)

### Railway Configuration Files

The following files are included for Railway deployment:

#### `railway.toml`
```toml
[build]
builder = "NIXPACKS"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

#### `Dockerfile`
- Optimized for Python 3.9
- Includes health checks
- Proper environment setup for AutoGen

#### `Procfile`
- Fallback process definition
- Compatible with multiple platforms

---

## 🌐 Vercel Frontend Deployment

Perfect for the Next.js application with automatic deployments.

### Step 1: Deploy Frontend

1. **Connect to Vercel**:
   ```bash
   # Go to vercel.com
   # Import your GitHub repository
   # Select the /web folder as root directory
   ```

2. **Vercel Auto-Configuration**:
   - Detects Next.js automatically
   - Configures build settings
   - Sets up automatic deployments

### Step 2: Environment Variables

In Vercel dashboard, add:

```env
# Frontend Environment Variables
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
NEXT_PUBLIC_AUTOGEN_SERVICE_URL=https://your-service.railway.app
NEXT_PUBLIC_OPENAI_API_KEY=sk-your-openai-api-key
```

### Step 3: Update CORS

Update your Railway service to allow Vercel domain:

```python
# In main.py, update CORS origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://your-app.vercel.app",  # Add your Vercel domain
        "https://*.vercel.app"  # Allow all Vercel preview deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🗄️ Supabase Database Setup

### Step 1: Create Project

1. Go to [supabase.com](https://supabase.com)
2. Create new project
3. Wait for setup completion

### Step 2: Run Schema

1. Go to SQL Editor in Supabase dashboard
2. Copy and paste the schema from `/docs/supabase-schema.sql`
3. Execute the script

### Step 3: Configure Storage

1. Go to Storage section
2. Verify `artifacts` bucket was created
3. Check storage policies are active

### Step 4: Get Credentials

Copy these from your Supabase dashboard:
- **Project URL**: `https://your-project.supabase.co`
- **Anon Key**: For frontend (public)
- **Service Role Key**: For backend (private)

---

## 🔧 Alternative Deployment Options

### Option 1: Docker Deployment

For any Docker-compatible platform:

```bash
# Build image
docker build -t adronaut-service ./service

# Run locally
docker run -p 8000:8000 --env-file .env adronaut-service

# Deploy to any cloud provider that supports Docker
```

### Option 2: Google Cloud Run

```bash
# Deploy to Cloud Run
gcloud run deploy adronaut-service \
  --source ./service \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Option 3: AWS ECS/Fargate

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker build -t adronaut-service ./service
docker tag adronaut-service:latest <account>.dkr.ecr.us-east-1.amazonaws.com/adronaut-service:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/adronaut-service:latest
```

### Option 4: Render

1. Connect GitHub repository
2. Select `/service` as root directory
3. Render auto-detects Python and uses Dockerfile
4. Add environment variables
5. Deploy

---

## 🔍 Health Checks & Monitoring

### Health Check Endpoint

The service includes a health check at `GET /`:

```json
{
  "message": "Adronaut AutoGen Service",
  "status": "running"
}
```

### Railway Monitoring

Railway provides built-in monitoring:
- **Metrics**: CPU, memory, network usage
- **Logs**: Real-time application logs
- **Deployments**: History and rollback options
- **Alerts**: Set up notifications for issues

### Vercel Monitoring

Vercel includes:
- **Analytics**: Page views and performance
- **Speed Insights**: Core Web Vitals
- **Function Logs**: Serverless function execution
- **Real User Monitoring**: Actual user experience

---

## 💰 Cost Estimation

### Railway (Backend)
- **Hobby Plan**: $5/month
- **Pro Plan**: $20/month (recommended for production)
- Includes: 512MB RAM, 1GB storage, unlimited bandwidth

### Vercel (Frontend)
- **Hobby Plan**: Free
- **Pro Plan**: $20/month (for commercial use)
- Includes: Unlimited bandwidth, automatic scaling

### Supabase (Database)
- **Free Tier**: 2 organizations, 500MB database
- **Pro Plan**: $25/month (recommended for production)
- Includes: 8GB database, 100GB bandwidth

**Total MVP Cost**: ~$50-65/month for production-ready deployment

---

## 🚀 Quick Deploy Commands

### Backend (Railway)
```bash
# Option 1: Railway CLI
npm install -g @railway/cli
railway login
railway link  # Link to existing project or create new
railway up    # Deploy from /service directory

# Option 2: GitHub Integration (Recommended)
# Connect repository at railway.app
# Select /service as root directory
# Add environment variables
# Deploy automatically
```

### Frontend (Vercel)
```bash
# Option 1: Vercel CLI
npm install -g vercel
cd web
vercel --prod

# Option 2: GitHub Integration (Recommended)
# Connect repository at vercel.com
# Select /web as root directory
# Add environment variables
# Deploy automatically
```

## 🔧 Production Optimizations

### Backend Optimizations

1. **Enable Production Mode**:
   ```env
   DEBUG=False
   ```

2. **Add Redis for Caching** (optional):
   ```bash
   # Add to requirements.txt
   redis==4.5.1
   ```

3. **Configure Logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.INFO)
   ```

### Frontend Optimizations

1. **Enable Analytics**:
   ```bash
   npm install @vercel/analytics
   ```

2. **Add Error Tracking**:
   ```bash
   npm install @sentry/nextjs
   ```

3. **Optimize Images**:
   ```jsx
   import Image from 'next/image'
   // Use Next.js Image optimization
   ```

---

## 🆘 Troubleshooting

### Common Issues

#### Railway Deployment Fails
```bash
# Check build logs in Railway dashboard
# Verify requirements.txt is complete
# Check Python version compatibility (3.9+)
```

#### Vercel Build Fails
```bash
# Check build logs in Vercel dashboard
# Verify all dependencies in package.json
# Check environment variables are set
```

#### CORS Errors
```python
# Update CORS origins in main.py
allow_origins=["https://your-app.vercel.app"]
```

#### Database Connection Issues
```bash
# Verify Supabase credentials
# Check network connectivity
# Ensure database schema is applied
```

### Getting Help

1. **Railway Support**: [docs.railway.app](https://docs.railway.app)
2. **Vercel Support**: [vercel.com/docs](https://vercel.com/docs)
3. **Supabase Support**: [supabase.com/docs](https://supabase.com/docs)

This deployment setup will give you a production-ready Adronaut MVP with automatic scaling, monitoring, and easy maintenance!
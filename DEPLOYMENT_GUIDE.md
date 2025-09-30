# 🚀 Adronaut Deployment Guide

## Quick Deploy to Vercel

### Prerequisites
- ✅ Railway backend deployed and running
- ✅ Supabase database configured
- ✅ GitHub repository with latest code

### 1. Deploy Frontend to Vercel

**Option A: One-Click Deploy**
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/your-username/adronaut&project-name=adronaut-web&repository-name=adronaut&root-directory=web)

**Option B: Manual Deploy**
1. Go to [vercel.com](https://vercel.com)
2. Click "Add New Project"
3. Import your GitHub repository
4. Set **Root Directory** to `web`
5. Click "Deploy"

### 2. Configure Environment Variables

In Vercel Dashboard → Settings → Environment Variables:

```env
NEXT_PUBLIC_AUTOGEN_SERVICE_URL=https://your-railway-app.railway.app
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

### 3. Update Backend CORS

Add your Vercel domain to Railway backend CORS:

```python
# In your Railway service/main.py
allow_origins=[
    "http://localhost:3000",
    "https://your-vercel-app.vercel.app",  # Add this
    "https://*.vercel.app",
]
```

### 4. Verify Deployment

✅ Frontend loads on Vercel URL
✅ Sidebar toggles properly
✅ Cards have visible borders
✅ Navigation works between pages
✅ Backend connection works (check Network tab)

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Vercel        │    │    Railway      │    │   Supabase      │
│   (Frontend)    │◄──►│   (Backend)     │◄──►│  (Database)     │
│                 │    │                 │    │                 │
│ • Next.js App   │    │ • FastAPI       │    │ • PostgreSQL    │
│ • New UI Design │    │ • AutoGen       │    │ • File Storage  │
│ • Premium Theme │    │ • AI Agents     │    │ • Real-time     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Post-Deployment Checklist

- [ ] Update README with live URLs
- [ ] Test complete workflow end-to-end
- [ ] Monitor performance and errors
- [ ] Set up analytics (optional)
- [ ] Configure custom domain (optional)

## Live URLs (Update After Deployment)

- **Frontend**: https://your-app.vercel.app
- **Backend**: https://your-service.railway.app
- **Database**: https://your-project.supabase.co

---
*Generated for Adronaut MVP - Premium Marketing Analytics Platform*
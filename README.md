# Adronaut MVP

A sci-fi themed marketing mission control system that helps marketers upload data artifacts, extract insights automatically, and manage audience strategies through LLM-powered agents.

## 🌟 Features

- **🚀 Workspace**: Upload data artifacts (CSV, JSON, PDF, images) and view AI-generated analysis snapshots
- **🎯 Strategy**: Mission control interface for HITL (Human-in-the-Loop) strategy management
- **📊 Results**: Real-time telemetry dashboard with campaign metrics and performance analysis
- **🤖 AutoGen Agents**: Multi-agent system for feature extraction, insights generation, and performance analysis
- **🎨 Sci-Fi UI**: Dark theme with neon accents, glowing effects, and holographic panels
- **🔄 Real-time Updates**: Server-Sent Events for live workflow progress
- **✏️ Natural Language Editing**: Edit AI proposals using plain English

## 🏗️ Architecture

### Three-Layer System

- **UI Layer**: Next.js with TypeScript and Tailwind CSS
- **Service Layer**: FastAPI with AutoGen orchestrator
- **Database Layer**: Supabase (PostgreSQL + Storage)

### Workflow

```
Upload → Analysis → Insights → HITL Approval → Strategy → Campaign → Metrics → Optimization
   ↓        ↓         ↓           ↓             ↓         ↓         ↓         ↓
Files → Features → Patches → Human Review → Brief → Launch → Collect → Analyze
```

## 📁 Project Structure

```
adronaut/
├── web/                    # Next.js frontend application
│   ├── src/app/           # Next.js App Router pages
│   ├── src/components/    # React components
│   ├── src/lib/          # Utilities and configurations
│   └── README.md         # Web app documentation
├── service/               # FastAPI backend with AutoGen
│   ├── main.py           # FastAPI application
│   ├── orchestrator.py   # AutoGen workflow orchestrator
│   ├── database.py       # Supabase database operations
│   ├── file_processor.py # File upload and processing
│   └── README.md         # Service documentation
├── docs/                 # Database schema and documentation
│   └── supabase-schema.sql
└── README.md            # This file
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.9+ and pip
- OpenAI API key
- Supabase account and project

### 1. Environment Setup

```bash
# Clone and enter directory
git clone <repository-url>
cd adronaut

# Copy environment files
cp web/.env.example web/.env.local
cp service/.env.example service/.env
```

### 2. Configure Environment Variables

**Web App (`web/.env.local`)**:
```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
NEXT_PUBLIC_AUTOGEN_SERVICE_URL=http://localhost:8000
NEXT_PUBLIC_OPENAI_API_KEY=your_openai_api_key
```

**Service (`service/.env`)**:
```env
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_role_key
PORT=8000
DEBUG=True
```

### 3. Database Setup

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Go to SQL Editor in your Supabase dashboard
3. Copy and execute the schema from `docs/supabase-schema.sql`

### 4. Install Dependencies

```bash
# Install web dependencies
cd web && npm install

# Install service dependencies
cd ../service && pip install -r requirements.txt
```

### 5. Run Development Servers

```bash
# Terminal 1: Start web app
cd web && npm run dev

# Terminal 2: Start AutoGen service
cd service && uvicorn main:app --reload --port 8000
```

### 6. Open Application

- **Web UI**: [http://localhost:3000](http://localhost:3000)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

## 🎮 Usage

### 1. Workspace - Data Upload

- Navigate to the Workspace page
- Drag & drop or select files (CSV, JSON, PDF, images)
- Click "Start Analysis" to begin feature extraction
- View AI-generated analysis snapshots with insights

### 2. Strategy - Mission Control

- Navigate to the Strategy page
- Review AI-proposed strategy patches
- **Approve**: Accept the patch as-is
- **Reject**: Discard the patch
- **Edit**: Use natural language to modify ("increase budget to $20k, focus on tech professionals")
- View active strategy and version history

### 3. Results - Telemetry Dashboard

- Navigate to the Results page
- Monitor campaign performance metrics
- Review AI-generated performance alerts
- Analyze trends and optimization opportunities

## 🤖 AI Agents

### AutoGen Agent Roles

1. **FeatureBuilder**: Extracts marketing features from uploaded files
2. **Insights Agent**: Generates strategic insights and proposes patches
3. **Analyzer Agent**: Analyzes campaign performance and suggests optimizations
4. **Patch Editor**: Edits strategy patches based on user natural language feedback

### HITL (Human-in-the-Loop) Process

1. AI agent proposes a strategy patch
2. Human reviews the proposal with justification
3. Human can approve, reject, or edit using natural language
4. If editing, LLM rewrites the patch based on feedback
5. Approved patches are applied to update the strategy

## 🎨 Design System

### Sci-Fi Theme

- **Colors**: Deep space grays, electric indigo, neon accents (emerald, cyan, rose, amber)
- **Typography**: Inter (body), Orbitron (headings), JetBrains Mono (code)
- **Effects**: Glowing borders, holographic panels, animated scan lines
- **Components**: Mission control cards, holo-dialogs, neon badges

### Key UI Components

- **Cards**: Holographic panels with glow variants
- **Buttons**: Sci-fi styled with pulse effects
- **Navigation**: Vertical sidebar with glowing indicators
- **Charts**: Neon data visualization with streaming animations
- **Dialogs**: Floating holo-panels with backdrop blur

## 🔧 Development

### Available Scripts

**Web App**:
```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run lint     # Run ESLint
```

**Service**:
```bash
uvicorn main:app --reload    # Start with auto-reload
python -m pytest            # Run tests (when added)
```

### Code Structure

- **TypeScript** for type safety
- **Async/await** for all database and API operations
- **Component-based architecture** with reusable UI components
- **Tailwind CSS** for styling with custom design system
- **AutoGen** for multi-agent orchestration

## 🚀 Deployment

### Frontend (Vercel - Recommended)

1. Connect repository to Vercel
2. Configure environment variables
3. Deploy with automatic git deployments

### Backend (Railway/Render)

1. Connect repository to hosting platform
2. Configure environment variables
3. Deploy FastAPI service with auto-scaling

## 📊 Data Flow

1. **Upload**: Files → Supabase Storage → Analysis
2. **Features**: AutoGen agents extract marketing insights
3. **Strategy**: AI proposes patches → HITL approval → Strategy updates
4. **Campaigns**: Strategy → Brief compilation → Campaign launch
5. **Results**: Metrics collection → Performance analysis → Optimization recommendations

## 🔍 Monitoring

- **Real-time Events**: SSE stream for workflow progress
- **Database Logging**: All operations logged in Supabase
- **Error Handling**: Comprehensive error capture and recovery
- **Performance Tracking**: Campaign metrics and AI agent performance

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is part of the Adronaut MVP system.

---

For detailed setup instructions, see:
- [Web App Documentation](./web/README.md)
- [Service Documentation](./service/README.md)
- [Database Schema](./docs/supabase-schema.sql)
# Adronaut AutoGen Service

The backend service for Adronaut - a FastAPI-based orchestrator that integrates AutoGen agents for marketing strategy automation.

## Features

- 🤖 **AutoGen Integration**: Multiple AI agents for feature extraction, insights, and analysis
- 🔄 **Workflow Orchestration**: Complete HITL (Human-in-the-Loop) workflow management
- 📁 **File Processing**: Support for CSV, JSON, PDF, and image analysis
- 🔐 **Deterministic Tools**: Validation, strategy editing, brief compilation
- 📡 **Real-time Events**: Server-Sent Events for workflow progress
- 🗄️ **Database Integration**: Supabase for data persistence

## Tech Stack

- **FastAPI** - High-performance async API framework
- **AutoGen** - Multi-agent conversation framework
- **OpenAI GPT-4** - Large language model for agents
- **Supabase** - Database and storage
- **Pandas** - Data processing
- **PyPDF2** - PDF text extraction
- **Pillow** - Image processing

## Prerequisites

- Python 3.9+ and pip
- OpenAI API key
- Supabase project with service role key

## Environment Setup

1. **Copy environment file**:
   ```bash
   cp .env.example .env
   ```

2. **Configure environment variables**:
   ```env
   # OpenAI Configuration
   OPENAI_API_KEY=your_openai_api_key

   # Supabase Configuration
   SUPABASE_URL=your_supabase_project_url
   SUPABASE_KEY=your_supabase_service_role_key

   # Service Configuration
   PORT=8000
   DEBUG=True
   ```

## Installation

1. **Create virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the service**:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

4. **Access API documentation**:
   Navigate to [http://localhost:8000/docs](http://localhost:8000/docs)

## Project Structure

```
service/
├── main.py                 # FastAPI application entry point
├── orchestrator.py         # AutoGen workflow orchestrator
├── database.py            # Supabase database operations
├── file_processor.py      # File upload and processing
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
└── README.md             # This file
```

## Core Components

### AutoGen Orchestrator (`orchestrator.py`)

Manages the complete workflow using multiple AI agents:

- **FeatureBuilder Agent**: Extracts marketing features from uploaded artifacts
- **Insights Agent**: Generates strategic insights and proposes patches
- **Analyzer Agent**: Analyzes campaign performance and suggests optimizations
- **Patch Editor**: Edits strategy patches based on user feedback

### Database Handler (`database.py`)

Provides async methods for all Supabase operations:

- Project and artifact management
- Strategy versions and patches
- Campaign and metrics tracking
- Workflow event logging

### File Processor (`file_processor.py`)

Handles file upload and analysis:

- **CSV**: Extracts marketing metrics and demographic data
- **JSON**: Analyzes structured data and API responses
- **PDF**: Extracts text content and metadata
- **Images**: Processes image metadata and basic analysis

## API Endpoints

### Core Operations

- `GET /` - Service status check
- `POST /upload` - Upload and process file artifacts
- `POST /autogen/run/start` - Start AutoGen workflow
- `POST /autogen/run/continue` - Continue workflow after HITL decision
- `GET /events/{run_id}` - Stream workflow events via SSE
- `GET /project/{project_id}/status` - Get project status and pending patches

### Workflow States

1. **INGEST** - Collect uploaded artifacts
2. **FEATURES** - Extract marketing features
3. **INSIGHTS** - Generate strategic insights
4. **PATCH_PROPOSED** - Propose strategy patch (HITL required)
5. **APPLY** - Apply approved patch to strategy
6. **BRIEF** - Compile marketing brief
7. **CAMPAIGN_RUN** - Launch simulated campaign
8. **COLLECT** - Gather performance metrics
9. **ANALYZE** - Analyze performance
10. **REFLECTION_PATCH_PROPOSED** - Propose optimization patch (HITL required)

## AutoGen Agent Configuration

### Agent Roles

1. **FeatureBuilder**:
   - Analyzes uploaded files
   - Extracts audience segments, content themes, performance metrics
   - Returns structured JSON with marketing insights

2. **Insights Agent**:
   - Takes extracted features as input
   - Generates strategic insights and recommendations
   - Proposes strategy patches with justifications

3. **Analyzer Agent**:
   - Reviews campaign performance metrics
   - Identifies optimization opportunities
   - Proposes reflection patches when needed

4. **Patch Editor**:
   - Takes user feedback in natural language
   - Edits existing strategy patches
   - Maintains JSON schema compliance

### Agent Prompts

Each agent has detailed system prompts that define their role, input/output format, and behavior. The prompts are designed to ensure consistent, structured responses that integrate with the deterministic workflow tools.

## HITL (Human-in-the-Loop) Flow

### Patch Approval Process

1. **Patch Proposed**: AI agent creates strategy patch
2. **Human Review**: User can approve, reject, or edit
3. **Natural Language Edit**: User describes changes in plain English
4. **LLM Rewrite**: Patch Editor agent rewrites patch based on feedback
5. **Apply**: Approved patch is applied to strategy

### Edit Request Examples

- "Increase the income threshold to 95k+ and focus on tech hubs"
- "Reduce the budget for social media and increase search ads"
- "Make the messaging more aggressive and competitive"

## Real-time Updates

The service uses Server-Sent Events (SSE) to provide real-time workflow updates:

```typescript
// Example client-side SSE consumption
const eventSource = new EventSource(`/events/${runId}`)
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data)
  console.log('Workflow update:', data)
}
```

### Event Format

```json
{
  "run_id": "uuid",
  "project_id": "uuid",
  "status": "running|completed|failed|hitl_required",
  "current_step": "FEATURES|INSIGHTS|PATCH_PROPOSED|...",
  "timestamp": "2024-09-28T15:30:00Z"
}
```

## Development

### Running in Development

```bash
# Start with auto-reload
uvicorn main:app --reload --port 8000

# Start with debug logging
DEBUG=True uvicorn main:app --reload --port 8000
```

### Testing Endpoints

Use the interactive API documentation at `/docs` or test with curl:

```bash
# Check service status
curl http://localhost:8000/

# Upload file
curl -X POST "http://localhost:8000/upload" \
  -F "file=@sample.csv" \
  -F "project_id=test-project"

# Start workflow
curl -X POST "http://localhost:8000/autogen/run/start" \
  -H "Content-Type: application/json" \
  -d '{"project_id": "test-project"}'
```

## Error Handling

The service implements comprehensive error handling:

- **Agent Failures**: Automatic retry with fallback responses
- **Database Errors**: Graceful degradation with logging
- **File Processing**: Error capture with detailed feedback
- **Workflow Interruptions**: State preservation and recovery

## Performance Considerations

- **Async Operations**: All database and LLM calls are async
- **Connection Pooling**: Supabase client manages connections
- **Memory Management**: File processing cleans up temporary files
- **Rate Limiting**: OpenAI API calls respect rate limits

## Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Cloud Deployment

The service can be deployed to:
- **Railway** - Simple Python app deployment
- **Render** - Web services with auto-deploy
- **Google Cloud Run** - Serverless containers
- **AWS ECS** - Container orchestration

## Monitoring

### Logging

The service logs all major operations:

```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

### Health Checks

- `GET /` returns service status
- Database connectivity checks
- AutoGen agent initialization status

## Troubleshooting

### Common Issues

1. **OpenAI API Errors**:
   - Check API key validity
   - Verify rate limits
   - Monitor token usage

2. **Supabase Connection**:
   - Verify service role key
   - Check database schema
   - Ensure network connectivity

3. **AutoGen Initialization**:
   - Verify all required packages installed
   - Check Python version compatibility
   - Monitor memory usage for large models

4. **File Processing**:
   - Check file format support
   - Verify file size limits
   - Monitor disk space for temporary files

### Debug Mode

Enable detailed logging:

```bash
DEBUG=True uvicorn main:app --reload
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is part of the Adronaut MVP system.
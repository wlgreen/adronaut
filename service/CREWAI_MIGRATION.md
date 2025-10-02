# CrewAI Framework Migration

This backend service has been migrated from AutoGen to CrewAI framework for better Gemini API integration and more sophisticated multi-agent workflows.

## Why CrewAI?

### Advantages over AutoGen

✅ **Native Gemini Support**: CrewAI has built-in LangChain integration for Gemini API
✅ **Better Multi-Agent Coordination**: More sophisticated agent orchestration
✅ **Flexible LLM Providers**: Easy switching between Gemini, OpenAI, and other providers
✅ **Task-Oriented Design**: Better suited for marketing strategy workflows
✅ **Rich Ecosystem**: Extensive tools and integrations
✅ **Active Development**: Rapidly evolving with modern AI features

### AutoGen Limitations

❌ **No Native Gemini Support**: Required custom API integration
❌ **OpenAI-Centric**: Designed primarily for OpenAI's API structure
❌ **Limited Flexibility**: Harder to customize agent behaviors
❌ **Conversation Focus**: Better for chat than structured task execution

## Changes Made

### 1. Dependencies Updated

**Removed:**
- `pyautogen==0.2.11`

**Added:**
- `crewai==0.86.0`
- `crewai-tools==0.17.0`
- `langchain-google-genai==2.2.0`
- `langchain-openai==0.2.10`

### 2. New Files

- `crew_orchestrator.py`: Complete CrewAI-based orchestrator
- `orchestrator_autogen_backup.py`: Backup of original AutoGen orchestrator

### 3. Agent Architecture

#### Marketing Analysis Crew

1. **Feature Builder Agent**
   - Role: Marketing Data Feature Extractor
   - Specializes in analyzing artifacts and extracting insights
   - Uses Gemini for pattern recognition and data analysis

2. **Insights Agent**
   - Role: Marketing Strategy Insights Expert
   - Generates strategic recommendations and strategy patches
   - Optimizes for audience targeting and messaging

3. **Performance Analyzer Agent**
   - Role: Marketing Performance Analyzer
   - Identifies optimization opportunities in campaigns
   - Provides data-driven adjustment recommendations

4. **Patch Editor Agent**
   - Role: Marketing Strategy Patch Editor
   - Handles user feedback and strategy modifications
   - Ensures consistency and validity of edits

### 4. Native Gemini Integration

```python
# CrewAI with native Gemini support
self.llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=self.gemini_api_key,
    temperature=0.7,
    convert_system_message_to_human=True
)
```

## Configuration

### Environment Variables

Same as before - no changes needed:

```env
# Primary LLM provider (Gemini)
GEMINI_API_KEY=your-actual-gemini-api-key-here

# Fallback LLM provider (OpenAI) - optional
OPENAI_API_KEY=your-openai-api-key-here

# Database
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
PORT=8000
```

## Workflow Improvements

### 1. Structured Task Execution

CrewAI uses a **Task-Crew-Agent** paradigm:

```python
# Define specific task
extraction_task = Task(
    description="Analyze marketing artifacts...",
    agent=self.feature_builder,
    expected_output="JSON object with features"
)

# Execute with crew
crew = Crew(
    agents=[self.feature_builder],
    tasks=[extraction_task],
    process=Process.sequential
)

result = crew.kickoff()
```

### 2. Better Error Handling

- Graceful fallbacks for each operation
- Structured logging and debugging
- Consistent JSON output parsing

### 3. Multi-Agent Coordination

CrewAI enables more sophisticated workflows:
- Agents can collaborate on complex tasks
- Sequential and parallel processing options
- Built-in memory and context sharing

## API Compatibility

### No Breaking Changes

All existing API endpoints remain the same:
- `/upload` - File upload and processing
- `/autogen/run/start` - Workflow initiation
- `/autogen/run/continue` - HITL decisions
- `/events/{run_id}` - Event streaming
- `/project/{project_id}/status` - Status queries

### Enhanced Capabilities

The CrewAI implementation provides:
- More reliable JSON parsing
- Better error recovery
- Improved agent reasoning
- Enhanced logging and debugging

## Testing Endpoints

### Health Check

```bash
GET /health
```

Returns CrewAI dependency status.

### CrewAI Test

```bash
GET /test-crewai
```

Returns:
```json
{
  "crewai": "✅",
  "version": "0.86.0",
  "gemini_configured": true,
  "llm_type": "ChatGoogleGenerativeAI"
}
```

## Deployment

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

In Railway dashboard, ensure:
- `GEMINI_API_KEY` is set with your API key
- Other environment variables remain unchanged

### 3. Deploy

```bash
git push origin main
```

### 4. Verify

Check logs for:
```
INFO - Using Gemini API with CrewAI
```

## Benefits Achieved

### Technical Benefits

✅ **Native Gemini Integration**: No more custom API wrappers
✅ **Better Agent Coordination**: More sophisticated multi-agent workflows
✅ **Improved Reliability**: Better error handling and fallbacks
✅ **Enhanced Logging**: More detailed operation tracking
✅ **Future-Proof**: Modern framework with active development

### Business Benefits

✅ **Faster Processing**: Optimized agent execution
✅ **Better Quality**: More reliable strategy generation
✅ **Scalability**: Easier to add new agent capabilities
✅ **Cost Optimization**: Better resource utilization with Gemini

## Migration Complete

✅ **Framework Migration**: AutoGen → CrewAI
✅ **Gemini Integration**: Native LangChain support
✅ **Agent Architecture**: Specialized marketing agents
✅ **API Compatibility**: No breaking changes
✅ **Enhanced Reliability**: Better error handling
✅ **Documentation**: Complete migration guide

The service now uses CrewAI with native Gemini integration for superior performance and reliability! 🚀
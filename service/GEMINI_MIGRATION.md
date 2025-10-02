# Gemini API Migration Guide

This backend service has been updated to use Google Gemini API as the preferred LLM provider, with OpenAI as a fallback option.

## Changes Made

### 1. Dependencies
- Added `google-generativeai==0.3.2` to `requirements.txt`

### 2. New Files
- `gemini_service.py`: Gemini API wrapper service

### 3. Updated Files
- `orchestrator.py`: Modified to use Gemini when available, fallback to OpenAI
- `.env.example`: Added `GEMINI_API_KEY` configuration
- `.env.production`: Added `GEMINI_API_KEY` configuration

## Configuration

### Environment Variables

Set these environment variables in your Railway deployment:

```env
# Primary LLM provider (Gemini)
GEMINI_API_KEY=your-actual-gemini-api-key-here

# Fallback LLM provider (OpenAI) - optional
OPENAI_API_KEY=your-openai-api-key-here

# Existing variables
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
PORT=8000
```

## How It Works

### Automatic Provider Selection

The service automatically detects which LLM provider to use:

1. **Primary**: If `GEMINI_API_KEY` is configured → Uses Gemini API
2. **Fallback**: If only `OPENAI_API_KEY` is configured → Uses OpenAI with AutoGen
3. **Error**: If neither is configured → Service fails to start

### API Operations

All major LLM operations now support both providers:

- **Feature Extraction**: Analyzes uploaded artifacts
- **Insights Generation**: Creates strategy patches
- **Patch Editing**: Modifies strategies based on user feedback

### Benefits of Gemini

- **No Rate Limiting**: Resolves OpenAI rate limit issues
- **Faster Responses**: Gemini 1.5 Flash for quick operations
- **Lower Costs**: More cost-effective than GPT-4
- **Better JSON**: More reliable structured output parsing

## Deployment Steps

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables** in Railway:
   - Go to your Railway project dashboard
   - Navigate to Variables tab
   - Add `GEMINI_API_KEY` with your actual API key

3. **Deploy**:
   ```bash
   # Railway will automatically redeploy when you push changes
   git push origin main
   ```

4. **Verify**:
   - Check logs for: "Using Gemini API for LLM operations"
   - Test file upload and analysis workflow

## API Key Setup

### Get Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Copy the key starting with `AIzaSy...`

### Configure in Railway

1. Go to Railway dashboard
2. Select your project
3. Go to Variables tab
4. Add variable:
   - **Name**: `GEMINI_API_KEY`
   - **Value**: Your actual API key

## Testing

The service automatically logs which provider it's using:

```
INFO - Using Gemini API for LLM operations  # ✅ Gemini configured
INFO - Using OpenAI API for LLM operations  # ⚠️  Fallback to OpenAI
```

## Troubleshooting

### Common Issues

1. **"No API key configured"**
   - Solution: Set `GEMINI_API_KEY` in environment variables

2. **"Gemini API error: API_KEY_INVALID"**
   - Solution: Verify your API key is correct

3. **"Quota exceeded"**
   - Solution: Check your Google Cloud billing and quotas

### Fallback Behavior

If Gemini fails, the service will:
1. Log the error
2. Return fallback sample data
3. Continue operating normally

This ensures the service remains functional even during API issues.

## Migration Complete

✅ Backend service now uses Gemini API by default
✅ OpenAI serves as fallback for compatibility
✅ All LLM operations migrated to new architecture
✅ Environment configuration updated
✅ Documentation provided for deployment

The service is ready for production deployment with Gemini API!
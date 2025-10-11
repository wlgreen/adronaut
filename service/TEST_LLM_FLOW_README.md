# LLM Flow Test Script

A comprehensive local testing tool for validating the complete LLM workflow with real artifact files.

**✨ NEW (Dec 2025):** Test script now **automatically syncs with production workflow** using `WorkflowEngine`. Any changes to the main workflow in `main.py` are instantly reflected in tests!

## Features

✅ **Auto-Sync with Production:** Uses `WorkflowEngine` - workflow changes automatically picked up
✅ **Complete Production Flow:** FEATURES → INSIGHTS → PATCH
✅ **Real LLM Calls:** Uses actual Gemini 2.5 Flash API
✅ **Detailed Logging:** Every LLM call logged with prompts and responses
✅ **Validation Checks:** Verifies output structure and required fields
✅ **Color-Coded Output:** Easy-to-read terminal output
✅ **Log Files:** Saves detailed logs for analysis

---

## Quick Start

### 1. **Setup Environment**
```bash
cd service

# Ensure .env has valid Gemini API key
cat .env | grep GEMINI_API_KEY
# Should show: GEMINI_API_KEY=your_actual_key_here
```

### 2. **Run Test with Sample Data**
```bash
python test_llm_flow.py test_sample_data.csv
```

### 3. **Run Test with Your Own Files**
```bash
# Single file
python test_llm_flow.py your_campaign_data.csv

# Multiple files
python test_llm_flow.py data1.csv data2.json report.pdf
```

---

## Usage

### **Basic Usage**
```bash
python test_llm_flow.py <artifact_file1> [artifact_file2] ...
```

### **Examples**

**Test with sample data:**
```bash
python test_llm_flow.py test_sample_data.csv
```

**Test with multiple files:**
```bash
python test_llm_flow.py campaign_metrics.csv audience_data.json creative_report.pdf
```

**Make script executable:**
```bash
chmod +x test_llm_flow.py
./test_llm_flow.py test_sample_data.csv
```

---

## What Gets Tested

### **Step 0: Artifact Processing**
- Reads file content
- Extracts text (supports CSV, JSON, TXT, PDF)
- Shows file size and preview

### **Step 1: FEATURES Extraction**
- Calls LLM @ temp=0.2
- Extracts structured features from artifacts
- Logs prompt and response
- Validates output structure

### **Step 2: INSIGHTS Generation**
- Calls LLM @ temp=0.35
- Generates k=5 insight candidates
- Scores and selects top 3 deterministically
- Validates required fields (11 fields)
- Shows impact scores and data support levels

### **Step 3: PATCH Generation**
- Calls LLM @ temp=0.2
- Generates strategy patch from insights
- Applies heuristic filters (budget, audience, creative)
- Runs sanity gate (LLM reflection @ temp=0.2)
- Shows validation flags and warnings
- Logs auto-downscope attempts

---

## Output Explained

### **Terminal Output**

```
================================================================================
📄 Processing artifact: test_sample_data.csv
================================================================================
   Size: 1,234 bytes
   Type: .csv

🔍 Extracting content...
   ✅ Extracted 1,200 characters

================================================================================
STEP 1: FEATURES EXTRACTION
================================================================================
📊 Processing 1 artifacts

🤖 Calling LLM for FEATURES extraction...
⏱️  Duration: 2.34s

📋 Extracted Features:
{
  "target_audience": {...},
  "metrics": {...},
  ...
}

✅ Validation:
   ✓ Valid dict structure
   ✓ Keys: ['target_audience', 'metrics', ...]

================================================================================
STEP 2: INSIGHTS GENERATION
================================================================================
🧠 Generating insight candidates...

🤖 Calling LLM for INSIGHTS (k=5 candidates)...
⏱️  Duration: 3.56s

📊 Insights Summary:
   Candidates evaluated: 5
   Selection method: deterministic_rubric
   Top insights selected: 3

   1. Insight (Score: 85/100):
      Primary lever: audience
      Data support: strong
      Confidence: 0.85
      Insight: Camp_002 shows highest ROAS (6.94-7.11) with consistent...
      Action: Reallocate 25% budget from underperforming Camp_003...
      Expected: increase ROAS by medium

✅ Validation:
   ✓ Exactly 3 insights returned
   ✓ Insight 1 has all required fields
   ✓ Insight 2 has all required fields
   ✓ Insight 3 has all required fields

================================================================================
STEP 3: PATCH GENERATION
================================================================================
🔧 Generating strategy patch with validation...

🤖 Calling LLM for PATCH generation...
⏱️  Duration: 4.12s

📋 Patch Generation Summary:
   Sanity review: safe
   Auto-downscoped: false
   Requires HITL review: false

🔍 Heuristic Validation:
   ✅ No heuristic violations

🛡️  Sanity Gate:
   ✅ No sanity concerns

📦 Patch Structure:
   - audience_targeting
   - messaging_strategy
   - channel_strategy
   - budget_allocation

================================================================================
✅ COMPLETE LLM FLOW TEST PASSED
================================================================================

📊 Summary:
   Artifacts processed: 1
   Features extracted: 8 keys
   Insights generated: 3
   Patch created: Yes

✅ Patch passed all validations

✅ Logs saved to: llm_test_20251008_173045.log
```

### **Log File Contents**

The log file contains timestamped entries for every operation:

```
[2025-10-08T17:30:45] ================================================================================
[2025-10-08T17:30:45] 📄 Processing artifact: test_sample_data.csv
[2025-10-08T17:30:45] ================================================================================
[2025-10-08T17:30:45]    Size: 1,234 bytes
[2025-10-08T17:30:45]    Type: .csv
[2025-10-08T17:30:45]
[2025-10-08T17:30:45] 🔍 Extracting content...
[2025-10-08T17:30:45]    ✅ Extracted 1,200 characters
...
[2025-10-08T17:30:48] 🤖 Calling LLM for FEATURES extraction...
[2025-10-08T17:30:50] ⏱️  Duration: 2.34s
[2025-10-08T17:30:50] 📋 Extracted Features:
[2025-10-08T17:30:50] {full JSON output}
...
```

---

## Validation Checks

### **FEATURES Validation**
- ✅ Output is a valid dict
- ✅ Contains expected keys
- ✅ JSON structure is valid

### **INSIGHTS Validation**
- ✅ Exactly 3 insights returned
- ✅ All 11 required fields present:
  - insight
  - hypothesis
  - proposed_action
  - primary_lever
  - expected_effect
  - confidence
  - data_support
  - evidence_refs
  - contrastive_reason
  - impact_rank (1-3)
  - impact_score (0-100)

### **PATCH Validation**
- ✅ Heuristic filters applied
- ✅ Sanity gate applied
- ✅ Annotations present (if violations)
- ✅ Auto-downscope attempted (if needed)

---

## Troubleshooting

### **Error: "GEMINI_API_KEY environment variable is required"**
```bash
# Check .env file
cat .env | grep GEMINI_API_KEY

# If missing, add it:
echo "GEMINI_API_KEY=your_actual_key_here" >> .env
```

### **Error: "File not found"**
```bash
# Check file path is correct
ls -la test_sample_data.csv

# Use absolute path if needed
python test_llm_flow.py /full/path/to/file.csv
```

### **Error: "No module named 'gemini_orchestrator'"**
```bash
# Ensure you're in service/ directory
cd service
python test_llm_flow.py test_sample_data.csv
```

### **LLM Returns Empty Response**
- Check Gemini API key is valid
- Check rate limits on API dashboard
- Check logs for error messages
- Try with smaller test file first

---

## Sample Test Data

The script includes `test_sample_data.csv` with:
- Campaign performance metrics (impressions, clicks, conversions, spend, revenue)
- Audience segment analysis
- Creative performance data
- Geographic insights
- Built-in recommendations for testing

This file is designed to trigger all validation paths:
- Strong data support (high ROAS campaigns)
- Moderate data support (mixed performance)
- Weak data support (underperforming campaigns)
- Budget reallocation opportunities (tests budget sanity)
- Multiple audience segments (tests audience overlap detection)

---

## Advanced Usage

### **Custom Log File Location**
```python
# Edit test_llm_flow.py, line ~50:
tester = LLMFlowTester(log_file="/path/to/custom_log.txt")
```

### **Inspect Specific Steps**
```python
# Run only FEATURES extraction
features = await tester.test_features_extraction(artifacts)

# Run only INSIGHTS generation
insights = await tester.test_insights_generation(features)

# Run only PATCH generation
patch = await tester.test_patch_generation(insights)
```

### **Test with Different Models**
```bash
# Temporarily override in .env
export LLM_INSIGHTS=gemini:gemini-2.5-pro  # Use Pro instead of Flash
python test_llm_flow.py test_sample_data.csv
```

---

## Interpreting Results

### **Good Results:**
```
✅ COMPLETE LLM FLOW TEST PASSED
   Artifacts processed: 1
   Features extracted: 8 keys
   Insights generated: 3
   Patch created: Yes
✅ Patch passed all validations
```

### **Warnings (May Be Normal):**
```
⚠️  Patch requires HITL review
   🔍 Heuristic Validation:
      ⚠️  1 flags:
         - budget_shift_exceeds_25_percent: total_shift=28.0%
   🛡️  Sanity Gate:
      ⚠️  1 flags:
         [MEDIUM] Budget increase is aggressive but supported by data
```

### **Errors (Need Investigation):**
```
❌ Insight 1 missing fields: ['evidence_refs', 'contrastive_reason']
❌ Expected 3 insights, got 2
❌ Invalid structure (not a dict)
```

---

## Performance Benchmarks

**Expected Latencies (Gemini 2.5 Flash):**
- FEATURES extraction: 1-3s
- INSIGHTS generation: 2-5s (k=5 candidates)
- PATCH generation: 3-6s (includes filters + sanity gate)
- **Total workflow: 6-14s**

**Token Usage (approximate):**
- FEATURES: ~2,000 tokens
- INSIGHTS: ~3,000 tokens
- PATCH: ~2,500 tokens
- Sanity gate: ~1,500 tokens
- **Total: ~9,000 tokens per test**

**Cost per Test (Gemini 2.5 Flash):**
- Input: ~6,000 tokens × $0.075/1M = $0.00045
- Output: ~3,000 tokens × $0.30/1M = $0.00090
- **Total: ~$0.00135 per test run**

---

## Integration with CI/CD

### **Run as Pre-Commit Check**
```bash
# .git/hooks/pre-commit
#!/bin/bash
cd service
python test_llm_flow.py test_sample_data.csv
if [ $? -ne 0 ]; then
    echo "LLM flow test failed"
    exit 1
fi
```

### **Run in GitHub Actions**
```yaml
- name: Test LLM Flow
  env:
    GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
  run: |
    cd service
    python test_llm_flow.py test_sample_data.csv
```

---

## Next Steps

After running this test successfully:

1. ✅ Verify log file has complete LLM interactions
2. ✅ Check insights have all required fields
3. ✅ Validate patch passes heuristic filters
4. ✅ Review sanity gate feedback
5. ✅ Test with your own real campaign data
6. ✅ Integrate into deployment pipeline

---

## Related Files

- `workflow_engine.py` - **NEW!** Reusable workflow logic (auto-sync with production)
- `test_llm_refactor.py` - Unit tests for foundation modules (29 tests)
- `test_sample_data.csv` - Sample campaign data for testing
- `gemini_orchestrator.py` - LLM orchestrator implementation
- `mechanics_cheat_sheet.py` - Metric→lever mappings
- `insights_selector.py` - Scoring and selection logic
- `heuristic_filters.py` - Validation filters
- `sanity_gate.py` - LLM reflection gate

## How Auto-Sync Works

The test script now uses `WorkflowEngine`, a shared module that contains the core workflow logic:

1. **`workflow_engine.py`** - Contains the production workflow (FEATURES → INSIGHTS → PATCH)
2. **`main.py`** - Uses `WorkflowEngine` for production API
3. **`test_llm_flow.py`** - Uses the **same `WorkflowEngine`** for local testing

**Result:** When you modify the workflow in `workflow_engine.py`, **both production and tests automatically pick up the changes**. No need to manually update the test script!

### What Gets Auto-Synced
- ✅ New workflow steps
- ✅ Modified LLM prompts
- ✅ Changed validation logic
- ✅ Updated temperature settings
- ✅ New heuristic filters
- ✅ Sanity gate changes

### What Stays Test-Specific
- ❌ Database writes (disabled for local tests)
- ❌ SSE status updates (production only)
- ❌ Color-coded logging (test-specific)
- ❌ Validation reporting (test-specific)

---

**Questions?** See `LLM_REFACTOR_COMPLETE.md` for full implementation details.

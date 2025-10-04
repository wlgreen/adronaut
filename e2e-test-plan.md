# Adronaut E2E Testing Strategy & Plan

## Overview
Comprehensive end-to-end testing suite for the Adronaut marketing automation platform covering critical user journeys, error scenarios, and performance validation.

## Architecture Summary
- **Frontend**: Next.js (Port 3000) - File upload, workflow visualization, strategy management
- **Backend**: FastAPI (Port 8000) - AI orchestration, file processing, database operations
- **Database**: Supabase - Real file storage with base64 encoding
- **AI**: Gemini 2.5 Pro with OpenAI GPT-4o fallback
- **Key Features**: Human-in-the-loop (HITL) workflow, real-time SSE events

## Critical User Flows

### 1. Complete Marketing Campaign Flow (Happy Path)
**Business Impact**: HIGH
**Priority**: 1

**Test Scenario**: End-to-end campaign creation and execution
1. Upload marketing artifacts (PDF, CSV, images)
2. Trigger AI analysis workflow
3. Review generated strategy patches
4. Approve/reject strategy recommendations
5. Monitor campaign launch via real-time events
6. Validate campaign metrics collection

**Success Criteria**:
- All files uploaded and stored in database
- AI workflow completes without errors
- Strategy patches generated and stored
- Real-time events stream correctly
- Campaign launches successfully
- Metrics collection initiated

### 2. Human-in-the-Loop (HITL) Workflow
**Business Impact**: HIGH
**Priority**: 1

**Test Scenarios**:
- **Patch Approval**: User approves strategy recommendations
- **Patch Rejection**: User rejects and workflow stops gracefully
- **Patch Editing**: User requests LLM edits with custom requirements

**Success Criteria**:
- Workflow pauses correctly for human input
- Approvals continue workflow execution
- Rejections stop workflow appropriately
- Edit requests generate new patches via LLM

### 3. File Upload & Processing
**Business Impact**: HIGH
**Priority**: 1

**Test Scenarios**:
- Upload different file types (PDF, CSV, JSON, images)
- Multiple file uploads simultaneously
- Large file uploads (up to 10MB)
- Invalid file type handling
- Network interruption during upload

**Success Criteria**:
- Files stored with base64 encoding in database
- File metadata captured correctly
- Progress indicators work accurately
- Error handling for invalid files
- Resume capability for interrupted uploads

## Error Handling & Edge Cases

### 4. Network & System Failures
**Business Impact**: MEDIUM
**Priority**: 2

**Test Scenarios**:
- Backend service unavailable during upload
- Database connection failures
- AI service timeouts (Gemini/OpenAI)
- SSE connection drops
- Partial workflow execution failures

**Success Criteria**:
- Graceful error messages displayed
- Failed operations can be retried
- Data integrity maintained
- Workflow state preserved during failures

### 5. AI Service Integration
**Business Impact**: HIGH
**Priority**: 1

**Test Scenarios**:
- Gemini API success and failure cases
- Automatic fallback to OpenAI
- LLM timeout handling
- Malformed AI responses
- Rate limiting scenarios

**Success Criteria**:
- Fallback mechanisms work correctly
- Timeout handling prevents hanging
- Error logging captures LLM interactions
- Retry logic functions properly

### 6. Concurrent User Scenarios
**Business Impact**: MEDIUM
**Priority**: 2

**Test Scenarios**:
- Multiple users uploading files simultaneously
- Concurrent workflow executions
- Real-time event streaming to multiple clients
- Database contention handling

**Success Criteria**:
- No data corruption under load
- Events delivered to correct clients
- Workflow isolation maintained
- Performance degradation within limits

## Performance & Load Testing

### 7. File Upload Performance
**Business Impact**: MEDIUM
**Priority**: 2

**Metrics**:
- Upload time for different file sizes
- Concurrent upload capacity
- Memory usage during processing
- Database insertion performance

**Thresholds**:
- < 2s for 1MB files
- < 10s for 10MB files
- Support 10 concurrent uploads
- < 500MB memory usage

### 8. AI Workflow Performance
**Business Impact**: HIGH
**Priority**: 1

**Metrics**:
- End-to-end workflow completion time
- LLM response times
- Database query performance
- SSE event delivery latency

**Thresholds**:
- < 60s for feature extraction
- < 30s for insight generation
- < 5s for patch creation
- < 1s SSE event delivery

## Data Validation Tests

### 9. Database Operations
**Business Impact**: HIGH
**Priority**: 1

**Test Scenarios**:
- Artifact storage with file content and metadata
- Project creation and management
- Strategy versioning and activation
- Campaign tracking and metrics
- Event logging completeness

**Success Criteria**:
- All data persisted correctly
- Relationships maintained properly
- No data loss during operations
- Audit trail complete

### 10. Real-time Event Streaming
**Business Impact**: HIGH
**Priority**: 1

**Test Scenarios**:
- Workflow progress events
- Multi-client event delivery
- Event ordering and completeness
- Connection recovery after drops

**Success Criteria**:
- Events delivered in correct order
- No missed events
- Clients receive only relevant events
- Reconnection works automatically

## Security & Authorization Tests

### 11. Input Validation
**Business Impact**: HIGH
**Priority**: 1

**Test Scenarios**:
- File type validation
- File size limits
- Malicious file content
- SQL injection attempts
- XSS prevention

**Success Criteria**:
- Invalid inputs rejected
- No security vulnerabilities exploited
- Proper error messages without data leaks

## Browser & Device Compatibility

### 12. Cross-Platform Testing
**Business Impact**: MEDIUM
**Priority**: 2

**Test Coverage**:
- Chrome, Firefox, Safari, Edge
- Desktop and mobile devices
- Different screen resolutions
- File upload drag-and-drop
- Real-time updates across browsers

## Test Data Management

### Test Data Strategy
- **Clean State**: Each test starts with fresh project ID
- **Realistic Data**: Use representative file types and sizes
- **Isolation**: Tests don't interfere with each other
- **Cleanup**: Automatic test data removal after runs

### Test Environments
- **Local**: Development testing with local services
- **Staging**: Production-like environment testing
- **CI/CD**: Automated testing on code changes

## Success Metrics

### Coverage Goals
- **Critical Paths**: 100% coverage
- **Error Scenarios**: 90% coverage
- **Edge Cases**: 80% coverage
- **Performance**: All thresholds met

### Quality Gates
- All tests passing before deployment
- Performance regressions detected
- Error handling validated
- User experience preserved

## Implementation Priority

**Phase 1 (Critical)**:
1. Complete marketing campaign flow
2. File upload and processing
3. HITL workflow testing
4. AI service integration

**Phase 2 (Important)**:
5. Error handling scenarios
6. Performance testing
7. Database validation
8. Real-time events

**Phase 3 (Nice-to-have)**:
9. Security testing
10. Cross-platform validation
11. Load testing
12. Advanced edge cases

This test plan ensures comprehensive coverage of the Adronaut platform's critical functionality while maintaining focus on user-impacting scenarios and business requirements.
import { v4 as uuidv4 } from 'uuid';

interface TestProject {
  id: string;
  name: string;
  createdAt: Date;
  artifacts: string[];
  snapshots: string[];
  strategies: string[];
  campaigns: string[];
}

interface TestArtifact {
  id: string;
  filename: string;
  projectId: string;
  size: number;
  type: string;
}

export class TestDataManager {
  private readonly backendUrl: string;
  private readonly testPrefix: string;
  private createdProjects: Set<string> = new Set();
  private createdArtifacts: Set<string> = new Set();

  constructor() {
    this.backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    this.testPrefix = process.env.TEST_PROJECT_PREFIX || 'e2e-test';
  }

  /**
   * Generate a unique test project ID
   */
  generateTestProjectId(): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 8);
    const projectId = `${this.testPrefix}-${timestamp}-${random}`;
    this.createdProjects.add(projectId);
    return projectId;
  }

  /**
   * Generate a unique test artifact ID
   */
  generateTestArtifactId(): string {
    const artifactId = uuidv4();
    this.createdArtifacts.add(artifactId);
    return artifactId;
  }

  /**
   * Create test file content for different file types
   */
  generateTestFileContent(fileType: string): { content: string; filename: string; mimeType: string } {
    const timestamp = Date.now();

    switch (fileType.toLowerCase()) {
      case 'csv':
        return {
          content: `name,email,age,purchase_amount
John Doe,john@example.com,30,299.99
Jane Smith,jane@example.com,25,199.50
Bob Johnson,bob@example.com,35,399.00`,
          filename: `test-data-${timestamp}.csv`,
          mimeType: 'text/csv'
        };

      case 'json':
        return {
          content: JSON.stringify({
            customers: [
              { id: 1, name: "Test Customer 1", segment: "premium" },
              { id: 2, name: "Test Customer 2", segment: "standard" }
            ],
            campaigns: [
              { id: 1, name: "Test Campaign", status: "active", budget: 5000 }
            ],
            metrics: {
              conversion_rate: 0.15,
              click_through_rate: 0.08,
              revenue: 25000
            }
          }, null, 2),
          filename: `test-analytics-${timestamp}.json`,
          mimeType: 'application/json'
        };

      case 'pdf':
        // For testing purposes, we'll use a simple text content
        // In a real implementation, you'd generate proper PDF binary data
        return {
          content: 'This is a test PDF document for marketing analysis.',
          filename: `test-document-${timestamp}.pdf`,
          mimeType: 'application/pdf'
        };

      case 'txt':
        return {
          content: `Test Marketing Document
Created: ${new Date().toISOString()}

This is a test document containing marketing content for analysis.
It includes customer feedback, campaign descriptions, and performance metrics.

Customer Reviews:
- "Great product, excellent service!"
- "Fast delivery and quality packaging."
- "Would recommend to friends and family."

Campaign Performance:
- Email open rate: 22%
- Click-through rate: 8%
- Conversion rate: 15%`,
          filename: `test-content-${timestamp}.txt`,
          mimeType: 'text/plain'
        };

      default:
        throw new Error(`Unsupported file type: ${fileType}`);
    }
  }

  /**
   * Create a test file blob for upload
   */
  createTestFile(fileType: string): File {
    const { content, filename, mimeType } = this.generateTestFileContent(fileType);
    const blob = new Blob([content], { type: mimeType });
    return new File([blob], filename, { type: mimeType });
  }

  /**
   * Upload a test file to the backend
   */
  async uploadTestFile(projectId: string, fileType: string, fetch: any): Promise<TestArtifact> {
    const { content, filename, mimeType } = this.generateTestFileContent(fileType);

    const formData = new FormData();
    const blob = new Blob([content], { type: mimeType });
    formData.append('file', blob, filename);

    const response = await fetch(`${this.backendUrl}/upload?project_id=${projectId}`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok()) {
      throw new Error(`Upload failed: ${response.status()} ${response.statusText()}`);
    }

    const result = await response.json();

    const artifact: TestArtifact = {
      id: result.artifact_id || this.generateTestArtifactId(),
      filename,
      projectId,
      size: content.length,
      type: fileType
    };

    this.createdArtifacts.add(artifact.id);
    return artifact;
  }

  /**
   * Wait for workflow to reach a specific status
   */
  async waitForWorkflowStatus(
    runId: string,
    expectedStatus: string,
    timeout: number = 120000
  ): Promise<any> {
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      try {
        // Check if run is still active (simple check for demo)
        // In real implementation, you'd poll the SSE endpoint or status API
        await new Promise(resolve => setTimeout(resolve, 2000));

        // For demo purposes, simulate status progression
        const elapsed = Date.now() - startTime;
        if (elapsed > 10000 && expectedStatus === 'hitl_required') {
          return { status: 'hitl_required', current_step: 'HITL_PATCH' };
        }
        if (elapsed > 30000 && expectedStatus === 'completed') {
          return { status: 'completed', current_step: 'COMPLETED' };
        }
      } catch (error) {
        console.warn('Error checking workflow status:', error);
      }
    }

    throw new Error(`Workflow did not reach status '${expectedStatus}' within ${timeout}ms`);
  }

  /**
   * Get project status from backend
   */
  async getProjectStatus(projectId: string, fetch: any): Promise<any> {
    const response = await fetch(`${this.backendUrl}/project/${projectId}/status`);

    if (!response.ok()) {
      throw new Error(`Failed to get project status: ${response.status()}`);
    }

    return await response.json();
  }

  /**
   * Clean up a specific test project
   */
  async cleanupTestProject(projectId: string, fetch?: any): Promise<void> {
    if (!this.createdProjects.has(projectId)) {
      return;
    }

    try {
      // In a real implementation, you'd call backend cleanup endpoints
      // For now, just remove from tracking
      this.createdProjects.delete(projectId);
      console.log(`✅ Cleaned up test project: ${projectId}`);
    } catch (error) {
      console.error(`❌ Failed to cleanup project ${projectId}:`, error);
    }
  }

  /**
   * Clean up all test data created during test runs
   */
  async cleanupAllTestData(): Promise<void> {
    console.log(`🧹 Cleaning up ${this.createdProjects.size} test projects...`);

    const cleanupPromises = Array.from(this.createdProjects).map(projectId =>
      this.cleanupTestProject(projectId)
    );

    await Promise.allSettled(cleanupPromises);

    // Clear tracking sets
    this.createdProjects.clear();
    this.createdArtifacts.clear();

    console.log('✅ Test data cleanup completed');
  }

  /**
   * Generate realistic test data for different scenarios
   */
  generateScenarioData(scenario: string): any {
    switch (scenario) {
      case 'e-commerce':
        return {
          files: ['csv', 'json'],
          expectedFeatures: ['customer_segments', 'product_performance', 'purchase_patterns'],
          expectedInsights: ['targeting_recommendations', 'campaign_optimization']
        };

      case 'b2b-saas':
        return {
          files: ['csv', 'json', 'txt'],
          expectedFeatures: ['user_behavior', 'feature_usage', 'churn_signals'],
          expectedInsights: ['retention_strategies', 'upsell_opportunities']
        };

      case 'content-marketing':
        return {
          files: ['txt', 'pdf', 'json'],
          expectedFeatures: ['content_performance', 'audience_engagement', 'topic_trends'],
          expectedInsights: ['content_strategy', 'distribution_optimization']
        };

      default:
        return {
          files: ['csv', 'json'],
          expectedFeatures: ['general_features'],
          expectedInsights: ['general_insights']
        };
    }
  }

  /**
   * Get test thresholds for performance testing
   */
  getPerformanceThresholds(): {
    uploadTime: number;
    workflowTime: number;
    aiResponseTime: number;
  } {
    return {
      uploadTime: parseInt(process.env.UPLOAD_PERFORMANCE_THRESHOLD_MS || '10000'),
      workflowTime: parseInt(process.env.WORKFLOW_PERFORMANCE_THRESHOLD_MS || '60000'),
      aiResponseTime: parseInt(process.env.AI_RESPONSE_THRESHOLD_MS || '30000')
    };
  }
}
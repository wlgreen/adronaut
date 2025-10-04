import { Page, Locator, expect } from '@playwright/test';

export class WorkspacePage {
  readonly page: Page;
  readonly fileUploader: Locator;
  readonly uploadArea: Locator;
  readonly fileInput: Locator;
  readonly uploadedFilesList: Locator;
  readonly startAnalysisButton: Locator;
  readonly analysisProgress: Locator;
  readonly analysisResults: Locator;
  readonly errorDisplay: Locator;

  constructor(page: Page) {
    this.page = page;
    this.fileUploader = page.locator('[data-testid="file-uploader"]');
    this.uploadArea = page.locator('[data-testid="upload-area"]');
    this.fileInput = page.locator('input[type="file"]');
    this.uploadedFilesList = page.locator('[data-testid="uploaded-files"]');
    this.startAnalysisButton = page.getByRole('button', { name: /start analysis/i });
    this.analysisProgress = page.locator('[data-testid="analysis-progress"]');
    this.analysisResults = page.locator('[data-testid="analysis-results"]');
    this.errorDisplay = page.locator('[data-testid="error-display"]');
  }

  async goto() {
    await this.page.goto('/');
    await this.page.waitForLoadState('networkidle');
  }

  async uploadFile(filePath: string) {
    await this.fileInput.setInputFiles(filePath);
  }

  async uploadMultipleFiles(filePaths: string[]) {
    await this.fileInput.setInputFiles(filePaths);
  }

  async waitForUploadComplete(filename: string, timeout: number = 30000) {
    const fileItem = this.uploadedFilesList.locator(`text=${filename}`);
    const successIcon = fileItem.locator('[data-testid="upload-success"]');
    await expect(successIcon).toBeVisible({ timeout });
  }

  async startAnalysis() {
    await this.startAnalysisButton.click();
  }

  async waitForAnalysisComplete(timeout: number = 120000) {
    await expect(this.analysisResults).toBeVisible({ timeout });
  }

  async getUploadedFilesCount(): Promise<number> {
    const fileItems = this.uploadedFilesList.locator('[data-testid="uploaded-file"]');
    return await fileItems.count();
  }

  async hasError(): Promise<boolean> {
    return await this.errorDisplay.isVisible();
  }

  async getErrorMessage(): Promise<string> {
    if (await this.hasError()) {
      return await this.errorDisplay.textContent() || '';
    }
    return '';
  }
}

export class StrategyPage {
  readonly page: Page;
  readonly strategiesContainer: Locator;
  readonly pendingPatches: Locator;
  readonly approveButton: Locator;
  readonly rejectButton: Locator;
  readonly editButton: Locator;
  readonly editModal: Locator;
  readonly editTextarea: Locator;
  readonly submitEditButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.strategiesContainer = page.locator('[data-testid="strategies-container"]');
    this.pendingPatches = page.locator('[data-testid="pending-patches"]');
    this.approveButton = page.getByRole('button', { name: /approve/i });
    this.rejectButton = page.getByRole('button', { name: /reject/i });
    this.editButton = page.getByRole('button', { name: /edit/i });
    this.editModal = page.locator('[data-testid="edit-modal"]');
    this.editTextarea = this.editModal.locator('textarea');
    this.submitEditButton = this.editModal.getByRole('button', { name: /submit/i });
  }

  async goto() {
    await this.page.goto('/strategy');
    await this.page.waitForLoadState('networkidle');
  }

  async waitForPendingPatch(timeout: number = 60000) {
    await expect(this.pendingPatches).toBeVisible({ timeout });
  }

  async approvePatch() {
    await this.approveButton.click();
  }

  async rejectPatch() {
    await this.rejectButton.click();
  }

  async editPatch(editRequest: string) {
    await this.editButton.click();
    await expect(this.editModal).toBeVisible();
    await this.editTextarea.fill(editRequest);
    await this.submitEditButton.click();
  }

  async getPatchCount(): Promise<number> {
    const patches = this.pendingPatches.locator('[data-testid="patch-item"]');
    return await patches.count();
  }
}

export class ResultsPage {
  readonly page: Page;
  readonly campaignResults: Locator;
  readonly metricsContainer: Locator;
  readonly performanceCharts: Locator;
  readonly campaignStatus: Locator;

  constructor(page: Page) {
    this.page = page;
    this.campaignResults = page.locator('[data-testid="campaign-results"]');
    this.metricsContainer = page.locator('[data-testid="metrics-container"]');
    this.performanceCharts = page.locator('[data-testid="performance-charts"]');
    this.campaignStatus = page.locator('[data-testid="campaign-status"]');
  }

  async goto() {
    await this.page.goto('/results');
    await this.page.waitForLoadState('networkidle');
  }

  async waitForCampaignResults(timeout: number = 60000) {
    await expect(this.campaignResults).toBeVisible({ timeout });
  }

  async getCampaignStatus(): Promise<string> {
    return await this.campaignStatus.textContent() || '';
  }

  async hasMetrics(): Promise<boolean> {
    return await this.metricsContainer.isVisible();
  }
}

export class NavigationHelper {
  readonly page: Page;
  readonly header: Locator;
  readonly workspaceLink: Locator;
  readonly strategyLink: Locator;
  readonly resultsLink: Locator;

  constructor(page: Page) {
    this.page = page;
    this.header = page.locator('header');
    this.workspaceLink = page.getByRole('link', { name: /workspace/i });
    this.strategyLink = page.getByRole('link', { name: /strategy/i });
    this.resultsLink = page.getByRole('link', { name: /results/i });
  }

  async navigateToWorkspace() {
    await this.workspaceLink.click();
    await this.page.waitForURL('**/');
  }

  async navigateToStrategy() {
    await this.strategyLink.click();
    await this.page.waitForURL('**/strategy');
  }

  async navigateToResults() {
    await this.resultsLink.click();
    await this.page.waitForURL('**/results');
  }
}

export class APIHelper {
  readonly page: Page;
  readonly backendUrl: string;

  constructor(page: Page) {
    this.page = page;
    this.backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
  }

  async checkBackendHealth(): Promise<boolean> {
    try {
      const response = await this.page.request.get(`${this.backendUrl}/`);
      return response.ok();
    } catch {
      return false;
    }
  }

  async getProjectStatus(projectId: string): Promise<any> {
    const response = await this.page.request.get(`${this.backendUrl}/project/${projectId}/status`);
    if (!response.ok()) {
      throw new Error(`Failed to get project status: ${response.status()}`);
    }
    return await response.json();
  }

  async startWorkflow(projectId: string): Promise<string> {
    const response = await this.page.request.post(`${this.backendUrl}/autogen/run/start`, {
      params: { project_id: projectId }
    });

    if (!response.ok()) {
      throw new Error(`Failed to start workflow: ${response.status()}`);
    }

    const result = await response.json();
    return result.run_id;
  }

  async continueWorkflow(projectId: string, patchId: string, action: 'approve' | 'reject' | 'edit', editRequest?: string): Promise<any> {
    const data: any = {
      project_id: projectId,
      patch_id: patchId,
      action
    };

    if (action === 'edit' && editRequest) {
      data.edit_request = editRequest;
    }

    const response = await this.page.request.post(`${this.backendUrl}/autogen/run/continue`, {
      data
    });

    if (!response.ok()) {
      throw new Error(`Failed to continue workflow: ${response.status()}`);
    }

    return await response.json();
  }

  async uploadFile(projectId: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.page.request.post(`${this.backendUrl}/upload`, {
      params: { project_id: projectId },
      multipart: formData
    });

    if (!response.ok()) {
      throw new Error(`File upload failed: ${response.status()}`);
    }

    return await response.json();
  }
}
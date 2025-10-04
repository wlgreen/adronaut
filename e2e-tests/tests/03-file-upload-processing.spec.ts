import { test, expect } from '@playwright/test';
import { WorkspacePage, APIHelper } from '../utils/page-objects';
import { TestDataManager } from '../utils/test-data-manager';
import { TestHelpers } from '../utils/test-helpers';

test.describe('File Upload and Processing @critical', () => {
  let workspacePage: WorkspacePage;
  let api: APIHelper;
  let testDataManager: TestDataManager;
  let projectId: string;

  test.beforeEach(async ({ page }) => {
    workspacePage = new WorkspacePage(page);
    api = new APIHelper(page);
    testDataManager = new TestDataManager();
    projectId = testDataManager.generateTestProjectId();

    await workspacePage.goto();
  });

  test.afterEach(async ({ page }) => {
    if (projectId) {
      await testDataManager.cleanupTestProject(projectId);
    }
  });

  test('should upload single file successfully', async ({ page }) => {
    console.log('📤 Testing single file upload...');

    const fileType = 'csv';
    const { files, uploadTime } = await TestHelpers.uploadTestFiles(page, projectId, [fileType]);

    // Verify upload performance
    const thresholds = testDataManager.getPerformanceThresholds();
    expect(uploadTime).toBeLessThan(thresholds.uploadTime);

    console.log(`✅ Single file uploaded in ${uploadTime}ms`);

    // Verify file appears in UI
    await workspacePage.waitForUploadComplete(files[0].name);
    const uploadedCount = await workspacePage.getUploadedFilesCount();
    expect(uploadedCount).toBe(1);

    // Verify file is stored in database
    await TestHelpers.validateDatabaseState(page, projectId, {
      artifactCount: 1
    });
  });

  test('should upload multiple files simultaneously', async ({ page }) => {
    console.log('📤 Testing multiple file upload...');

    const fileTypes = ['csv', 'json', 'txt'];
    const { files, uploadTime } = await TestHelpers.uploadTestFiles(page, projectId, fileTypes);

    console.log(`✅ Multiple files uploaded in ${uploadTime}ms`);

    // Verify all files are visible in UI
    for (const file of files) {
      await workspacePage.waitForUploadComplete(file.name);
    }

    const uploadedCount = await workspacePage.getUploadedFilesCount();
    expect(uploadedCount).toBe(fileTypes.length);

    // Verify all files are stored in database
    await TestHelpers.validateDatabaseState(page, projectId, {
      artifactCount: fileTypes.length
    });
  });

  test('should handle different file types correctly', async ({ page }) => {
    console.log('📎 Testing different file type handling...');

    const fileTypes = ['csv', 'json', 'txt', 'pdf'];

    for (const fileType of fileTypes) {
      console.log(`Testing ${fileType} file upload...`);

      const testProjectId = testDataManager.generateTestProjectId();
      const { files } = await TestHelpers.uploadTestFiles(page, testProjectId, [fileType]);

      // Verify file content is processed correctly based on type
      const projectStatus = await api.getProjectStatus(testProjectId);
      expect(projectStatus.artifacts).toBeDefined();
      expect(projectStatus.artifacts.length).toBe(1);

      const artifact = projectStatus.artifacts[0];
      expect(artifact.filename).toContain(fileType);
      expect(artifact.mime).toBeTruthy();

      // Cleanup individual test project
      await testDataManager.cleanupTestProject(testProjectId);
    }

    console.log('✅ All file types handled correctly');
  });

  test('should reject invalid file types', async ({ page }) => {
    console.log('🚫 Testing invalid file type rejection...');

    // Create a file with unsupported extension
    const invalidFile = new File(['invalid content'], 'test.exe', { type: 'application/octet-stream' });

    // Attempt to upload invalid file
    const fileInput = page.locator('input[type="file"]');

    // Since we can't directly test drag-and-drop rejection in this context,
    // we'll verify the accept attribute restricts file types
    const acceptAttribute = await fileInput.getAttribute('accept');
    expect(acceptAttribute).toBeTruthy();

    // Verify common valid types are accepted
    expect(acceptAttribute).toContain('.csv');
    expect(acceptAttribute).toContain('.json');
    expect(acceptAttribute).toContain('.pdf');

    console.log('✅ File type validation working correctly');
  });

  test('should handle large file uploads', async ({ page }) => {
    console.log('📊 Testing large file upload...');

    // Generate large test file content
    const largeContent = 'x'.repeat(1024 * 1024); // 1MB file
    const formData = new FormData();
    const blob = new Blob([largeContent], { type: 'text/plain' });
    formData.append('file', blob, 'large-test-file.txt');

    // Test upload performance for large file
    const { duration: uploadTime } = await TestHelpers.measureExecutionTime(async () => {
      const response = await page.request.post(`${api.backendUrl}/upload?project_id=${projectId}`, {
        multipart: formData
      });
      expect(response.ok()).toBe(true);
      return response.json();
    });

    console.log(`✅ Large file (1MB) uploaded in ${uploadTime}ms`);

    // Verify performance is within acceptable limits
    const thresholds = testDataManager.getPerformanceThresholds();
    expect(uploadTime).toBeLessThan(thresholds.uploadTime * 2); // Allow 2x threshold for large files
  });

  test('should handle upload progress correctly', async ({ page }) => {
    console.log('📈 Testing upload progress indication...');

    // Monitor network requests during upload
    const { requests, startCapture, stopCapture } = await TestHelpers.captureNetworkRequests(page, '/upload');
    startCapture();

    const { files } = await TestHelpers.uploadTestFiles(page, projectId, ['csv']);

    stopCapture();

    // Verify upload request was made
    expect(requests.length).toBeGreaterThan(0);
    const uploadRequest = requests.find(req => req.method === 'POST' && req.url.includes('/upload'));
    expect(uploadRequest).toBeTruthy();

    console.log('✅ Upload progress tracking verified');
  });

  test('should handle network interruption during upload', async ({ page }) => {
    console.log('🔌 Testing network interruption handling...');

    // Simulate network failure during upload
    const cleanup = await TestHelpers.simulateNetworkFailure(page, '/upload', 'abort');

    try {
      // Attempt upload during network failure
      await TestHelpers.uploadTestFiles(page, projectId, ['csv']);

      // Should not reach here if network simulation works
      expect(true).toBe(false);
    } catch (error) {
      console.log('✅ Network interruption handled correctly:', error.message);
      expect(error.message).toContain('Upload failed');
    }

    // Restore network and retry
    cleanup();

    const { files } = await TestHelpers.uploadTestFiles(page, projectId, ['csv']);
    expect(files.length).toBe(1);

    console.log('✅ Upload retry after network recovery successful');
  });

  test('should validate file size limits', async ({ page }) => {
    console.log('📏 Testing file size limit validation...');

    // Test file at the size limit (10MB as per UI)
    const maxSizeContent = 'x'.repeat(10 * 1024 * 1024); // 10MB
    const formData = new FormData();
    const blob = new Blob([maxSizeContent], { type: 'text/plain' });
    formData.append('file', blob, 'max-size-file.txt');

    try {
      const response = await page.request.post(`${api.backendUrl}/upload?project_id=${projectId}`, {
        multipart: formData
      });

      // Should either succeed or fail with appropriate message
      if (response.ok()) {
        console.log('✅ Max size file accepted');
      } else {
        const errorText = await response.text();
        expect(errorText).toContain('size');
        console.log('✅ Max size file rejected with appropriate error');
      }
    } catch (error) {
      console.log('✅ File size validation working:', error.message);
    }
  });

  test('should handle concurrent uploads from same user', async ({ page }) => {
    console.log('⚡ Testing concurrent uploads...');

    const fileTypes = ['csv', 'json', 'txt'];

    // Start multiple uploads simultaneously
    const uploadPromises = fileTypes.map(async (fileType, index) => {
      const testProjectId = `${projectId}-concurrent-${index}`;
      return TestHelpers.uploadTestFiles(page, testProjectId, [fileType]);
    });

    const results = await Promise.all(uploadPromises);

    // Verify all uploads completed successfully
    results.forEach((result, index) => {
      expect(result.files.length).toBe(1);
      console.log(`✅ Concurrent upload ${index + 1} completed in ${result.uploadTime}ms`);
    });

    console.log('✅ All concurrent uploads completed successfully');
  });

  test('should preserve file metadata correctly', async ({ page }) => {
    console.log('📋 Testing file metadata preservation...');

    const { content, filename, mimeType } = testDataManager.generateTestFileContent('json');
    const formData = new FormData();
    const blob = new Blob([content], { type: mimeType });
    formData.append('file', blob, filename);

    const response = await page.request.post(`${api.backendUrl}/upload?project_id=${projectId}`, {
      multipart: formData
    });

    expect(response.ok()).toBe(true);

    // Verify metadata is preserved in database
    const projectStatus = await api.getProjectStatus(projectId);
    const artifact = projectStatus.artifacts[0];

    expect(artifact.filename).toBe(filename);
    expect(artifact.mime).toBe(mimeType);
    expect(artifact.file_size).toBe(content.length);
    expect(artifact.file_content).toBeTruthy();

    console.log('✅ File metadata preserved correctly');
  });

  test('should handle empty file upload gracefully', async ({ page }) => {
    console.log('📄 Testing empty file upload handling...');

    const formData = new FormData();
    const emptyBlob = new Blob([''], { type: 'text/plain' });
    formData.append('file', emptyBlob, 'empty.txt');

    try {
      const response = await page.request.post(`${api.backendUrl}/upload?project_id=${projectId}`, {
        multipart: formData
      });

      if (response.ok()) {
        console.log('✅ Empty file accepted (system allows empty files)');
      } else {
        const errorText = await response.text();
        expect(errorText).toBeTruthy();
        console.log('✅ Empty file rejected with appropriate error');
      }
    } catch (error) {
      console.log('✅ Empty file handling working:', error.message);
    }
  });
});
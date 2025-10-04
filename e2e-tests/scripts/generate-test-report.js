#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

/**
 * Generate consolidated test report from multiple test result artifacts
 */
class TestReportGenerator {
  constructor(artifactsPath) {
    this.artifactsPath = artifactsPath;
    this.reportDir = path.join(__dirname, '../test-reports');
    this.results = {
      critical: [],
      smoke: [],
      performance: [],
      crossBrowser: [],
      security: []
    };
  }

  /**
   * Process all test artifacts and generate reports
   */
  async generateReport() {
    console.log('🎯 Generating consolidated test report...');

    // Ensure report directory exists
    if (!fs.existsSync(this.reportDir)) {
      fs.mkdirSync(this.reportDir, { recursive: true });
    }

    // Collect all test results
    await this.collectTestResults();

    // Generate reports
    await this.generateHTMLReport();
    await this.generateMarkdownSummary();
    await this.generateJSONReport();

    console.log('✅ Test report generated successfully');
  }

  /**
   * Collect test results from all artifacts
   */
  async collectTestResults() {
    console.log('📊 Collecting test results...');

    if (!fs.existsSync(this.artifactsPath)) {
      console.warn('⚠️ Artifacts path not found:', this.artifactsPath);
      return;
    }

    const artifactDirs = fs.readdirSync(this.artifactsPath)
      .filter(dir => fs.statSync(path.join(this.artifactsPath, dir)).isDirectory());

    for (const dir of artifactDirs) {
      const artifactPath = path.join(this.artifactsPath, dir);
      console.log(`Processing artifact: ${dir}`);

      // Look for JSON test results
      const resultsPath = path.join(artifactPath, 'results.json');
      if (fs.existsSync(resultsPath)) {
        try {
          const results = JSON.parse(fs.readFileSync(resultsPath, 'utf8'));
          this.categorizeResults(dir, results);
        } catch (error) {
          console.error(`Error parsing ${resultsPath}:`, error.message);
        }
      }

      // Look for JUnit XML results
      const junitPath = path.join(artifactPath, 'junit.xml');
      if (fs.existsSync(junitPath)) {
        // Parse JUnit XML if needed
        console.log(`Found JUnit results: ${junitPath}`);
      }
    }
  }

  /**
   * Categorize test results by type
   */
  categorizeResults(artifactName, results) {
    if (artifactName.includes('critical')) {
      this.results.critical.push({ artifact: artifactName, ...results });
    } else if (artifactName.includes('smoke')) {
      this.results.smoke.push({ artifact: artifactName, ...results });
    } else if (artifactName.includes('performance')) {
      this.results.performance.push({ artifact: artifactName, ...results });
    } else if (artifactName.includes('cross-browser')) {
      this.results.crossBrowser.push({ artifact: artifactName, ...results });
    } else if (artifactName.includes('security')) {
      this.results.security.push({ artifact: artifactName, ...results });
    }
  }

  /**
   * Generate HTML report
   */
  async generateHTMLReport() {
    console.log('📄 Generating HTML report...');

    const htmlTemplate = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Adronaut E2E Test Report</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; }
        .header h1 { margin: 0; font-size: 2.5em; }
        .header p { margin: 10px 0 0 0; opacity: 0.9; }
        .content { padding: 30px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 40px; }
        .metric-card { background: #f8f9fa; border-radius: 8px; padding: 20px; border-left: 4px solid #007bff; }
        .metric-card.success { border-left-color: #28a745; }
        .metric-card.warning { border-left-color: #ffc107; }
        .metric-card.error { border-left-color: #dc3545; }
        .metric-value { font-size: 2em; font-weight: bold; margin: 10px 0; }
        .section { margin-bottom: 40px; }
        .section h2 { color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        .test-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .test-card { border: 1px solid #ddd; border-radius: 8px; padding: 20px; }
        .test-card.passed { border-left: 4px solid #28a745; }
        .test-card.failed { border-left: 4px solid #dc3545; }
        .test-card.skipped { border-left: 4px solid #6c757d; }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold; }
        .badge.success { background: #d4edda; color: #155724; }
        .badge.danger { background: #f8d7da; color: #721c24; }
        .badge.secondary { background: #e2e3e5; color: #383d41; }
        .performance-chart { background: #f8f9fa; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .footer { text-align: center; color: #666; padding: 20px; border-top: 1px solid #eee; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Adronaut E2E Test Report</h1>
            <p>Generated on ${new Date().toLocaleString()}</p>
        </div>

        <div class="content">
            ${this.generateSummarySection()}
            ${this.generateTestSections()}
            ${this.generatePerformanceSection()}
        </div>

        <div class="footer">
            <p>Generated by Adronaut E2E Test Suite • <a href="https://github.com/adronaut/e2e-tests">View on GitHub</a></p>
        </div>
    </div>
</body>
</html>`;

    fs.writeFileSync(path.join(this.reportDir, 'index.html'), htmlTemplate);
  }

  /**
   * Generate summary section for HTML report
   */
  generateSummarySection() {
    const totalTests = this.getTotalTestCount();
    const passedTests = this.getPassedTestCount();
    const failedTests = this.getFailedTestCount();
    const successRate = totalTests > 0 ? ((passedTests / totalTests) * 100).toFixed(1) : 0;

    return `
    <div class="section">
        <h2>📊 Test Summary</h2>
        <div class="summary">
            <div class="metric-card success">
                <div class="metric-label">Total Tests</div>
                <div class="metric-value">${totalTests}</div>
            </div>
            <div class="metric-card success">
                <div class="metric-label">Passed</div>
                <div class="metric-value">${passedTests}</div>
            </div>
            <div class="metric-card ${failedTests > 0 ? 'error' : 'success'}">
                <div class="metric-label">Failed</div>
                <div class="metric-value">${failedTests}</div>
            </div>
            <div class="metric-card ${successRate < 95 ? 'warning' : 'success'}">
                <div class="metric-label">Success Rate</div>
                <div class="metric-value">${successRate}%</div>
            </div>
        </div>
    </div>`;
  }

  /**
   * Generate test sections for HTML report
   */
  generateTestSections() {
    let sections = '';

    if (this.results.critical.length > 0) {
      sections += this.generateTestSection('Critical Tests', this.results.critical, '🔴');
    }

    if (this.results.smoke.length > 0) {
      sections += this.generateTestSection('Smoke Tests', this.results.smoke, '💨');
    }

    if (this.results.crossBrowser.length > 0) {
      sections += this.generateTestSection('Cross-Browser Tests', this.results.crossBrowser, '🌐');
    }

    if (this.results.security.length > 0) {
      sections += this.generateTestSection('Security Tests', this.results.security, '🔒');
    }

    return sections;
  }

  /**
   * Generate individual test section
   */
  generateTestSection(title, results, icon) {
    const testCards = results.map(result => {
      const status = this.getResultStatus(result);
      return `
      <div class="test-card ${status}">
          <h4>${result.artifact}</h4>
          <div class="badge ${status === 'passed' ? 'success' : status === 'failed' ? 'danger' : 'secondary'}">
              ${status.toUpperCase()}
          </div>
          <p>Duration: ${this.getResultDuration(result)}ms</p>
          ${result.error ? `<p style="color: #dc3545;">Error: ${result.error}</p>` : ''}
      </div>`;
    }).join('');

    return `
    <div class="section">
        <h2>${icon} ${title}</h2>
        <div class="test-grid">
            ${testCards}
        </div>
    </div>`;
  }

  /**
   * Generate performance section
   */
  generatePerformanceSection() {
    if (this.results.performance.length === 0) {
      return '';
    }

    return `
    <div class="section">
        <h2>⚡ Performance Metrics</h2>
        <div class="performance-chart">
            <h3>Performance Trends</h3>
            <p>Upload Time Threshold: 10s | Workflow Time Threshold: 60s</p>
            ${this.generatePerformanceTable()}
        </div>
    </div>`;
  }

  /**
   * Generate performance table
   */
  generatePerformanceTable() {
    const performanceData = this.results.performance.map(result => {
      return `
      <tr>
          <td>${result.artifact}</td>
          <td>${this.getPerformanceMetric(result, 'uploadTime') || 'N/A'}</td>
          <td>${this.getPerformanceMetric(result, 'workflowTime') || 'N/A'}</td>
          <td>${this.getPerformanceMetric(result, 'totalTime') || 'N/A'}</td>
      </tr>`;
    }).join('');

    return `
    <table style="width: 100%; border-collapse: collapse;">
        <thead>
            <tr style="background: #f8f9fa;">
                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Test</th>
                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Upload Time (ms)</th>
                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Workflow Time (ms)</th>
                <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Total Time (ms)</th>
            </tr>
        </thead>
        <tbody>
            ${performanceData}
        </tbody>
    </table>`;
  }

  /**
   * Generate Markdown summary
   */
  async generateMarkdownSummary() {
    console.log('📝 Generating Markdown summary...');

    const totalTests = this.getTotalTestCount();
    const passedTests = this.getPassedTestCount();
    const failedTests = this.getFailedTestCount();
    const successRate = totalTests > 0 ? ((passedTests / totalTests) * 100).toFixed(1) : 0;

    const summary = `# 🚀 Adronaut E2E Test Results

## 📊 Summary
- **Total Tests**: ${totalTests}
- **Passed**: ${passedTests} ✅
- **Failed**: ${failedTests} ❌
- **Success Rate**: ${successRate}%

## 🎯 Test Categories

### Critical Tests
${this.results.critical.length > 0 ? this.formatResultsForMarkdown(this.results.critical) : 'No critical tests ran'}

### Smoke Tests
${this.results.smoke.length > 0 ? this.formatResultsForMarkdown(this.results.smoke) : 'No smoke tests ran'}

### Performance Tests
${this.results.performance.length > 0 ? this.formatPerformanceForMarkdown(this.results.performance) : 'No performance tests ran'}

### Cross-Browser Tests
${this.results.crossBrowser.length > 0 ? this.formatResultsForMarkdown(this.results.crossBrowser) : 'No cross-browser tests ran'}

---
*Generated on ${new Date().toLocaleString()}*`;

    fs.writeFileSync(path.join(this.reportDir, 'summary.md'), summary);
  }

  /**
   * Format results for markdown
   */
  formatResultsForMarkdown(results) {
    return results.map(result => {
      const status = this.getResultStatus(result);
      const icon = status === 'passed' ? '✅' : status === 'failed' ? '❌' : '⏭️';
      return `- ${icon} **${result.artifact}** (${this.getResultDuration(result)}ms)`;
    }).join('\n');
  }

  /**
   * Format performance results for markdown
   */
  formatPerformanceForMarkdown(results) {
    return results.map(result => {
      const uploadTime = this.getPerformanceMetric(result, 'uploadTime');
      const workflowTime = this.getPerformanceMetric(result, 'workflowTime');
      return `- **${result.artifact}**
  - Upload: ${uploadTime || 'N/A'}ms
  - Workflow: ${workflowTime || 'N/A'}ms`;
    }).join('\n');
  }

  /**
   * Generate JSON report
   */
  async generateJSONReport() {
    console.log('📋 Generating JSON report...');

    const report = {
      generated: new Date().toISOString(),
      summary: {
        total: this.getTotalTestCount(),
        passed: this.getPassedTestCount(),
        failed: this.getFailedTestCount(),
        successRate: this.getTotalTestCount() > 0 ? ((this.getPassedTestCount() / this.getTotalTestCount()) * 100) : 0
      },
      results: this.results,
      environment: {
        node_version: process.version,
        platform: process.platform
      }
    };

    fs.writeFileSync(path.join(this.reportDir, 'report.json'), JSON.stringify(report, null, 2));
  }

  // Helper methods
  getTotalTestCount() {
    return Object.values(this.results).flat().length;
  }

  getPassedTestCount() {
    return Object.values(this.results).flat().filter(result => this.getResultStatus(result) === 'passed').length;
  }

  getFailedTestCount() {
    return Object.values(this.results).flat().filter(result => this.getResultStatus(result) === 'failed').length;
  }

  getResultStatus(result) {
    if (result.stats) {
      return result.stats.failures > 0 ? 'failed' : 'passed';
    }
    return result.status || 'unknown';
  }

  getResultDuration(result) {
    return result.stats?.duration || result.duration || 0;
  }

  getPerformanceMetric(result, metric) {
    return result.performance?.[metric] || result[metric];
  }
}

// Run the report generator
async function main() {
  const artifactsPath = process.argv[2] || './test-artifacts';
  const generator = new TestReportGenerator(artifactsPath);
  await generator.generateReport();
}

if (require.main === module) {
  main().catch(console.error);
}

module.exports = TestReportGenerator;
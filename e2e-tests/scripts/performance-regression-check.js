#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

/**
 * Performance regression checker
 * Compares current test results with baseline metrics
 */
class PerformanceRegressionChecker {
  constructor(resultsPath) {
    this.resultsPath = resultsPath;
    this.baselinePath = path.join(__dirname, '../performance-baseline.json');
    this.thresholds = {
      uploadTime: 10000, // 10 seconds
      workflowTime: 60000, // 60 seconds
      apiResponseTime: 2000, // 2 seconds
      pageLoadTime: 5000, // 5 seconds
      regressionThreshold: 0.2 // 20% performance degradation triggers alert
    };
  }

  /**
   * Check for performance regressions
   */
  async checkRegressions() {
    console.log('🔍 Checking for performance regressions...');

    if (!fs.existsSync(this.resultsPath)) {
      console.error('❌ Test results file not found:', this.resultsPath);
      process.exit(1);
    }

    const currentResults = this.loadResults(this.resultsPath);
    const baseline = this.loadBaseline();

    const regressions = this.detectRegressions(currentResults, baseline);

    if (regressions.length > 0) {
      this.reportRegressions(regressions);
      this.updateBaseline(currentResults);
      process.exit(1); // Fail the build if regressions are found
    } else {
      console.log('✅ No performance regressions detected');
      this.updateBaseline(currentResults);
    }
  }

  /**
   * Load test results from file
   */
  loadResults(filePath) {
    try {
      const content = fs.readFileSync(filePath, 'utf8');
      return JSON.parse(content);
    } catch (error) {
      console.error('❌ Failed to load test results:', error.message);
      return null;
    }
  }

  /**
   * Load baseline metrics
   */
  loadBaseline() {
    if (!fs.existsSync(this.baselinePath)) {
      console.log('⚠️ No baseline found, creating new baseline');
      return null;
    }

    try {
      const content = fs.readFileSync(this.baselinePath, 'utf8');
      return JSON.parse(content);
    } catch (error) {
      console.warn('⚠️ Failed to load baseline:', error.message);
      return null;
    }
  }

  /**
   * Detect performance regressions
   */
  detectRegressions(currentResults, baseline) {
    if (!baseline) {
      return []; // No baseline to compare against
    }

    const regressions = [];

    // Extract performance metrics from current results
    const currentMetrics = this.extractPerformanceMetrics(currentResults);
    const baselineMetrics = baseline.metrics || {};

    // Compare each metric
    for (const [metric, currentValue] of Object.entries(currentMetrics)) {
      const baselineValue = baselineMetrics[metric];

      if (baselineValue && currentValue > baselineValue) {
        const degradation = (currentValue - baselineValue) / baselineValue;

        if (degradation > this.thresholds.regressionThreshold) {
          regressions.push({
            metric,
            currentValue,
            baselineValue,
            degradation: (degradation * 100).toFixed(1) + '%',
            threshold: this.thresholds[metric] || 'N/A'
          });
        }
      }

      // Also check against absolute thresholds
      const threshold = this.thresholds[metric];
      if (threshold && currentValue > threshold) {
        regressions.push({
          metric,
          currentValue,
          threshold,
          type: 'threshold_exceeded',
          message: `${metric} exceeded absolute threshold`
        });
      }
    }

    return regressions;
  }

  /**
   * Extract performance metrics from test results
   */
  extractPerformanceMetrics(results) {
    const metrics = {};

    // Handle different result formats
    if (results.suites) {
      // Playwright JSON format
      results.suites.forEach(suite => {
        suite.specs.forEach(spec => {
          spec.tests.forEach(test => {
            // Extract timing information
            const duration = test.results?.[0]?.duration || 0;
            const testName = test.title.toLowerCase();

            if (testName.includes('upload')) {
              metrics.uploadTime = Math.max(metrics.uploadTime || 0, duration);
            } else if (testName.includes('workflow')) {
              metrics.workflowTime = Math.max(metrics.workflowTime || 0, duration);
            } else if (testName.includes('api')) {
              metrics.apiResponseTime = Math.max(metrics.apiResponseTime || 0, duration);
            } else if (testName.includes('page load')) {
              metrics.pageLoadTime = Math.max(metrics.pageLoadTime || 0, duration);
            }
          });
        });
      });
    } else if (results.metrics) {
      // Custom metrics format
      Object.assign(metrics, results.metrics);
    }

    return metrics;
  }

  /**
   * Report performance regressions
   */
  reportRegressions(regressions) {
    console.log('❌ Performance regressions detected:');
    console.log('');

    regressions.forEach(regression => {
      if (regression.type === 'threshold_exceeded') {
        console.log(`🚨 ${regression.metric}: ${regression.currentValue}ms > ${regression.threshold}ms (threshold exceeded)`);
      } else {
        console.log(`📈 ${regression.metric}: ${regression.currentValue}ms vs ${regression.baselineValue}ms baseline (+${regression.degradation})`);
      }
    });

    console.log('');
    console.log('💡 Consider optimizing the affected components or updating performance thresholds if the degradation is expected.');

    // Generate detailed regression report
    this.generateRegressionReport(regressions);
  }

  /**
   * Generate detailed regression report
   */
  generateRegressionReport(regressions) {
    const reportPath = path.join(__dirname, '../test-reports/performance-regression.md');
    const reportDir = path.dirname(reportPath);

    if (!fs.existsSync(reportDir)) {
      fs.mkdirSync(reportDir, { recursive: true });
    }

    const report = `# Performance Regression Report

Generated: ${new Date().toISOString()}

## 🚨 Regressions Detected

${regressions.map(r => {
      if (r.type === 'threshold_exceeded') {
        return `### ${r.metric}
- **Current**: ${r.currentValue}ms
- **Threshold**: ${r.threshold}ms
- **Status**: ❌ Threshold Exceeded
- **Action**: Investigate performance issues`;
      } else {
        return `### ${r.metric}
- **Current**: ${r.currentValue}ms
- **Baseline**: ${r.baselineValue}ms
- **Degradation**: +${r.degradation}
- **Status**: ❌ Performance Regression
- **Action**: Review recent changes affecting ${r.metric}`;
      }
    }).join('\n\n')}

## 📊 Recommendations

1. **Profile the affected components** to identify bottlenecks
2. **Review recent code changes** that might impact performance
3. **Check infrastructure resources** (CPU, memory, network)
4. **Consider optimizations** or update thresholds if degradation is expected

## 🔧 Next Steps

- [ ] Investigate root cause of performance degradation
- [ ] Implement optimizations if needed
- [ ] Update performance baselines if changes are expected
- [ ] Monitor performance trends over time
`;

    fs.writeFileSync(reportPath, report);
    console.log('📄 Detailed regression report saved to:', reportPath);
  }

  /**
   * Update baseline with current results
   */
  updateBaseline(currentResults) {
    const metrics = this.extractPerformanceMetrics(currentResults);

    const baseline = {
      lastUpdated: new Date().toISOString(),
      metrics,
      thresholds: this.thresholds,
      environment: {
        node_version: process.version,
        platform: process.platform
      }
    };

    fs.writeFileSync(this.baselinePath, JSON.stringify(baseline, null, 2));
    console.log('✅ Performance baseline updated');
  }

  /**
   * Generate performance trend analysis
   */
  generateTrendAnalysis() {
    const trendsPath = path.join(__dirname, '../performance-trends.json');
    let trends = [];

    if (fs.existsSync(trendsPath)) {
      try {
        trends = JSON.parse(fs.readFileSync(trendsPath, 'utf8'));
      } catch (error) {
        console.warn('⚠️ Failed to load performance trends:', error.message);
      }
    }

    const currentResults = this.loadResults(this.resultsPath);
    const currentMetrics = this.extractPerformanceMetrics(currentResults);

    // Add current metrics to trends
    trends.push({
      timestamp: new Date().toISOString(),
      metrics: currentMetrics,
      commit: process.env.GITHUB_SHA || 'unknown',
      branch: process.env.GITHUB_REF || 'unknown'
    });

    // Keep only last 30 data points
    if (trends.length > 30) {
      trends = trends.slice(-30);
    }

    fs.writeFileSync(trendsPath, JSON.stringify(trends, null, 2));
    console.log('📈 Performance trends updated');
  }
}

// CLI interface
async function main() {
  const resultsPath = process.argv[2];

  if (!resultsPath) {
    console.error('Usage: node performance-regression-check.js <results-file-path>');
    process.exit(1);
  }

  const checker = new PerformanceRegressionChecker(resultsPath);
  await checker.checkRegressions();
  checker.generateTrendAnalysis();
}

if (require.main === module) {
  main().catch(console.error);
}

module.exports = PerformanceRegressionChecker;
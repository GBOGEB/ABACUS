
/**
 * DeepAgent Apps Framework - KPI Tracking Utilities
 * Version: 2.0
 * Purpose: KPI management, tracking, and analysis utilities
 */

import {
  IKPI,
  IKPIFramework,
  IKPICategory,
  KPIFrequency,
  KPITrend,
  KPIStatus,
  IPerformanceMetric,
  IAlert,
  AlertSeverity,
  KPIError,
  IEvent,
  EventType
} from './framework';

// KPI Manager
export class KPIManager {
  private kpis: Map<string, IKPI> = new Map();
  private metrics: Map<string, IPerformanceMetric[]> = new Map();
  private thresholds: Map<string, IKPIThreshold> = new Map();
  private collectors: Map<string, IKPICollector> = new Map();
  private eventEmitter: IKPIEventEmitter;

  constructor(eventEmitter: IKPIEventEmitter) {
    this.eventEmitter = eventEmitter;
    this.initializeDefaultCollectors();
  }

  // KPI Registration and Management
  public registerKPI(kpi: IKPI): void {
    this.kpis.set(kpi.name, kpi);
    this.metrics.set(kpi.name, []);
    
    // Parse and set thresholds
    const threshold = this.parseKPITarget(kpi.target);
    if (threshold) {
      this.thresholds.set(kpi.name, threshold);
    }

    console.log(`KPI registered: ${kpi.name}`);
  }

  public registerKPIFramework(framework: IKPIFramework): void {
    // Register all KPIs from all categories
    Object.values(framework.categories).forEach(category => {
      category.metrics.forEach(kpi => this.registerKPI(kpi));
    });
  }

  public getKPI(name: string): IKPI | undefined {
    return this.kpis.get(name);
  }

  public getAllKPIs(): IKPI[] {
    return Array.from(this.kpis.values());
  }

  public getKPIsByCategory(categoryName: string): IKPI[] {
    return this.getAllKPIs().filter(kpi => 
      kpi.name.toLowerCase().includes(categoryName.toLowerCase())
    );
  }

  // Metric Collection
  public async collectMetric(kpiName: string, value: number | string, source?: string): Promise<void> {
    const kpi = this.kpis.get(kpiName);
    if (!kpi) {
      throw new KPIError(`KPI not found: ${kpiName}`, kpiName);
    }

    const metric: IPerformanceMetric = {
      name: kpiName,
      value: typeof value === 'string' ? parseFloat(value) || 0 : value,
      unit: this.extractUnit(kpi.target),
      timestamp: new Date(),
      source: source || 'manual',
      tags: {
        owner: kpi.owner,
        frequency: kpi.frequency
      }
    };

    // Store metric
    const metrics = this.metrics.get(kpiName) || [];
    metrics.push(metric);
    this.metrics.set(kpiName, metrics);

    // Update KPI current value and status
    kpi.currentValue = value;
    kpi.status = this.calculateKPIStatus(kpi, metric.value);
    kpi.trend = this.calculateKPITrend(kpiName);

    // Check thresholds and generate alerts
    await this.checkThresholds(kpi, metric);

    console.log(`Metric collected for ${kpiName}: ${value}`);
  }

  public async collectMetrics(data: { [kpiName: string]: number | string }): Promise<void> {
    const promises = Object.entries(data).map(([kpiName, value]) =>
      this.collectMetric(kpiName, value, 'batch_collection')
    );
    
    await Promise.all(promises);
  }

  // Automated Collection
  public registerCollector(kpiName: string, collector: IKPICollector): void {
    this.collectors.set(kpiName, collector);
    console.log(`Collector registered for KPI: ${kpiName}`);
  }

  public async startAutomatedCollection(): Promise<void> {
    for (const [kpiName, collector] of this.collectors) {
      const kpi = this.kpis.get(kpiName);
      if (!kpi) continue;

      const interval = this.getCollectionInterval(kpi.frequency);
      
      setInterval(async () => {
        try {
          const value = await collector.collect();
          await this.collectMetric(kpiName, value, 'automated');
        } catch (error) {
          console.error(`Failed to collect metric for ${kpiName}:`, error);
        }
      }, interval);
    }
  }

  // Analysis and Reporting
  public getKPIHistory(kpiName: string, timeRange?: ITimeRange): IPerformanceMetric[] {
    const metrics = this.metrics.get(kpiName) || [];
    
    if (!timeRange) {
      return metrics;
    }

    return metrics.filter(metric => 
      metric.timestamp >= timeRange.start && metric.timestamp <= timeRange.end
    );
  }

  public calculateKPITrend(kpiName: string, periods: number = 5): KPITrend {
    const metrics = this.metrics.get(kpiName) || [];
    if (metrics.length < periods) {
      return 'stable';
    }

    const recent = metrics.slice(-periods);
    const values = recent.map(m => typeof m.value === 'number' ? m.value : 0);
    
    // Simple trend calculation using linear regression slope
    const n = values.length;
    const sumX = (n * (n - 1)) / 2;
    const sumY = values.reduce((a, b) => a + b, 0);
    const sumXY = values.reduce((sum, y, x) => sum + x * y, 0);
    const sumX2 = values.reduce((sum, _, x) => sum + x * x, 0);
    
    const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
    
    if (slope > 0.1) return 'improving';
    if (slope < -0.1) return 'declining';
    return 'stable';
  }

  public generateKPIReport(timeRange?: ITimeRange): IKPIReport {
    const report: IKPIReport = {
      generatedAt: new Date(),
      timeRange: timeRange || {
        start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
        end: new Date()
      },
      summary: {
        totalKPIs: this.kpis.size,
        onTarget: 0,
        atRisk: 0,
        offTarget: 0
      },
      kpiDetails: []
    };

    for (const kpi of this.kpis.values()) {
      const history = this.getKPIHistory(kpi.name, report.timeRange);
      const detail: IKPIDetail = {
        kpi,
        currentValue: kpi.currentValue,
        status: kpi.status || 'on_target',
        trend: kpi.trend || 'stable',
        dataPoints: history.length,
        lastUpdated: history.length > 0 ? history[history.length - 1].timestamp : undefined
      };

      report.kpiDetails.push(detail);

      // Update summary counts
      switch (detail.status) {
        case 'on_target':
          report.summary.onTarget++;
          break;
        case 'at_risk':
          report.summary.atRisk++;
          break;
        case 'off_target':
          report.summary.offTarget++;
          break;
      }
    }

    return report;
  }

  // Dashboard and Visualization
  public generateDashboardData(): IKPIDashboardData {
    const kpis = this.getAllKPIs();
    
    return {
      overview: {
        totalKPIs: kpis.length,
        onTarget: kpis.filter(k => k.status === 'on_target').length,
        atRisk: kpis.filter(k => k.status === 'at_risk').length,
        offTarget: kpis.filter(k => k.status === 'off_target').length
      },
      categories: this.groupKPIsByCategory(),
      recentAlerts: this.getRecentAlerts(),
      trendingKPIs: this.getTrendingKPIs()
    };
  }

  private groupKPIsByCategory(): { [category: string]: IKPI[] } {
    const categories: { [category: string]: IKPI[] } = {};
    
    for (const kpi of this.kpis.values()) {
      // Extract category from KPI name or owner
      const category = this.extractCategory(kpi);
      if (!categories[category]) {
        categories[category] = [];
      }
      categories[category].push(kpi);
    }
    
    return categories;
  }

  private extractCategory(kpi: IKPI): string {
    if (kpi.name.toLowerCase().includes('development')) return 'Development';
    if (kpi.name.toLowerCase().includes('deployment')) return 'Deployment';
    if (kpi.name.toLowerCase().includes('performance')) return 'Performance';
    if (kpi.name.toLowerCase().includes('user')) return 'User Engagement';
    if (kpi.name.toLowerCase().includes('business') || kpi.name.toLowerCase().includes('revenue')) return 'Business';
    return 'Other';
  }

  // Threshold Management
  private parseKPITarget(target: string): IKPIThreshold | null {
    const patterns = [
      { regex: />= (\d+(?:\.\d+)?)/, operator: '>=' as const },
      { regex: /<= (\d+(?:\.\d+)?)/, operator: '<=' as const },
      { regex: /> (\d+(?:\.\d+)?)/, operator: '>' as const },
      { regex: /< (\d+(?:\.\d+)?)/, operator: '<' as const },
      { regex: /= (\d+(?:\.\d+)?)/, operator: '=' as const }
    ];

    for (const pattern of patterns) {
      const match = target.match(pattern.regex);
      if (match) {
        return {
          operator: pattern.operator,
          value: parseFloat(match[1]),
          warningThreshold: parseFloat(match[1]) * 0.9, // 90% of target as warning
          criticalThreshold: parseFloat(match[1]) * 0.8  // 80% of target as critical
        };
      }
    }

    return null;
  }

  private calculateKPIStatus(kpi: IKPI, currentValue: number): KPIStatus {
    const threshold = this.thresholds.get(kpi.name);
    if (!threshold) return 'on_target';

    const isThresholdMet = this.evaluateThreshold(currentValue, threshold.operator, threshold.value);
    
    if (isThresholdMet) {
      return 'on_target';
    }

    const isWarningMet = this.evaluateThreshold(currentValue, threshold.operator, threshold.warningThreshold);
    if (isWarningMet) {
      return 'at_risk';
    }

    return 'off_target';
  }

  private evaluateThreshold(value: number, operator: string, threshold: number): boolean {
    switch (operator) {
      case '>=': return value >= threshold;
      case '<=': return value <= threshold;
      case '>': return value > threshold;
      case '<': return value < threshold;
      case '=': return Math.abs(value - threshold) < 0.01;
      default: return false;
    }
  }

  private async checkThresholds(kpi: IKPI, metric: IPerformanceMetric): Promise<void> {
    const threshold = this.thresholds.get(kpi.name);
    if (!threshold) return;

    const value = typeof metric.value === 'number' ? metric.value : 0;
    const status = this.calculateKPIStatus(kpi, value);

    if (status === 'off_target' || status === 'at_risk') {
      const alert: IAlert = {
        name: `KPI Threshold Alert: ${kpi.name}`,
        condition: `${kpi.name} ${status === 'off_target' ? 'critically' : 'significantly'} below target`,
        severity: status === 'off_target' ? 'critical' : 'medium',
        channels: ['dashboard', 'email']
      };

      await this.emitKPIEvent('kpi_threshold_breached', {
        kpiName: kpi.name,
        currentValue: value,
        target: kpi.target,
        status,
        alert
      });
    }
  }

  // Utility Methods
  private extractUnit(target: string): string {
    if (target.includes('%')) return '%';
    if (target.includes('ms')) return 'ms';
    if (target.includes('seconds')) return 's';
    if (target.includes('minutes')) return 'min';
    if (target.includes('hours')) return 'h';
    if (target.includes('days')) return 'd';
    return 'count';
  }

  private getCollectionInterval(frequency: KPIFrequency): number {
    const intervals: { [key in KPIFrequency]: number } = {
      'Real-time': 5000,      // 5 seconds
      'Daily': 86400000,      // 24 hours
      'Weekly': 604800000,    // 7 days
      'Monthly': 2592000000,  // 30 days
      'Quarterly': 7776000000, // 90 days
      'Per deployment': 0,    // Event-driven
      'Per project': 0,       // Event-driven
      'Hourly': 3600000       // 1 hour
    };
    
    return intervals[frequency] || 3600000; // Default to hourly
  }

  private initializeDefaultCollectors(): void {
    // Initialize collectors for common metrics
    this.registerCollector('System Uptime', new UptimeCollector());
    this.registerCollector('Application Response Time', new ResponseTimeCollector());
    this.registerCollector('Error Rate', new ErrorRateCollector());
    this.registerCollector('Daily Active Users (DAU)', new DAUCollector());
  }

  private getRecentAlerts(): IAlert[] {
    // This would typically fetch from an alert storage system
    return [];
  }

  private getTrendingKPIs(): IKPI[] {
    return this.getAllKPIs()
      .filter(kpi => kpi.trend === 'improving' || kpi.trend === 'declining')
      .sort((a, b) => {
        // Sort by trend significance (declining first, then improving)
        if (a.trend === 'declining' && b.trend !== 'declining') return -1;
        if (b.trend === 'declining' && a.trend !== 'declining') return 1;
        return 0;
      })
      .slice(0, 10); // Top 10 trending KPIs
  }

  private async emitKPIEvent(eventType: EventType, data: any): Promise<void> {
    const event: IEvent = {
      id: `kpi_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type: eventType,
      source: 'kpi_manager',
      timestamp: new Date(),
      data
    };

    await this.eventEmitter.emit(event);
  }
}

// Interfaces
export interface IKPIThreshold {
  operator: '>=' | '<=' | '>' | '<' | '=';
  value: number;
  warningThreshold: number;
  criticalThreshold: number;
}

export interface IKPICollector {
  collect(): Promise<number | string>;
}

export interface ITimeRange {
  start: Date;
  end: Date;
}

export interface IKPIReport {
  generatedAt: Date;
  timeRange: ITimeRange;
  summary: {
    totalKPIs: number;
    onTarget: number;
    atRisk: number;
    offTarget: number;
  };
  kpiDetails: IKPIDetail[];
}

export interface IKPIDetail {
  kpi: IKPI;
  currentValue?: number | string;
  status: KPIStatus;
  trend: KPITrend;
  dataPoints: number;
  lastUpdated?: Date;
}

export interface IKPIDashboardData {
  overview: {
    totalKPIs: number;
    onTarget: number;
    atRisk: number;
    offTarget: number;
  };
  categories: { [category: string]: IKPI[] };
  recentAlerts: IAlert[];
  trendingKPIs: IKPI[];
}

export interface IKPIEventEmitter {
  emit(event: IEvent): Promise<void>;
}

// Default Collector Implementations
class UptimeCollector implements IKPICollector {
  async collect(): Promise<number> {
    // Implementation would check system uptime
    return 99.9; // Mock uptime percentage
  }
}

class ResponseTimeCollector implements IKPICollector {
  async collect(): Promise<number> {
    // Implementation would measure actual response times
    return Math.random() * 200 + 50; // Mock response time in ms
  }
}

class ErrorRateCollector implements IKPICollector {
  async collect(): Promise<number> {
    // Implementation would calculate actual error rates
    return Math.random() * 0.5; // Mock error rate percentage
  }
}

class DAUCollector implements IKPICollector {
  async collect(): Promise<number> {
    // Implementation would query user analytics
    return Math.floor(Math.random() * 1000) + 500; // Mock daily active users
  }
}

// Export KPI manager instance
export const kpiManager = new KPIManager({
  async emit(event: IEvent): Promise<void> {
    console.log(`KPI Event emitted: ${event.type}`, event.data);
  }
});

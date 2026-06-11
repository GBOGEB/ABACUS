
/**
 * DeepAgent Apps Framework - Core Interfaces and Types
 * Version: 2.0
 * Purpose: TypeScript definitions for enhanced DeepAgent framework with DMAIC and KPI support
 */

// Core Project Interface
export interface IProject {
  metadata: IProjectMetadata;
  projectOverview: IProjectOverview;
  dmaicFramework: IDMAICFramework;
  kpiFramework: IKPIFramework;
  recursiveHandover: IRecursiveHandover;
  automationFramework: IAutomationFramework;
  enhancedWorkflow: IEnhancedWorkflow;
}

// Project Metadata
export interface IProjectMetadata {
  projectName: string;
  description: string;
  version: string;
  createdDate: string;
  teamLead: string;
  framework: string;
  status: ProjectStatus;
  dmaicPhase: DMAICPhase;
  processMaturity: ProcessMaturity;
}

export type ProjectStatus = 'planning' | 'development' | 'testing' | 'deployed' | 'optimizing';
export type DMAICPhase = 'define' | 'measure' | 'analyze' | 'improve' | 'control';
export type ProcessMaturity = 'initial' | 'managed' | 'defined' | 'quantitatively_managed' | 'optimizing';

// Project Overview
export interface IProjectOverview {
  vision: string;
  targetAudience: string;
  businessValue: string;
  keyFeatures: string[];
  successMetrics: string[];
  qualityGates: string[];
}

// DMAIC Framework
export interface IDMAICFramework {
  description: string;
  define: IDMAICPhase;
  measure: IDMAICPhase;
  analyze: IDMAICPhase;
  improve: IDMAICPhase;
  control: IDMAICPhase;
}

export interface IDMAICPhase {
  phaseDescription: string;
  objectives: string[];
  deliverables: IDeliverable[];
  kpis: IKPI[];
  automationWorkflows: IAutomationWorkflow[];
}

export interface IDeliverable {
  name: string;
  template: string;
  requiredFields: string[];
}

// KPI Framework
export interface IKPIFramework {
  description: string;
  categories: {
    developmentKpis: IKPICategory;
    deploymentKpis: IKPICategory;
    performanceKpis: IKPICategory;
    userEngagementKpis: IKPICategory;
    businessKpis: IKPICategory;
  };
}

export interface IKPICategory {
  description: string;
  metrics: IKPI[];
}

export interface IKPI {
  name: string;
  definition: string;
  target: string;
  measurementMethod: string;
  frequency: KPIFrequency;
  owner: string;
  currentValue?: number | string;
  trend?: KPITrend;
  status?: KPIStatus;
}

export type KPIFrequency = 'Real-time' | 'Daily' | 'Weekly' | 'Monthly' | 'Quarterly' | 'Per deployment' | 'Per project' | 'Hourly';
export type KPITrend = 'improving' | 'stable' | 'declining';
export type KPIStatus = 'on_target' | 'at_risk' | 'off_target';

// Recursive Handover Structure
export interface IRecursiveHandover {
  description: string;
  structure: IHandoverLevel;
  handoverTemplates: {
    projectHandover: IHandoverTemplate;
    moduleHandover: IHandoverTemplate;
    featureHandover: IHandoverTemplate;
  };
}

export interface IHandoverLevel {
  name: string;
  scope: string;
  components: string[];
  nestedHandovers?: { [key: string]: IHandoverLevel };
}

export interface IHandoverTemplate {
  sections: IHandoverSection[];
}

export interface IHandoverSection {
  name: string;
  requiredFields: string[];
}

// Automation Framework
export interface IAutomationFramework {
  description: string;
  workflowCategories: {
    developmentAutomation: IWorkflowCategory;
    deploymentAutomation: IWorkflowCategory;
    monitoringAutomation?: IWorkflowCategory;
    qualityAutomation?: IWorkflowCategory;
  };
}

export interface IWorkflowCategory {
  description: string;
  workflows: IAutomationWorkflow[];
}

export interface IAutomationWorkflow {
  name: string;
  trigger: string;
  approvalRequired?: boolean;
  steps: IWorkflowStep[];
}

export interface IWorkflowStep {
  name: string;
  action: string;
  parameters: { [key: string]: any };
}

// Enhanced Workflow
export interface IEnhancedWorkflow {
  description: string;
  phases: {
    definePlanning: IWorkflowPhase;
    measureInitialBuild: IWorkflowPhase;
    analyzeIterativeDevelopment: IWorkflowPhase;
    improveDeployment: IWorkflowPhase;
    controlOptimization: IWorkflowPhase;
  };
}

export interface IWorkflowPhase {
  name: string;
  dmaicPhase: DMAICPhase;
  description: string;
  steps: string[];
  deliverables: string[];
  qualityGates: string[];
}

// Quality Gates
export interface IQualityGate {
  name: string;
  criteria: IQualityCriteria[];
  phase: DMAICPhase;
  mandatory: boolean;
}

export interface IQualityCriteria {
  metric: string;
  threshold: string;
  operator: ComparisonOperator;
  value: number | string;
}

export type ComparisonOperator = '>=' | '<=' | '>' | '<' | '=' | '!=';

// Performance Metrics
export interface IPerformanceMetric {
  name: string;
  value: number;
  unit: string;
  timestamp: Date;
  source: string;
  tags?: { [key: string]: string };
}

// Deployment Configuration
export interface IDeploymentConfig {
  environment: DeploymentEnvironment;
  strategy: DeploymentStrategy;
  healthChecks: IHealthCheck[];
  rollbackConfig: IRollbackConfig;
  monitoring: IMonitoringConfig;
}

export type DeploymentEnvironment = 'development' | 'staging' | 'production';
export type DeploymentStrategy = 'blue_green' | 'canary' | 'rolling' | 'recreate';

export interface IHealthCheck {
  name: string;
  url: string;
  timeout: number;
  interval: number;
  retries: number;
}

export interface IRollbackConfig {
  enabled: boolean;
  automaticTriggers: string[];
  manualApprovalRequired: boolean;
  rollbackTimeout: number;
}

export interface IMonitoringConfig {
  metrics: string[];
  alerts: IAlert[];
  dashboards: string[];
}

export interface IAlert {
  name: string;
  condition: string;
  severity: AlertSeverity;
  channels: string[];
}

export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';

// Utility Types
export interface ITimestamp {
  created: Date;
  updated: Date;
  version: string;
}

export interface IValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

export interface IExecutionResult {
  success: boolean;
  message: string;
  data?: any;
  executionTime: number;
}

// Event Types
export interface IEvent {
  id: string;
  type: EventType;
  source: string;
  timestamp: Date;
  data: any;
}

export type EventType = 
  | 'project_created'
  | 'phase_completed'
  | 'kpi_threshold_breached'
  | 'quality_gate_failed'
  | 'deployment_started'
  | 'deployment_completed'
  | 'automation_triggered'
  | 'handover_initiated'
  | 'improvement_implemented'
  | 'section_updated'
  | 'section_completed'
  | 'handover_completed'
  | 'dependency_added';

// Configuration Types
export interface IFrameworkConfig {
  enableDMAIC: boolean;
  enableKPITracking: boolean;
  enableAutomation: boolean;
  enableRecursiveHandover: boolean;
  defaultKPITargets: { [key: string]: string };
  automationSettings: IAutomationSettings;
}

export interface IAutomationSettings {
  maxConcurrentWorkflows: number;
  defaultTimeout: number;
  retryAttempts: number;
  enableNotifications: boolean;
  notificationChannels: string[];
}

// Error Types
export class FrameworkError extends Error {
  constructor(
    message: string,
    public code: string,
    public phase?: DMAICPhase,
    public component?: string
  ) {
    super(message);
    this.name = 'FrameworkError';
  }
}

export class ValidationError extends FrameworkError {
  constructor(message: string, public field: string, phase?: DMAICPhase) {
    super(message, 'VALIDATION_ERROR', phase);
    this.name = 'ValidationError';
  }
}

export class AutomationError extends FrameworkError {
  constructor(message: string, public workflowName: string, public stepName?: string) {
    super(message, 'AUTOMATION_ERROR');
    this.name = 'AutomationError';
  }
}

export class KPIError extends FrameworkError {
  constructor(message: string, public kpiName: string) {
    super(message, 'KPI_ERROR');
    this.name = 'KPIError';
  }
}

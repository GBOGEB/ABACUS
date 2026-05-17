
/**
 * DeepAgent Apps Framework - Main Export Barrel
 * Version: 2.0
 * Purpose: Central export point for all framework components
 */

// Core Framework Exports
export * from './framework';

// Automation Framework Exports
export {
  AutomationEngine,
  automationEngine,
  IWorkflowContext,
  IWorkflowExecution,
  IWorkflowExecutionResult,
  IStepExecutionResult,
  WorkflowStatus,
  IActionHandler,
  IEventHandler
} from './automation';

// KPI Management Exports
export {
  KPIManager,
  kpiManager,
  IKPIThreshold,
  IKPICollector,
  ITimeRange,
  IKPIReport,
  IKPIDetail,
  IKPIDashboardData,
  IKPIEventEmitter
} from './kpi';

// DMAIC Process Exports
export {
  DMAICProcessManager,
  dmaicManager,
  IDMAICPhaseData,
  IDeliverableInstance,
  IPhaseTransitionResult,
  IPhaseExecutionResult,
  IProjectCharter,
  IMeasurementPlan,
  IAnalysisScope,
  IImprovementPlan,
  IControlPlan,
  IDMAICEventEmitter
} from './dmaic';

// Handover Management Exports
export {
  HandoverManager,
  createHandoverManager,
  HandoverLevel,
  HandoverStatus,
  SectionStatus,
  DependencyType,
  IHandoverInstance,
  IHandoverSectionInstance,
  IHandoverDependency,
  IHandoverCompletionResult,
  IDependencyCheckResult,
  IDependencyValidationResult,
  IHandoverReport,
  IHandoverSectionReport,
  IHandoverMetrics,
  IHandoverEventEmitter
} from './handover';

// Import instances for internal use
import { automationEngine } from './automation';
import { kpiManager, IKPIEventEmitter } from './kpi';
import { dmaicManager, IDMAICEventEmitter } from './dmaic';
import { createHandoverManager, IHandoverEventEmitter } from './handover';
import {
  IProject,
  IKPIFramework,
  IAutomationWorkflow,
  IRecursiveHandover,
  IAutomationFramework,
  IEnhancedWorkflow,
  IDMAICFramework
} from './framework';

// Framework Initialization and Configuration
export class DeepAgentFramework {
  private static instance: DeepAgentFramework;
  private initialized: boolean = false;
  
  private constructor() {}

  public static getInstance(): DeepAgentFramework {
    if (!DeepAgentFramework.instance) {
      DeepAgentFramework.instance = new DeepAgentFramework();
    }
    return DeepAgentFramework.instance;
  }

  public async initialize(config: IFrameworkInitConfig): Promise<void> {
    if (this.initialized) {
      console.warn('Framework already initialized');
      return;
    }

    try {
      // Initialize KPI Framework
      if (config.enableKPITracking && config.kpiFramework) {
        kpiManager.registerKPIFramework(config.kpiFramework);
        if (config.enableAutomatedCollection) {
          await kpiManager.startAutomatedCollection();
        }
      }

      // Initialize DMAIC Process
      if (config.enableDMAIC) {
        // DMAIC manager is ready to use
        console.log('DMAIC process manager initialized');
      }

      // Initialize Automation Engine
      if (config.enableAutomation && config.automationWorkflows) {
        for (const workflow of config.automationWorkflows) {
          automationEngine.registerWorkflow(workflow);
        }
      }

      // Initialize Handover Management
      if (config.enableRecursiveHandover && config.handoverStructure) {
        // Handover manager will be created as needed
        console.log('Handover management ready');
      }

      this.initialized = true;
      console.log('DeepAgent Framework initialized successfully');
    } catch (error) {
      console.error('Framework initialization failed:', error);
      throw error;
    }
  }

  public isInitialized(): boolean {
    return this.initialized;
  }

  public getVersion(): string {
    return '2.0.0';
  }

  public getCapabilities(): string[] {
    return [
      'DMAIC Process Management',
      'KPI Tracking and Analytics',
      'Automation Workflows',
      'Recursive Handover Structure',
      'Quality Gates and Validation',
      'Performance Monitoring',
      'Event-Driven Architecture'
    ];
  }
}

// Framework Configuration Interface
export interface IFrameworkInitConfig {
  enableDMAIC?: boolean;
  enableKPITracking?: boolean;
  enableAutomation?: boolean;
  enableRecursiveHandover?: boolean;
  enableAutomatedCollection?: boolean;
  kpiFramework?: IKPIFramework;
  automationWorkflows?: IAutomationWorkflow[];
  handoverStructure?: IRecursiveHandover;
  eventEmitters?: {
    kpi?: IKPIEventEmitter;
    dmaic?: IDMAICEventEmitter;
    handover?: IHandoverEventEmitter;
  };
}

// Utility Functions
export function createProject(config: IProjectConfig): IProject {
  return {
    metadata: {
      projectName: config.name,
      description: config.description,
      version: '1.0.0',
      createdDate: new Date().toISOString().split('T')[0],
      teamLead: config.teamLead,
      framework: 'DeepAgent Apps Enhanced',
      status: 'planning',
      dmaicPhase: 'define',
      processMaturity: 'initial'
    },
    projectOverview: {
      vision: config.vision,
      targetAudience: config.targetAudience,
      businessValue: config.businessValue || '',
      keyFeatures: config.keyFeatures || [],
      successMetrics: config.successMetrics || [],
      qualityGates: config.qualityGates || []
    },
    dmaicFramework: config.dmaicFramework,
    kpiFramework: config.kpiFramework,
    recursiveHandover: config.recursiveHandover,
    automationFramework: config.automationFramework,
    enhancedWorkflow: config.enhancedWorkflow
  };
}

export interface IProjectConfig {
  name: string;
  description: string;
  teamLead: string;
  vision: string;
  targetAudience: string;
  businessValue?: string;
  keyFeatures?: string[];
  successMetrics?: string[];
  qualityGates?: string[];
  dmaicFramework: IDMAICFramework;
  kpiFramework: IKPIFramework;
  recursiveHandover: IRecursiveHandover;
  automationFramework: IAutomationFramework;
  enhancedWorkflow: IEnhancedWorkflow;
}

// Export framework instance
export const framework = DeepAgentFramework.getInstance();

// Default export
export default {
  framework,
  automationEngine,
  kpiManager,
  dmaicManager,
  createHandoverManager,
  createProject,
  DeepAgentFramework
};

export function createState() {
  return {
    projects: [],
    selectedProjectId: "",
    activeProject: null,
    workspace: null,
    bootstrapStatus: null,
    bootstrapPlan: null,
    queueFilters: {
      project_id: "",
      repo_id: "",
      status: "",
      type: "",
      assigned_agent: "",
    },
    report: null,
    exportText: "",
    projectFactoryDossier: null,
    scopePackage: null,
    architectureContract: null,
    milestoneIssuePlan: null,
    githubApplyPlan: null,
    agentDispatchPlan: null,
    validationExecutionPlan: null,
    documentationCloseoutPlan: null,
    executionPhaseApproval: null,
    executionReadiness: null,
  };
}
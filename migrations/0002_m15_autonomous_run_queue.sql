CREATE TABLE IF NOT EXISTS autonomous_runs (
    run_id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    parent_issue INTEGER NOT NULL,
    target_issue INTEGER NOT NULL,
    current_step TEXT NOT NULL,
    status TEXT NOT NULL,
    selected_agent TEXT NOT NULL,
    model_tier TEXT NOT NULL,
    branch_name TEXT,
    commit_hash TEXT,
    pr_number INTEGER,
    validation_status TEXT NOT NULL,
    qa_status TEXT NOT NULL,
    closeout_status TEXT NOT NULL,
    next_issue_candidate INTEGER,
    safety_mode TEXT NOT NULL,
    validation_expectations JSONB NOT NULL DEFAULT '[]'::jsonb,
    next_recommended_command TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS run_steps (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES autonomous_runs(run_id) ON DELETE CASCADE,
    step_order INTEGER NOT NULL,
    step_type TEXT NOT NULL,
    status TEXT NOT NULL,
    inputs JSONB NOT NULL DEFAULT '{}'::jsonb,
    outputs JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failure_reason TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    requires_human_approval BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (run_id, step_order)
);

CREATE INDEX IF NOT EXISTS idx_autonomous_runs_status ON autonomous_runs(status);
CREATE INDEX IF NOT EXISTS idx_autonomous_runs_target_issue ON autonomous_runs(target_issue);
CREATE INDEX IF NOT EXISTS idx_run_steps_run_order ON run_steps(run_id, step_order);

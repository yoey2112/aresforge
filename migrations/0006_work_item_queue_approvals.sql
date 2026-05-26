CREATE TABLE IF NOT EXISTS work_item_queue_approvals (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    work_item_id TEXT NOT NULL REFERENCES work_items(id) ON DELETE CASCADE,
    target_queue_id TEXT NOT NULL REFERENCES queues(id),
    approval_status TEXT NOT NULL,
    actor TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT work_item_queue_approvals_status_check
        CHECK (approval_status IN ('pending', 'approved', 'rejected', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_work_item_queue_approvals_lookup
    ON work_item_queue_approvals(project_id, work_item_id, target_queue_id, created_at DESC);

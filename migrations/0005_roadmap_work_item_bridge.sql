CREATE TABLE IF NOT EXISTS roadmap_work_item_links (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    roadmap_task_id TEXT NOT NULL REFERENCES roadmap_tasks(id) ON DELETE CASCADE,
    work_item_id TEXT NOT NULL REFERENCES work_items(id) ON DELETE CASCADE,
    link_type TEXT NOT NULL DEFAULT 'implements',
    status TEXT NOT NULL DEFAULT 'active',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (roadmap_task_id, work_item_id)
);

CREATE INDEX IF NOT EXISTS idx_roadmap_work_item_links_project_id
    ON roadmap_work_item_links(project_id);
CREATE INDEX IF NOT EXISTS idx_roadmap_work_item_links_task_id
    ON roadmap_work_item_links(roadmap_task_id);
CREATE INDEX IF NOT EXISTS idx_roadmap_work_item_links_work_item_id
    ON roadmap_work_item_links(work_item_id);
CREATE INDEX IF NOT EXISTS idx_roadmap_work_item_links_status
    ON roadmap_work_item_links(status);

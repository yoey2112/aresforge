CREATE TABLE IF NOT EXISTS roadmap_areas (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'planned',
    sort_order INTEGER NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS roadmap_milestones (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    area_id TEXT REFERENCES roadmap_areas(id),
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'planned',
    sort_order INTEGER NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS roadmap_tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    milestone_id TEXT REFERENCES roadmap_milestones(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'planned',
    priority TEXT NOT NULL DEFAULT 'normal',
    sort_order INTEGER NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS roadmap_task_dependencies (
    task_id TEXT NOT NULL REFERENCES roadmap_tasks(id) ON DELETE CASCADE,
    depends_on_task_id TEXT NOT NULL REFERENCES roadmap_tasks(id) ON DELETE CASCADE,
    dependency_type TEXT NOT NULL DEFAULT 'blocks',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (task_id, depends_on_task_id)
);

CREATE TABLE IF NOT EXISTS roadmap_events (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    area_id TEXT REFERENCES roadmap_areas(id),
    milestone_id TEXT REFERENCES roadmap_milestones(id),
    task_id TEXT REFERENCES roadmap_tasks(id),
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'aresforge-cli',
    summary TEXT NOT NULL DEFAULT '',
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_roadmap_areas_project_sort ON roadmap_areas(project_id, sort_order, id);
CREATE INDEX IF NOT EXISTS idx_roadmap_areas_status ON roadmap_areas(status);

CREATE INDEX IF NOT EXISTS idx_roadmap_milestones_project_sort ON roadmap_milestones(project_id, sort_order, id);
CREATE INDEX IF NOT EXISTS idx_roadmap_milestones_area_sort ON roadmap_milestones(area_id, sort_order, id);
CREATE INDEX IF NOT EXISTS idx_roadmap_milestones_status ON roadmap_milestones(status);

CREATE INDEX IF NOT EXISTS idx_roadmap_tasks_project_sort ON roadmap_tasks(project_id, sort_order, id);
CREATE INDEX IF NOT EXISTS idx_roadmap_tasks_milestone_sort ON roadmap_tasks(milestone_id, sort_order, id);
CREATE INDEX IF NOT EXISTS idx_roadmap_tasks_status ON roadmap_tasks(status);

CREATE INDEX IF NOT EXISTS idx_roadmap_task_dependencies_depends_on ON roadmap_task_dependencies(depends_on_task_id);
CREATE INDEX IF NOT EXISTS idx_roadmap_task_dependencies_dependency_type ON roadmap_task_dependencies(dependency_type);

CREATE INDEX IF NOT EXISTS idx_roadmap_events_project_created ON roadmap_events(project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_roadmap_events_area_created ON roadmap_events(area_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_roadmap_events_milestone_created ON roadmap_events(milestone_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_roadmap_events_task_created ON roadmap_events(task_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_roadmap_events_type_created ON roadmap_events(event_type, created_at DESC);

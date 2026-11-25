CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    scenario TEXT NOT NULL,
    triggered_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    total_duration_seconds REAL
);

CREATE TABLE IF NOT EXISTS agent_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT NOT NULL REFERENCES incidents(id),
    agent_name TEXT NOT NULL,
    action_type TEXT NOT NULL,
    input_summary TEXT,
    output_summary TEXT,
    success INTEGER NOT NULL,
    duration_ms INTEGER,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recovery_metrics (
    incident_id TEXT PRIMARY KEY REFERENCES incidents(id),
    mttr_seconds REAL,
    detection_time_seconds REAL,
    diagnosis_time_seconds REAL,
    planning_time_seconds REAL,
    recovery_time_seconds REAL,
    verification_time_seconds REAL,
    replan_count INTEGER DEFAULT 0,
    recovery_strategy TEXT,
    success INTEGER NOT NULL
);

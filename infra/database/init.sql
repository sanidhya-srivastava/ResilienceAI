CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL DEFAULT 'healthy',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO services (name, status) VALUES
    ('web-server', 'healthy'),
    ('app-database', 'healthy'),
    ('backup-store', 'healthy')
ON CONFLICT (name) DO NOTHING;

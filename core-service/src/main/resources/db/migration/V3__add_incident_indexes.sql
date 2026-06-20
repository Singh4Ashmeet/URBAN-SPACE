CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents (status);
CREATE INDEX IF NOT EXISTS idx_incidents_incident_type ON incidents (incident_type);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents (severity);
CREATE INDEX IF NOT EXISTS idx_incidents_reported_at ON incidents (reported_at);
CREATE INDEX IF NOT EXISTS idx_incidents_location ON incidents USING GIST (location);

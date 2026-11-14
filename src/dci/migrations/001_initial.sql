CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at REAL NOT NULL
);
CREATE TABLE cases (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at REAL NOT NULL,
    revision INTEGER NOT NULL DEFAULT 0,
    accepted_fingerprint TEXT,
    accepted_by TEXT,
    accepted_at REAL,
    acceptance_reason TEXT,
    published_fingerprint TEXT
);
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(id),
    document_key TEXT NOT NULL,
    version INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    filename TEXT NOT NULL,
    size INTEGER NOT NULL,
    created_at REAL NOT NULL,
    profile TEXT NOT NULL,
    policy_digest TEXT NOT NULL,
    status TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 0,
    parsed_json TEXT,
    extraction_json TEXT,
    checks_json TEXT,
    error_code TEXT,
    UNIQUE(case_id, document_key, version),
    UNIQUE(case_id, document_key, sha256)
);
CREATE INDEX document_cases ON documents(case_id, document_key, version DESC);
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    document_id TEXT UNIQUE NOT NULL REFERENCES documents(id),
    status TEXT NOT NULL,
    attempt INTEGER NOT NULL DEFAULT 0,
    owner TEXT,
    lease_token TEXT,
    lease_until REAL,
    available_at REAL NOT NULL,
    created_at REAL NOT NULL,
    stage TEXT NOT NULL DEFAULT 'parse',
    last_error TEXT,
    elapsed_seconds REAL,
    finished_at REAL
);
CREATE INDEX queue_claims ON jobs(status, available_at, created_at);
CREATE TABLE audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at REAL NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    case_id TEXT NOT NULL,
    document_id TEXT,
    revision INTEGER,
    details_json TEXT NOT NULL
);
CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit BEGIN
    SELECT RAISE(ABORT, 'audit entries are immutable');
END;
CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit BEGIN
    SELECT RAISE(ABORT, 'audit entries are immutable');
END;
CREATE TABLE publications (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(id),
    fingerprint TEXT NOT NULL,
    published_at REAL NOT NULL,
    published_by TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE(case_id, fingerprint)
);
CREATE TABLE published_invoices (
    supplier_id TEXT NOT NULL,
    invoice_id TEXT NOT NULL,
    case_id TEXT NOT NULL REFERENCES cases(id),
    PRIMARY KEY(supplier_id, invoice_id)
);

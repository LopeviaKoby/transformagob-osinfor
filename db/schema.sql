PRAGMA foreign_keys = ON;

CREATE TABLE build_metadata (
    metadata_key TEXT PRIMARY KEY,
    metadata_value TEXT NOT NULL
);

CREATE TABLE cases (
    case_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    case_type TEXT NOT NULL
        CHECK (case_type IN ('clean', 'inconsistent')),

    titulo_habilitante TEXT NOT NULL,
    parcela_corta TEXT NOT NULL,
    codigo_arbol TEXT NOT NULL,

    verification_status TEXT NOT NULL,
    attestation_eligible INTEGER NOT NULL
        CHECK (attestation_eligible IN (0, 1)),

    titular TEXT,
    plan_operativo TEXT,
    resolucion TEXT,

    especie_censo TEXT,
    especie_supervision TEXT,

    volumen_censo_m3 REAL,
    volumen_tala_m3 REAL,
    volumen_trozado_m3 REAL,
    diferencia_tala_trozado_m3 REAL,

    observations TEXT,
    evidence_hash_sha256 TEXT NOT NULL UNIQUE,
    source_json_path TEXT NOT NULL,
    loaded_at_utc TEXT NOT NULL,

    UNIQUE (
        titulo_habilitante,
        parcela_corta,
        codigo_arbol
    )
);

CREATE TABLE case_checks (
    case_id TEXT NOT NULL,
    check_name TEXT NOT NULL,

    check_status TEXT NOT NULL
        CHECK (
            check_status IN (
                'PASS',
                'FAIL',
                'NOT_EVALUATED'
            )
        ),

    raw_value_json TEXT NOT NULL,

    PRIMARY KEY (case_id, check_name),

    FOREIGN KEY (case_id)
        REFERENCES cases(case_id)
        ON DELETE CASCADE
);

CREATE TABLE case_sources (
    case_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    source_path TEXT NOT NULL,

    PRIMARY KEY (case_id, stage),

    FOREIGN KEY (case_id)
        REFERENCES cases(case_id)
        ON DELETE CASCADE
);

CREATE TABLE case_records (
    case_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    record_index INTEGER NOT NULL,
    record_json TEXT NOT NULL,

    PRIMARY KEY (
        case_id,
        stage,
        record_index
    ),

    FOREIGN KEY (case_id)
        REFERENCES cases(case_id)
        ON DELETE CASCADE
);

CREATE TABLE case_logs (
    case_id TEXT NOT NULL,
    codigo_troza TEXT NOT NULL,

    PRIMARY KEY (case_id, codigo_troza),

    FOREIGN KEY (case_id)
        REFERENCES cases(case_id)
        ON DELETE CASCADE
);

CREATE TABLE case_gtf (
    case_id TEXT NOT NULL,
    numero_gtf TEXT NOT NULL,

    PRIMARY KEY (case_id, numero_gtf),

    FOREIGN KEY (case_id)
        REFERENCES cases(case_id)
        ON DELETE CASCADE
);

CREATE INDEX idx_cases_tree
    ON cases (
        titulo_habilitante,
        parcela_corta,
        codigo_arbol
    );

CREATE INDEX idx_cases_status
    ON cases (
        verification_status,
        attestation_eligible
    );

CREATE INDEX idx_records_stage
    ON case_records (
        case_id,
        stage
    );
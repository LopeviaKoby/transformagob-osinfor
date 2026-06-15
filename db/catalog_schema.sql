PRAGMA foreign_keys = ON;

CREATE TABLE build_metadata (
    metadata_key TEXT PRIMARY KEY,
    metadata_value TEXT NOT NULL
);

CREATE TABLE data_sources (
    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_kind TEXT NOT NULL,
    source_name TEXT NOT NULL,
    relative_path TEXT NOT NULL UNIQUE,
    sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    workbook_sheets_json TEXT,
    pdf_pages INTEGER,
    processed_rows INTEGER NOT NULL DEFAULT 0,
    loaded_rows INTEGER NOT NULL DEFAULT 0,
    rejected_rows INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE titles (
    title_id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo_habilitante_original TEXT NOT NULL,
    titulo_habilitante_norm TEXT NOT NULL UNIQUE,
    titular_original TEXT,
    titular_norm TEXT,
    modalidad_original TEXT,
    plan_operativo_original TEXT,
    plan_operativo_norm TEXT,
    resolucion_original TEXT,
    resolucion_norm TEXT
);

CREATE TABLE trees (
    tree_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id INTEGER NOT NULL,
    titulo_habilitante_norm TEXT NOT NULL,
    parcela_corta_original TEXT,
    parcela_corta_norm TEXT NOT NULL,
    codigo_arbol_original TEXT,
    codigo_arbol_norm TEXT NOT NULL,
    composite_tree_key TEXT NOT NULL UNIQUE,
    especie_original TEXT,
    especie_norm TEXT,
    volumen_censo_text TEXT,
    dap_text TEXT,
    ac_text TEXT,
    dmc_text TEXT,
    source_relative_path TEXT NOT NULL,
    source_sheet TEXT,
    source_row_number INTEGER,
    raw_payload_json TEXT NOT NULL,
    normalized_payload_json TEXT NOT NULL,
    FOREIGN KEY (title_id) REFERENCES titles(title_id)
);

CREATE TABLE supervisions (
    supervision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id INTEGER,
    title_id INTEGER NOT NULL,
    titulo_habilitante_norm TEXT NOT NULL,
    parcela_corta_original TEXT,
    parcela_corta_norm TEXT NOT NULL,
    codigo_arbol_original TEXT,
    codigo_arbol_norm TEXT NOT NULL,
    composite_tree_key TEXT NOT NULL,
    especie_original TEXT,
    especie_norm TEXT,
    especie_censo_referida_original TEXT,
    especie_censo_referida_norm TEXT,
    coincide_especies_norm TEXT,
    source_relative_path TEXT NOT NULL,
    source_sheet TEXT,
    source_row_number INTEGER,
    raw_payload_json TEXT NOT NULL,
    normalized_payload_json TEXT NOT NULL,
    FOREIGN KEY (tree_id) REFERENCES trees(tree_id),
    FOREIGN KEY (title_id) REFERENCES titles(title_id)
);

CREATE TABLE fellings (
    felling_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id INTEGER,
    title_id INTEGER NOT NULL,
    titulo_habilitante_norm TEXT NOT NULL,
    parcela_corta_original TEXT,
    parcela_corta_norm TEXT NOT NULL,
    codigo_arbol_original TEXT,
    codigo_arbol_norm TEXT NOT NULL,
    composite_tree_key TEXT NOT NULL,
    especie_original TEXT,
    especie_norm TEXT,
    fecha_operacion TEXT,
    volumen_text TEXT,
    diametro_mayor_text TEXT,
    diametro_menor_text TEXT,
    longitud_text TEXT,
    r_private_value TEXT,
    observaciones_private TEXT,
    source_relative_path TEXT NOT NULL,
    source_sheet TEXT,
    source_row_number INTEGER,
    raw_payload_json TEXT NOT NULL,
    normalized_payload_json TEXT NOT NULL,
    FOREIGN KEY (tree_id) REFERENCES trees(tree_id),
    FOREIGN KEY (title_id) REFERENCES titles(title_id)
);

CREATE TABLE logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id INTEGER,
    felling_id INTEGER,
    title_id INTEGER NOT NULL,
    titulo_habilitante_norm TEXT NOT NULL,
    parcela_corta_original TEXT,
    parcela_corta_norm TEXT NOT NULL,
    codigo_troza_original TEXT,
    codigo_troza_norm TEXT NOT NULL,
    codigo_arbol_padre_norm TEXT NOT NULL,
    composite_tree_key TEXT NOT NULL,
    composite_log_key TEXT NOT NULL UNIQUE,
    especie_original TEXT,
    especie_norm TEXT,
    fecha_operacion TEXT,
    volumen_text TEXT,
    diametro_mayor_text TEXT,
    diametro_menor_text TEXT,
    longitud_text TEXT,
    r_private_value TEXT,
    observaciones_private TEXT,
    source_relative_path TEXT NOT NULL,
    source_sheet TEXT,
    source_row_number INTEGER,
    raw_payload_json TEXT NOT NULL,
    normalized_payload_json TEXT NOT NULL,
    FOREIGN KEY (tree_id) REFERENCES trees(tree_id),
    FOREIGN KEY (felling_id) REFERENCES fellings(felling_id),
    FOREIGN KEY (title_id) REFERENCES titles(title_id)
);

CREATE TABLE dispatches (
    dispatch_id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id INTEGER,
    tree_id INTEGER,
    title_id INTEGER NOT NULL,
    titulo_habilitante_norm TEXT NOT NULL,
    parcela_corta_original TEXT,
    parcela_corta_norm TEXT NOT NULL,
    codigo_troza_original TEXT,
    codigo_troza_norm TEXT NOT NULL,
    codigo_arbol_padre_norm TEXT NOT NULL,
    composite_tree_key TEXT NOT NULL,
    composite_log_key TEXT NOT NULL,
    codigo_despacho_original TEXT,
    codigo_despacho_norm TEXT,
    numero_gtf_original TEXT,
    numero_gtf_norm TEXT,
    fecha_operacion TEXT,
    observaciones_private TEXT,
    source_relative_path TEXT NOT NULL,
    source_sheet TEXT,
    source_row_number INTEGER,
    raw_payload_json TEXT NOT NULL,
    normalized_payload_json TEXT NOT NULL,
    FOREIGN KEY (log_id) REFERENCES logs(log_id),
    FOREIGN KEY (tree_id) REFERENCES trees(tree_id),
    FOREIGN KEY (title_id) REFERENCES titles(title_id)
);

CREATE TABLE species_balances (
    balance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id INTEGER NOT NULL,
    titulo_habilitante_norm TEXT NOT NULL,
    parcela_corta_original TEXT,
    parcela_corta_norm TEXT NOT NULL,
    product_type TEXT NOT NULL,
    especie_original TEXT,
    especie_norm TEXT NOT NULL,
    composite_balance_key TEXT NOT NULL,
    volumen_autorizado_text TEXT NOT NULL,
    volumen_extraido_text TEXT NOT NULL,
    saldo_reportado_text TEXT NOT NULL,
    source_fragment TEXT NOT NULL,
    source_relative_path TEXT NOT NULL,
    source_sheet TEXT,
    source_row_number INTEGER,
    raw_payload_json TEXT NOT NULL,
    normalized_payload_json TEXT NOT NULL,
    FOREIGN KEY (title_id) REFERENCES titles(title_id)
);

CREATE TABLE trace_catalog (
    trace_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id INTEGER,
    title_id INTEGER NOT NULL,
    titulo_habilitante_norm TEXT NOT NULL,
    parcela_corta_norm TEXT NOT NULL,
    codigo_arbol_norm TEXT NOT NULL,
    composite_tree_key TEXT NOT NULL UNIQUE,
    especie_censo_norm TEXT,
    especie_supervision_norm TEXT,
    especie_operacion_norm TEXT,
    volumen_censo_text TEXT,
    volumen_tala_text TEXT,
    volumen_trozado_text TEXT,
    verification_status TEXT NOT NULL
        CHECK (verification_status IN (
            'CONSISTENTE',
            'POR_REVISAR',
            'INCOMPLETO',
            'NO_EVALUADO'
        )),
    troza_count INTEGER NOT NULL DEFAULT 0,
    dispatch_count INTEGER NOT NULL DEFAULT 0,
    gtf_count INTEGER NOT NULL DEFAULT 0,
    evidence_hash_sha256 TEXT NOT NULL,
    public_payload_json TEXT NOT NULL,
    lineage_json TEXT NOT NULL,
    FOREIGN KEY (tree_id) REFERENCES trees(tree_id),
    FOREIGN KEY (title_id) REFERENCES titles(title_id)
);

CREATE TABLE trace_checks (
    trace_id INTEGER NOT NULL,
    check_name TEXT NOT NULL,
    check_status TEXT NOT NULL
        CHECK (check_status IN ('PASS', 'FAIL', 'NOT_EVALUATED')),
    value_json TEXT NOT NULL,
    PRIMARY KEY (trace_id, check_name),
    FOREIGN KEY (trace_id) REFERENCES trace_catalog(trace_id) ON DELETE CASCADE
);

CREATE TABLE search_identifiers (
    search_id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id INTEGER NOT NULL,
    identifier_type TEXT NOT NULL
        CHECK (identifier_type IN ('GTF', 'TROZA', 'ARBOL', 'TITULO')),
    identifier_value_norm TEXT NOT NULL,
    display_value TEXT,
    composite_tree_key TEXT,
    titulo_habilitante_norm TEXT,
    parcela_corta_norm TEXT,
    verification_status TEXT NOT NULL,
    FOREIGN KEY (trace_id) REFERENCES trace_catalog(trace_id) ON DELETE CASCADE
);

CREATE INDEX idx_search_identifiers_type_value
    ON search_identifiers(identifier_type, identifier_value_norm);

CREATE INDEX idx_dispatches_numero_gtf
    ON dispatches(numero_gtf_norm);

CREATE INDEX idx_logs_codigo_troza
    ON logs(codigo_troza_norm);

CREATE INDEX idx_trace_catalog_tree
    ON trace_catalog(composite_tree_key);

CREATE INDEX idx_trace_catalog_tree_simple
    ON trace_catalog(codigo_arbol_norm);

CREATE INDEX idx_species_balances_scope
    ON species_balances(titulo_habilitante_norm, parcela_corta_norm, especie_norm);

CREATE INDEX idx_trace_catalog_status
    ON trace_catalog(verification_status);

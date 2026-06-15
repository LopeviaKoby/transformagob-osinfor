# Catalog Data Dictionary

## Alcance
`db/huella_catalog.db` integra censo, muestra supervisada, libros de operaciones y balances PDF para reconstruir trazabilidad por arbol compuesto, troza, GTF y balance por especie/parcela.

## Reglas base
- Llave de arbol: `titulo_habilitante + parcela_corta + codigo_arbol`
- Llave de troza: `titulo_habilitante + parcela_corta + codigo_troza`
- Llave de balance: `titulo_habilitante + parcela_corta + especie`
- Los volumenes normalizados se almacenan como texto decimal canonico.
- El campo `R` se conserva solo como dato privado y nunca decide estados.

## Tablas

### `build_metadata`
- Metadatos de construccion del catalogo.

### `data_sources`
- Inventario de fuentes procesadas.
- Incluye ruta relativa, hash SHA-256, tamanio, hojas o paginas y conteos de filas procesadas/cargadas/rechazadas.

### `titles`
- Catalogo de titulos habilitantes.
- Guarda version original y normalizada, titular, plan y resolucion cuando existen.

### `trees`
- Registros de censo por arbol.
- Columnas clave: `titulo_habilitante_norm`, `parcela_corta_norm`, `codigo_arbol_norm`, `composite_tree_key`.
- Conserva `raw_payload_json` y `normalized_payload_json`.

### `supervisions`
- Registros de supervision/muestra supervisada.
- Se vinculan por `composite_tree_key`.
- `especie_norm` representa la especie observada en supervision.

### `fellings`
- Registros de tala canonicos por arbol compuesto.
- Conserva fecha, volumen, diametros, longitud, `r_private_value` y observaciones privadas.

### `logs`
- Registros de trozado canonicos por troza compuesta.
- Incluye `codigo_troza_norm`, `codigo_arbol_padre_norm`, volumen y datos privados.

### `dispatches`
- Registros de despacho por troza y GTF.
- Incluye `numero_gtf_norm`, `codigo_despacho_norm` y linaje de hoja/fila.

### `species_balances`
- Filas de balance extraidas desde PDF con `pypdf`.
- Incluye `product_type`, especie normalizada, volumen autorizado, extraido, saldo y fragmento fuente.

### `trace_catalog`
- Vista materializada por arbol compuesto.
- Resume especie, volumenes, conteos de trozas/GTF, estado general y hash determinista del expediente.

### `trace_checks`
- Resultado de controles por expediente.
- Estados permitidos: `PASS`, `FAIL`, `NOT_EVALUATED`.

### `search_identifiers`
- Indice de busqueda por `GTF`, `TROZA`, `ARBOL` y `TITULO`.
- Puede devolver multiples coincidencias para codigos de arbol ambiguos.

## Controles cargados
- `census_present`
- `felling_present`
- `logs_present`
- `dispatch_present`
- `gtf_present`
- `dispatched_logs_registered`
- `supervision_species_match`
- `operation_species_match`
- `census_volume_vs_felling`
- `felling_volume_vs_logs`
- `species_balance_available`
- `species_balance_non_negative`
- `gtf_scope_consistent`
- `source_r_interpreted`

## Estados generales
- `CONSISTENTE`
- `POR_REVISAR`
- `INCOMPLETO`
- `NO_EVALUADO`

## Privacidad
El bloque publico usado para el hash y la traza no incluye coordenadas, DNI, RUC, placas, inspectores, observaciones internas, valor de `R` ni rutas absolutas.

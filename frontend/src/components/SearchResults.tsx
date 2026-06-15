import type { SearchResult } from '../types/search';
import { StatusBadge } from './StatusBadge';
import styles from './SearchResults.module.css';

interface Props {
  query: string;
  isLoading: boolean;
  errorMessage: string | null;
  results: SearchResult[];
  hasSearched: boolean;
  onSelect: (traceId: string) => void;
}

export function SearchResults({
  query,
  isLoading,
  errorMessage,
  results,
  hasSearched,
  onSelect,
}: Props) {
  if (isLoading) {
    return <p className={styles.message}>Buscando registros…</p>;
  }

  if (errorMessage) {
    return (
      <div className={styles.error} role="alert">
        <p>{errorMessage}</p>
      </div>
    );
  }

  if (!hasSearched) {
    return null;
  }

  if (results.length === 0) {
    return (
      <section className={styles.panel}>
        <h2 className={styles.heading}>No encontramos registros con ese código.</h2>
        <p className={styles.help}>
          Revisa el código e inténtalo nuevamente.
        </p>
      </section>
    );
  }

  return (
    <section className={styles.panel}>
      <div className={styles.header}>
        <h2 className={styles.heading}>
          {results.length === 1 ? 'Resultado encontrado' : 'Resultados encontrados'}
        </h2>
        <p className={styles.help}>
          {results.length === 1
            ? `Abriremos el resultado de ${query}.`
            : 'Selecciona el registro que corresponde al código consultado.'}
        </p>
      </div>

      <div className={styles.list}>
        {results.map((result) => (
          <button
            key={`${result.trace_id}-${result.identifier_type}-${result.identifier}`}
            type="button"
            className={styles.card}
            onClick={() => onSelect(result.trace_id)}
          >
            <div className={styles.cardTop}>
              <span className={styles.identifier}>{result.identifier}</span>
              <StatusBadge status={result.status} compact />
            </div>
            <p className={styles.tree}>Árbol {result.codigo_arbol} · {result.parcela_corta}</p>
            <p className={styles.species}>{result.especie ?? 'Especie no disponible'}</p>
            <p className={styles.title}>{result.titulo_habilitante}</p>
          </button>
        ))}
      </div>
    </section>
  );
}

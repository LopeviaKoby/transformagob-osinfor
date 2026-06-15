import type { CaseSummary } from '../types/verification';
import { StatusBadge } from './StatusBadge';
import styles from './CaseList.module.css';

interface Props {
  cases: CaseSummary[];
  selectedId: string | null;
  onSelect: (caseId: string) => void;
}

function getCommonName(species: string | null): string {
  if (!species) return '—';
  const parts = species.split('|');
  if (parts.length > 1) {
    return parts[1].trim();
  }
  return species.trim();
}

export function CaseList({ cases, selectedId, onSelect }: Props) {
  return (
    <nav aria-label="Casos" className={styles.nav}>
      <h2 className={styles.title}>Casos</h2>
      <ul className={styles.list} role="list">
        {cases.map((c) => {
          const isActive = c.case_id === selectedId;
          return (
            <li key={c.case_id}>
              <button
                type="button"
                className={styles.card}
                aria-current={isActive ? 'true' : undefined}
                onClick={() => onSelect(c.case_id)}
              >
                <span className={styles.tree}>
                  Árbol <strong>{c.codigo_arbol}</strong>
                </span>
                <span className={styles.species}>
                  {getCommonName(c.especie_censo)}
                </span>
                <span className={styles.parcel}>{c.parcela_corta}</span>
                <div style={{ marginTop: '0.2rem' }}>
                  <StatusBadge
                    status={c.verification_status}
                    text={c.attestation_eligible ? 'Consistente' : 'Por revisar'}
                  />
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

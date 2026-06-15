import type { VerificationStatus } from '../types/verification';
import styles from './StatusBadge.module.css';

export const STATUS_PRESENTATION: Record<
  VerificationStatus,
  { label: string; symbol: string; mod: string }
> = {
  CONSISTENTE: {
    label: 'Evidencia consistente',
    symbol: '✓',
    mod: styles.consistent,
  },
  POR_REVISAR: {
    label: 'Evidencia con observaciones',
    symbol: '!',
    mod: styles.warning,
  },
  INCOMPLETO: {
    label: 'Información incompleta',
    symbol: '•',
    mod: styles.incomplete,
  },
  NO_EVALUADO: {
    label: 'Información no evaluada',
    symbol: '?',
    mod: styles.unevaluated,
  },
  INCONSISTENTE: {
    label: 'Evidencia con observaciones',
    symbol: '!',
    mod: styles.warning,
  },
};

export function getStatusPresentation(status: VerificationStatus) {
  return STATUS_PRESENTATION[status];
}

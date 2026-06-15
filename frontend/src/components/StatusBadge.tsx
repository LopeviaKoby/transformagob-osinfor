import styles from './StatusBadge.module.css';
import type { VerificationStatus } from '../types/verification';
import { getStatusPresentation } from './statusPresentation';

interface Props {
  status: VerificationStatus;
  compact?: boolean;
  text?: string;
}

export function StatusBadge({ status, compact = false, text }: Props) {
  const { label, symbol, mod } = getStatusPresentation(status);
  const displayText = text ?? label;
  return (
    <span
      className={`${styles.badge} ${mod} ${compact ? styles.compact : ''}`}
      aria-label={displayText}
    >
      <span className={styles.symbol} aria-hidden="true">
        {symbol}
      </span>
      <span className={styles.text}>{displayText}</span>
    </span>
  );
}

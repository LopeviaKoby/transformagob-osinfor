import type { Validacion } from '../types/verification';
import {
  getValidationLabel,
  getValidationStatusLabel,
} from './validationPresentation';
import styles from './ValidationList.module.css';

interface Props {
  validaciones: Validacion[];
}

const STATUS_CONFIG = {
  PASS: { label: getValidationStatusLabel('PASS'), mod: styles.pass },
  FAIL: { label: getValidationStatusLabel('FAIL'), mod: styles.fail },
  NOT_EVALUATED: { label: getValidationStatusLabel('NOT_EVALUATED'), mod: styles.notEval },
} as const;

export function ValidationList({ validaciones }: Props) {
  const passCount = validaciones.filter((v) => v.status === 'PASS').length;
  const failCount = validaciones.filter((v) => v.status === 'FAIL').length;

  const summaryText = failCount === 0
    ? `${passCount} controles cumplen.`
    : `${passCount} cumplen · ${failCount} por revisar.`;

  return (
    <div className={styles.wrapper}>
      <p className={styles.summary}>{summaryText}</p>
      <details open={failCount > 0} className={styles.details}>
        <summary className={styles.summaryBtn}>Ver controles</summary>
        <ul className={styles.list} role="list">
          {validaciones.map((v) => {
            const { label, mod } = STATUS_CONFIG[v.status];
            return (
              <li key={v.name} className={`${styles.item} ${mod}`}>
                <span className={styles.name}>{getValidationLabel(v.name)}</span>
                <span className={styles.result}>{label}</span>
              </li>
            );
          })}
        </ul>
      </details>
    </div>
  );
}

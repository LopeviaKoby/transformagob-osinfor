import styles from './VolumeFlow.module.css';

interface Props {
  censo: number | null;
  tala: number | null;
  trozado: number | null;
}

function fmt(v: number | null): string {
  if (v === null) return '—';
  return v.toFixed(3) + ' m³';
}

export function VolumeFlow({ censo, tala, trozado }: Props) {
  const alert =
    tala !== null && trozado !== null && tala < trozado;

  return (
    <div className={styles.wrapper}>
      <ol className={styles.flow} aria-label="Flujo de volúmenes">
        <li className={styles.step}>
          <span className={styles.stage}>Censo</span>
          <span className={styles.value}>{fmt(censo)}</span>
        </li>
        <li className={styles.step}>
          <span className={styles.stage}>Tala</span>
          <span className={styles.value}>{fmt(tala)}</span>
        </li>
        <li className={styles.step}>
          <span className={styles.stage}>Trozado</span>
          <span className={styles.value}>{fmt(trozado)}</span>
        </li>
      </ol>
      <p
        className={alert ? styles.alertText : styles.normalText}
        role={alert ? 'alert' : undefined}
      >
        {alert
          ? 'El volumen trozado supera el volumen de tala.'
          : 'El volumen baja después de la tala.'}
      </p>
    </div>
  );
}

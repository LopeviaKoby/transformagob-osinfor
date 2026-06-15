import styles from './UseCasesFaq.module.css';

export function UseCasesFaq() {
  return (
    <section className={styles.wrapper}>
      <h2 className={styles.title}>¿Para qué puedes usar esta plataforma?</h2>

      <details className={styles.item}>
        <summary className={styles.summary}>Demostrar el origen de mi madera</summary>
        <p className={styles.body}>
          Consulta y comparte la evidencia asociada a una GTF, troza o árbol.
        </p>
      </details>

      <details className={styles.item}>
        <summary className={styles.summary}>Revisar una carga o guía</summary>
        <p className={styles.body}>
          Contrasta el origen, las trozas, los volúmenes y las fuentes registradas.
        </p>
      </details>

      <details className={styles.item}>
        <summary className={styles.summary}>Verificar antes de comprar</summary>
        <p className={styles.body}>
          Revisa de dónde proviene la madera y qué información respalda su recorrido.
        </p>
      </details>
    </section>
  );
}

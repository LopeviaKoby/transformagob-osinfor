import type { FormEvent } from 'react';
import osinforLogo from '../assets/standard_logo_OSINFOR_GOB.PE-prensa-01.svg';
import styles from './SearchHome.module.css';

interface Props {
  query: string;
  isLoading: boolean;
  onQueryChange: (value: string) => void;
  onSubmit: () => void;
}

export function SearchHome({
  query,
  isLoading,
  onQueryChange,
  onSubmit,
}: Props) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <section className={styles.shell}>
      <header className={styles.banner}>
        <div className={styles.logoFrame}>
          <img src={osinforLogo} alt="OSINFOR" className={styles.logo} />
        </div>
        <div className={styles.copy}>
          <p className={styles.eyebrow}>OSINFOR · PROTOTIPO</p>
          <h1 className={styles.title}>Huella Digital del Árbol</h1>
        </div>
      </header>

      <form className={styles.form} onSubmit={handleSubmit}>
        <label className={styles.label} htmlFor="search-input">
          Busca por GTF, troza, árbol o título habilitante
        </label>
        <div className={styles.row}>
          <input
            id="search-input"
            className={styles.input}
            type="text"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Ingresa un código"
            maxLength={100}
            autoComplete="off"
          />
          <button type="submit" className={styles.button} disabled={isLoading}>
            {isLoading ? 'Buscando…' : 'Verificar'}
          </button>
        </div>
        <p className={styles.help}>
          Puedes consultar una GTF, una troza, un árbol o un título habilitante.
        </p>
      </form>
    </section>
  );
}

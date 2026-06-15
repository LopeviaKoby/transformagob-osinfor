import type { ReactNode } from 'react';
import styles from './DetailSection.module.css';

interface Props {
  title: string;
  children: ReactNode;
}

export function DetailSection({ title, children }: Props) {
  return (
    <section className={styles.section}>
      <h3 className={styles.heading}>{title}</h3>
      <div className={styles.body}>{children}</div>
    </section>
  );
}

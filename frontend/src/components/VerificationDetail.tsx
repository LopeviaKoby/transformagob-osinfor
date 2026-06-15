import { useState } from 'react';
import type { VerificationDetail } from '../types/verification';
import { DetailSection } from './DetailSection';
import { StatusBadge } from './StatusBadge';
import { getStatusPresentation } from './statusPresentation';
import { ValidationList } from './ValidationList';
import { VerificationQr } from './VerificationQr';
import { VolumeFlow } from './VolumeFlow';
import styles from './VerificationDetail.module.css';

interface Props {
  detail: VerificationDetail;
  onNewSearch?: () => void;
}

/** Orden lógico de etapas del linaje */
const LINEAGE_ORDER = [
  'censo',
  'muestra_supervisada',
  'tala',
  'trozado',
  'despacho',
  'balance',
];

const STAGE_LABELS: Record<string, string> = {
  censo: 'Censo',
  muestra_supervisada: 'Supervisión',
  tala: 'Tala',
  trozado: 'Trozado',
  despacho: 'Despacho',
  balance: 'Balance',
};

function formatVolume(value: number | null | undefined): string {
  if (value == null) return '—';
  return `${value.toFixed(3)} m³`;
}

export function VerificationDetail({ detail, onNewSearch }: Props) {
  const [copyLabel, setCopyLabel] = useState('Copiar huella');
  const [copyAnnounce, setCopyAnnounce] = useState('');

  const speciesMismatch =
    detail.especie_censo !== null &&
    detail.especie_supervision !== null &&
    detail.especie_censo !== detail.especie_supervision;

  const statusPresentation = getStatusPresentation(detail.verification_status);
  const headingText = {
    CONSISTENTE: 'Los datos coinciden entre etapas.',
    POR_REVISAR: 'Hay diferencias por revisar.',
    INCONSISTENTE: 'Hay diferencias por revisar.',
    INCOMPLETO: 'Faltan etapas o registros para completar la cadena.',
    NO_EVALUADO: 'La información disponible no permite evaluar toda la cadena.',
  }[detail.verification_status];

  // Ordenar etapas de linaje según el orden lógico definido
  const sortedStages = [...detail.lineage_stages].sort((a, b) => {
    const ia = LINEAGE_ORDER.indexOf(a);
    const ib = LINEAGE_ORDER.indexOf(b);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });

  async function handleCopyHash() {
    try {
      await navigator.clipboard.writeText(detail.evidence_hash_sha256);
      setCopyLabel('Huella copiada');
      setCopyAnnounce('Huella digital copiada al portapapeles.');
      setTimeout(() => {
        setCopyLabel('Copiar huella');
        setCopyAnnounce('');
      }, 2500);
    } catch {
      setCopyAnnounce('No se pudo copiar. Selecciona el texto manualmente.');
      setTimeout(() => setCopyAnnounce(''), 3000);
    }
  }

  const shortHash =
    detail.evidence_hash_sha256.slice(0, 12) +
    '...' +
    detail.evidence_hash_sha256.slice(-12);

  return (
    <article className={styles.article}>
      {/* ── Encabezado ─────────────────────────────────────────── */}
      <header className={styles.header}>
        <div className={styles.headerMain}>
          <span className={styles.treeCode}>
            Árbol {detail.codigo_arbol ?? '—'}
          </span>
          <StatusBadge
            status={detail.verification_status}
            text={statusPresentation.label}
          />
          {onNewSearch && (
            <button
              type="button"
              className={styles.secondaryBtn}
              onClick={onNewSearch}
            >
              Nueva búsqueda
            </button>
          )}
          <button
            type="button"
            className={styles.printBtn}
            onClick={() => window.print()}
            aria-label="Imprimir resumen del expediente seleccionado"
          >
            Imprimir resumen
          </button>
        </div>
        <p className={styles.headingText}>{headingText}</p>
      </header>

      {/* ── Origen ──────────────────────────────────────────── */}
      <DetailSection title="Origen">
        <dl className={styles.dl}>
          <dt>Titular</dt>
          <dd>{detail.titular ?? '—'}</dd>
          <dt>Título habilitante</dt>
          <dd>{detail.titulo_habilitante ?? '—'}</dd>
          <dt>Parcela</dt>
          <dd>{detail.parcela_corta ?? '—'}</dd>
          <dt>Plan</dt>
          <dd>{detail.plan_operativo ?? '—'}</dd>
          <dt>Resolución</dt>
          <dd>{detail.resolucion ?? '—'}</dd>
        </dl>
      </DetailSection>

      {/* ── Especie ────────────────────────────────────────── */}
      <DetailSection title="Especie">
        <dl className={styles.dl}>
          <dt>Censo</dt>
          <dd>{detail.especie_censo ?? '—'}</dd>
          <dt>Supervisión</dt>
          <dd
            className={speciesMismatch ? styles.mismatch : undefined}
            aria-label={
              speciesMismatch
                ? `${detail.especie_supervision} — No coincide`
                : undefined
            }
          >
            {detail.especie_supervision ?? '—'}
            {speciesMismatch ? (
              <span className={styles.mismatchTag}>No coincide</span>
            ) : (
              <span className={styles.matchTag}>Coincide</span>
            )}
          </dd>
        </dl>
      </DetailSection>

      {/* ── Volumen ───────────────────────────────────────── */}
      <DetailSection title="Volumen">
        <VolumeFlow
          censo={detail.volumen_censo_m3}
          tala={detail.volumen_tala_m3}
          trozado={detail.volumen_trozado_m3}
        />
      </DetailSection>

      {detail.balance?.available && (
        <DetailSection title="Balance">
          <p className={styles.balanceText}>
            Balance de la especie en esta parcela.
          </p>
          <dl className={styles.dl}>
            <dt>Especie</dt>
            <dd>{detail.balance.species ?? '—'}</dd>
            <dt>Volumen autorizado</dt>
            <dd>{formatVolume(detail.balance.authorized_m3)}</dd>
            <dt>Volumen extraído reportado</dt>
            <dd>{formatVolume(detail.balance.extracted_reported_m3)}</dd>
            <dt>Saldo reportado</dt>
            <dd>{formatVolume(detail.balance.remaining_reported_m3)}</dd>
          </dl>
        </DetailSection>
      )}

      {/* ── Controles ────────────────────────────────────── */}
      <DetailSection title="Controles">
        <ValidationList validaciones={detail.validaciones} />
      </DetailSection>

      {/* ── Transporte ────────────────────────────────────── */}
      <DetailSection title="Transporte">
        <div className={styles.mobilGrid}>
          <div>
            <h4 className={styles.subhead}>Trozas</h4>
            <ul className={styles.chipList} role="list">
              {detail.trozas.map((t) => (
                <li key={t} className={styles.chip}>{t}</li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className={styles.subhead}>GTF</h4>
            <ul className={styles.chipList} role="list">
              {detail.gtf.map((g) => (
                <li key={g} className={styles.chip}>{g}</li>
              ))}
            </ul>
          </div>
        </div>
      </DetailSection>

      {/* ── Fuentes ──────────────────────────────── */}
      <DetailSection title="Fuentes">
        <h4 className={styles.subhead}>Registros usados</h4>
        <ul className={styles.chipList} aria-label="Etapas de linaje" role="list">
          {sortedStages.map((stage) => (
            <li key={stage} className={styles.chip}>
              {STAGE_LABELS[stage] ?? stage.replace(/_/g, ' ')}
            </li>
          ))}
        </ul>

        <h4 className={styles.subhead} style={{ marginTop: '1rem' }}>
          Huella digital
        </h4>
        <div className={styles.hashBlock}>
          <code className={styles.hash}>{shortHash}</code>
          <button
            type="button"
            className={styles.copyBtn}
            onClick={handleCopyHash}
            aria-label="Copiar huella digital al portapapeles"
          >
            {copyLabel}
          </button>
        </div>
        <p
          className={styles.copyAnnounce}
          aria-live="polite"
          aria-atomic="true"
        >
          {copyAnnounce}
        </p>

        <details className={styles.hashDetails}>
          <summary className={styles.hashSummary}>Ver huella completa</summary>
          <div className={styles.fullHashWrapper}>
            <code className={styles.fullHash}>{detail.evidence_hash_sha256}</code>
          </div>
        </details>
      </DetailSection>

      {/* ── Verifica con QR ──────────────────────────────────── */}
      <VerificationQr
        caseId={detail.case_id}
        evidenceHash={detail.evidence_hash_sha256}
        eligible={detail.attestation_eligible}
      />

      {/* ── Disclaimer ──────────────────────────────────────── */}
      <footer className={styles.disclaimer}>
        <p>{detail.disclaimer}</p>
      </footer>
    </article>
  );
}

import { useEffect, useState } from 'react';
import QRCode from 'qrcode';
import type { VerificationDetail } from '../types/verification';
import { buildVerificationUrl } from '../utils/verificationUrl';
import { getStatusPresentation } from './statusPresentation';
import {
  getValidationLabel,
  getValidationStatusLabel,
} from './validationPresentation';
import styles from './PrintableVerification.module.css';

interface Props {
  detail: VerificationDetail;
}

const STAGE_LABELS: Record<string, string> = {
  censo: 'Censo',
  muestra_supervisada: 'Supervisión',
  tala: 'Tala',
  trozado: 'Trozado',
  despacho: 'Despacho',
  balance: 'Balance',
};

export function PrintableVerification({ detail }: Props) {
  const [qrUrl, setQrUrl] = useState<string | null>(null);
  const [qrError, setQrError] = useState(false);

  useEffect(() => {
    let active = true;
    const url = buildVerificationUrl(detail.case_id);

    QRCode.toDataURL(url, {
      errorCorrectionLevel: 'M',
      width: 160,
      margin: 1,
      color: {
        dark: '#1a3d2b',
        light: '#ffffff',
      },
    })
      .then((dataUrl) => {
        if (active) {
          setQrUrl(dataUrl);
        }
      })
      .catch(() => {
        if (active) {
          setQrError(true);
        }
      });

    return () => {
      active = false;
    };
  }, [detail.case_id]);

  const statusPresentation = getStatusPresentation(detail.verification_status);
  const speciesMismatch =
    detail.especie_censo !== null &&
    detail.especie_supervision !== null &&
    detail.especie_censo !== detail.especie_supervision;

  const volumeAlert =
    detail.volumen_tala_m3 !== null &&
    detail.volumen_trozado_m3 !== null &&
    detail.volumen_tala_m3 < detail.volumen_trozado_m3;

  const passCount = detail.validaciones.filter((v) => v.status === 'PASS').length;
  const failCount = detail.validaciones.filter((v) => v.status === 'FAIL').length;
  const notEvalCount = detail.validaciones.filter((v) => v.status === 'NOT_EVALUATED').length;

  const controlSummary = failCount === 0
    ? `${passCount} controles cumplen.`
    : `${passCount} cumplen · ${failCount} por revisar.`;

  const failedControls = detail.validaciones.filter((v) => v.status === 'FAIL');

  const fmt = (v: number | null) => {
    if (v === null) return '—';
    return v.toFixed(3) + ' m³';
  };

  const sortedStages = [...detail.lineage_stages].sort((a, b) => {
    const LINEAGE_ORDER = ['censo', 'muestra_supervisada', 'tala', 'trozado', 'despacho', 'balance'];
    const ia = LINEAGE_ORDER.indexOf(a);
    const ib = LINEAGE_ORDER.indexOf(b);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });

  const stagesLine = sortedStages.map((s) => STAGE_LABELS[s] ?? s).join(' · ');

  return (
    <section data-print-root="verification" className={styles.printRoot}>
      {/* Encabezado */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <p className={styles.eyebrow}>OSINFOR · PROTOTIPO</p>
          <h1 className={styles.title}>Resumen de trazabilidad</h1>
          <div className={styles.meta}>
            <span className={styles.metaItem}><strong>Árbol:</strong> {detail.codigo_arbol ?? '—'}</span>
            <span className={styles.metaItem}>
              <strong>Estado:</strong> {statusPresentation.label}
            </span>
            <span className={styles.metaItem}><strong>ID de caso:</strong> {detail.case_id}</span>
            <span className={styles.metaItem}><strong>Parcela:</strong> {detail.parcela_corta ?? '—'}</span>
            <span className={styles.metaItem}><strong>Plan:</strong> {detail.plan_operativo ?? '—'}</span>
          </div>
        </div>
        <div className={styles.qrContainer}>
          {qrUrl ? (
            <img src={qrUrl} alt="Código QR de verificación" className={styles.qrImg} />
          ) : qrError ? (
            <span className={styles.qrError}>QR no disponible</span>
          ) : (
            <span className={styles.qrLoading}>Generando QR…</span>
          )}
        </div>
      </header>

      {/* Origen */}
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Origen</h2>
        <table className={styles.table}>
          <tbody>
            <tr>
              <th>Titular</th>
              <td>{detail.titular ?? '—'}</td>
            </tr>
            <tr>
              <th>Título habilitante</th>
              <td>{detail.titulo_habilitante ?? '—'}</td>
            </tr>
            <tr>
              <th>Resolución</th>
              <td>{detail.resolucion ?? '—'}</td>
            </tr>
            <tr>
              <th>Especie de censo</th>
              <td>{detail.especie_censo ?? '—'}</td>
            </tr>
              <tr>
                <th>Especie de supervisión</th>
                <td>
                  {detail.especie_supervision ?? '—'}{' '}
                  <span className={styles.speciesStatus}>
                  ({speciesMismatch ? 'No coincide' : 'Coincide'})
                  </span>
                </td>
              </tr>
          </tbody>
        </table>
      </div>

      {/* Volumen */}
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Volumen</h2>
        <div className={styles.volRow}>
          <span><strong>Censo:</strong> {fmt(detail.volumen_censo_m3)}</span>
          <span className={styles.arrow}>→</span>
          <span><strong>Tala:</strong> {fmt(detail.volumen_tala_m3)}</span>
          <span className={styles.arrow}>→</span>
          <span><strong>Trozado:</strong> {fmt(detail.volumen_trozado_m3)}</span>
        </div>
        <p className={volumeAlert ? styles.volConclusionAlert : styles.volConclusionNormal}>
          {volumeAlert
            ? 'El volumen trozado supera el volumen de tala.'
            : 'El volumen baja después de la tala.'}
        </p>
      </div>

      {/* Controles */}
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Controles</h2>
        <p className={styles.controlsSummary}>{controlSummary}</p>
        {failedControls.length > 0 && (
          <ul className={styles.failedList}>
            {failedControls.map((v) => (
              <li key={v.name} className={styles.failedItem}>
                <strong>{getValidationLabel(v.name)}:</strong> {getValidationStatusLabel('FAIL')}
              </li>
            ))}
          </ul>
        )}
        {notEvalCount > 0 && (
          <p className={styles.notEvalMsg}>
            {notEvalCount === 1 ? '1 control no evaluado.' : `${notEvalCount} controles no evaluados.`}
          </p>
        )}
      </div>

      {detail.balance?.available && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Balance</h2>
          <p className={styles.controlsSummary}>Balance de la especie en esta parcela.</p>
          <table className={styles.table}>
            <tbody>
              <tr>
                <th>Especie</th>
                <td>{detail.balance.species ?? '—'}</td>
              </tr>
              <tr>
                <th>Volumen autorizado</th>
                <td>{fmt(detail.balance.authorized_m3 ?? null)}</td>
              </tr>
              <tr>
                <th>Volumen extraído reportado</th>
                <td>{fmt(detail.balance.extracted_reported_m3 ?? null)}</td>
              </tr>
              <tr>
                <th>Saldo reportado</th>
                <td>{fmt(detail.balance.remaining_reported_m3 ?? null)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {/* Transporte */}
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Transporte</h2>
        <table className={styles.table}>
          <tbody>
            <tr>
              <th>Trozas</th>
              <td>
                {detail.trozas.length > 0 ? detail.trozas.join(', ') : 'Ninguna'}
              </td>
            </tr>
            <tr>
              <th>GTF</th>
              <td>
                {detail.gtf.length > 0 ? detail.gtf.join(', ') : 'Ninguno'}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Fuentes */}
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Fuentes</h2>
        <p className={styles.stagesLine}>{stagesLine}</p>
      </div>

      {/* Huella digital */}
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Huella digital</h2>
        <code className={styles.fullHash}>{detail.evidence_hash_sha256}</code>
      </div>

      {/* Disclaimer y bloque final */}
      <footer className={styles.footer}>
        <p className={styles.disclaimer}>{detail.disclaimer}</p>
        <p className={styles.sourceMsg}>Datos obtenidos de las fuentes incorporadas en este prototipo.</p>
      </footer>
    </section>
  );
}

import { useEffect, useRef, useState } from 'react';
import QRCode from 'qrcode';
import { buildVerificationUrl } from '../utils/verificationUrl';
import styles from './VerificationQr.module.css';

interface Props {
  caseId: string;
  evidenceHash: string;
  eligible: boolean;
}

type QrState =
  | { status: 'loading' }
  | { status: 'ok'; dataUrl: string; verificationUrl: string }
  | { status: 'error' };

const isLocalhost =
  typeof window !== 'undefined' &&
  (window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1');

export function VerificationQr({ caseId, eligible }: Props) {
  const [qrState, setQrState] = useState<QrState>({ status: 'loading' });
  const [copyLabel, setCopyLabel] = useState('Copiar enlace');
  const [copyAnnounce, setCopyAnnounce] = useState('');
  const [prevCaseId, setPrevCaseId] = useState<string>(caseId);

  // Ajustar estado durante el renderizado cuando cambia el prop caseId
  if (caseId !== prevCaseId) {
    setPrevCaseId(caseId);
    setQrState({ status: 'loading' });
  }

  // Referencia para cleanup de promesa montada
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;

    const url = buildVerificationUrl(caseId);

    QRCode.toDataURL(url, {
      errorCorrectionLevel: 'M',
      width: 170,
      margin: 2,
      color: {
        dark: '#1a3d2b',  // verde oscuro legible
        light: '#ffffff', // fondo blanco
      },
    })
      .then((dataUrl: string) => {
        if (!mountedRef.current) return;
        setQrState({ status: 'ok', dataUrl, verificationUrl: url });
      })
      .catch(() => {
        if (!mountedRef.current) return;
        setQrState({ status: 'error' });
      });

    return () => {
      mountedRef.current = false;
    };
  }, [caseId]);

  async function handleCopyLink() {
    if (qrState.status !== 'ok') return;
    try {
      await navigator.clipboard.writeText(qrState.verificationUrl);
      setCopyLabel('Enlace copiado');
      setCopyAnnounce('Enlace copiado al portapapeles.');
    } catch {
      setCopyLabel('No se pudo copiar');
      setCopyAnnounce('No se pudo copiar el enlace.');
    }
    setTimeout(() => {
      setCopyLabel('Copiar enlace');
      setCopyAnnounce('');
    }, 2000);
  }

  const eligibilityLabel = eligible
    ? 'Consistente'
    : 'Por revisar';

  return (
    <section className={styles.wrapper} aria-label="Verifica con QR">
      <h3 className={styles.heading}>Verifica con QR</h3>
      <p className={styles.description}>
        Escanea para abrir este caso.
      </p>

      {isLocalhost && (
        <p className={styles.localNote}>
          Este QR solo funciona en este equipo. Para usarlo en otro dispositivo, publica la aplicación.
        </p>
      )}

      <div className={styles.body}>
        {/* QR */}
        <div className={styles.qrArea}>
          {qrState.status === 'loading' && (
            <div className={styles.qrPlaceholder} aria-label="Generando QR…">
              <span>Generando…</span>
            </div>
          )}
          {qrState.status === 'error' && (
            <div className={styles.qrPlaceholder} aria-label="Error al generar QR">
              <span>Error al generar el QR</span>
            </div>
          )}
          {qrState.status === 'ok' && (
            <img
              src={qrState.dataUrl}
              alt={`Código QR para verificar el expediente del árbol ${caseId}`}
              className={styles.qrImage}
              width={170}
              height={170}
            />
          )}
          <span
            className={`${styles.eligibilityTag} ${eligible ? styles.eligible : styles.ineligible}`}
          >
            {eligibilityLabel}
          </span>
        </div>

        {/* URL y acciones */}
        <div className={styles.actions}>
          {qrState.status === 'ok' && (
            <>
              <p className={styles.urlLabel}>Enlace</p>
              <code className={styles.urlText}>{qrState.verificationUrl}</code>

              <div className={styles.btns}>
                <button
                  type="button"
                  className={styles.copyBtn}
                  onClick={handleCopyLink}
                  aria-label="Copiar enlace de verificación al portapapeles"
                >
                  {copyLabel}
                </button>
                <a
                  href={qrState.verificationUrl}
                  target="_blank"
                  rel="noreferrer"
                  className={styles.openLink}
                  aria-label={`Abrir verificación del árbol ${caseId} en nueva pestaña`}
                >
                  Abrir caso
                </a>
              </div>

              <p
                className={styles.announce}
                aria-live="polite"
                aria-atomic="true"
              >
                {copyAnnounce}
              </p>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

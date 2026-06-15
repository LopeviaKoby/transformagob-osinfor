import { useCallback, useEffect, useState } from 'react';
import { searchCatalog } from './api/searchApi';
import { getVerification } from './api/verificationApi';
import { SearchHome } from './components/SearchHome';
import { SearchResults } from './components/SearchResults';
import { UseCasesFaq } from './components/UseCasesFaq';
import { PrintableVerification } from './components/PrintableVerification';
import { VerificationDetail } from './components/VerificationDetail';
import type { SearchResult } from './types/search';
import type { VerificationDetail as VerificationDetailType } from './types/verification';
import {
  clearVerificationUrl,
  getRequestedCaseId,
  getRequestedSearchQuery,
  updateVerificationUrl,
} from './utils/verificationUrl';
import './App.css';

function assertNotRawObject(label: string, value: unknown): void {
  if (import.meta.env.DEV && value !== null && typeof value === 'object' && !Array.isArray(value)) {
    console.warn(`[DEV] Se intentó renderizar un objeto en ${label}. Verifica que no se expongan datos crudos.`);
  }
}

type SearchState =
  | { status: 'idle'; results: SearchResult[]; query: string; message: null }
  | { status: 'loading'; results: SearchResult[]; query: string; message: null }
  | { status: 'results'; results: SearchResult[]; query: string; message: null }
  | { status: 'empty'; results: SearchResult[]; query: string; message: null }
  | { status: 'error'; results: SearchResult[]; query: string; message: string };

type DetailState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ok'; data: VerificationDetailType }
  | { status: 'error'; message: string };

export default function App() {
  const requestedCaseId = getRequestedCaseId();
  const requestedSearchQuery = getRequestedSearchQuery();
  const [searchQuery, setSearchQuery] = useState(requestedSearchQuery ?? '');
  const [searchState, setSearchState] = useState<SearchState>({
    status: 'idle',
    results: [],
    query: '',
    message: null,
  });
  const [selectedId, setSelectedId] = useState<string | null>(requestedCaseId);
  const [detailState, setDetailState] = useState<DetailState>(
    requestedCaseId ? { status: 'loading' } : { status: 'idle' }
  );
  const [detailKey, setDetailKey] = useState(0);

  useEffect(() => {
    if (!selectedId) {
      return;
    }

    const controller = new AbortController();

    function onLoad(data: VerificationDetailType) {
      assertNotRawObject('VerificationDetail root', data);
      setDetailState({ status: 'ok', data });
    }

    function onError(err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') return;
      const message = err instanceof Error ? err.message : 'Error al cargar el detalle.';
      setDetailState({ status: 'error', message });
    }

    getVerification(selectedId, controller.signal).then(onLoad).catch(onError);

    return () => controller.abort();
  }, [selectedId, detailKey]);

  const openVerification = useCallback((traceId: string) => {
    setSelectedId(traceId);
    setDetailState({ status: 'loading' });
    setDetailKey((current) => current + 1);
    updateVerificationUrl(traceId);
  }, []);

  const performSearch = useCallback((rawQuery: string) => {
    const normalized = rawQuery.trim();
    if (!normalized) {
      setSearchState({
        status: 'error',
        results: [],
        query: '',
        message: 'Ingresa un código para buscar.',
      });
      return;
    }

    const controller = new AbortController();
    setSearchState({
      status: 'loading',
      results: [],
      query: normalized,
      message: null,
    });

    searchCatalog(normalized, controller.signal)
      .then((response) => {
        if (response.count === 1) {
          setSearchState({
            status: 'results',
            results: response.results,
            query: normalized,
            message: null,
          });
          openVerification(response.results[0].trace_id);
          return;
        }

        setSelectedId(null);
        setDetailState({ status: 'idle' });
        setSearchState({
          status: response.count === 0 ? 'empty' : 'results',
          results: response.results,
          query: normalized,
          message: null,
        });
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : 'No pudimos completar la búsqueda.';
        setSearchState({
          status: 'error',
          results: [],
          query: normalized,
          message,
        });
      });
  }, [openVerification]);

  useEffect(() => {
    if (requestedCaseId || !requestedSearchQuery) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      performSearch(requestedSearchQuery);
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [performSearch, requestedCaseId, requestedSearchQuery]);

  const handleSubmitSearch = useCallback(() => {
    performSearch(searchQuery);
  }, [performSearch, searchQuery]);

  const handleSelectResult = useCallback((traceId: string) => {
    openVerification(traceId);
  }, [openVerification]);

  const handleRetryDetail = useCallback(() => {
    if (!selectedId) return;
    setDetailState({ status: 'loading' });
    setDetailKey((current) => current + 1);
  }, [selectedId]);

  const handleNewSearch = useCallback(() => {
    setSelectedId(null);
    setDetailState({ status: 'idle' });
    setSearchQuery('');
    setSearchState({
      status: 'idle',
      results: [],
      query: '',
      message: null,
    });
    clearVerificationUrl();
  }, []);

  const isHome = selectedId === null;

  return (
    <main className={isHome ? 'app-main app-main-home' : 'app-main app-main-detail'}>
      {isHome ? (
        <section className="app-home" aria-label="Buscador de verificación">
          <SearchHome
            query={searchQuery}
            isLoading={searchState.status === 'loading'}
            onQueryChange={setSearchQuery}
            onSubmit={handleSubmitSearch}
          />
          <SearchResults
            query={searchState.query}
            isLoading={searchState.status === 'loading'}
            errorMessage={searchState.status === 'error' ? searchState.message : null}
            results={searchState.results}
            hasSearched={searchState.status !== 'idle'}
            onSelect={handleSelectResult}
          />
          <UseCasesFaq />
        </section>
      ) : (
        <section className="app-detail" aria-label="Detalle del comprobante">
          {detailState.status === 'loading' && (
            <p className="state-msg" aria-live="polite">
              Cargando comprobante…
            </p>
          )}
          {detailState.status === 'error' && (
            <div className="state-error" role="alert">
              <p>{detailState.message}</p>
              <div className="state-actions">
                <button type="button" className="btn-retry" onClick={handleRetryDetail}>
                  Reintentar
                </button>
                <button type="button" className="btn-secondary" onClick={handleNewSearch}>
                  Nueva búsqueda
                </button>
              </div>
            </div>
          )}
          {detailState.status === 'ok' && (
            <>
              <VerificationDetail
                detail={detailState.data}
                onNewSearch={handleNewSearch}
              />
              <PrintableVerification detail={detailState.data} />
            </>
          )}
        </section>
      )}
    </main>
  );
}

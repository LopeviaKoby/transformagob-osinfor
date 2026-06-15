import type { VerificationStatus } from './verification';

export interface SearchResult {
  trace_id: string;
  identifier_type: 'GTF' | 'TROZA' | 'ARBOL' | 'TITULO';
  identifier: string;
  codigo_arbol: string;
  parcela_corta: string;
  titulo_habilitante: string;
  especie: string | null;
  status: VerificationStatus;
}

export interface SearchResponse {
  query: string;
  detected_type: 'GTF' | 'TROZA' | 'ARBOL' | 'TITULO';
  count: number;
  results: SearchResult[];
}

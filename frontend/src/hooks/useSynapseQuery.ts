'use client';

import { useState, useRef } from 'react';
import { getApiBaseUrl } from '@/lib/api-base';
import { SynapseResponse } from '@/types/synapse';

export function useSynapseQuery() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<SynapseResponse | null>(null);
  /** Continuidad Cortex Agent: se envía en cada ask tras la primera respuesta */
  const conversationIdRef = useRef<string | null>(null);

  const API_URL = getApiBaseUrl();

  const askSynapse = async (query: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const payload: Record<string, string> = {
        query,
        tenant_id: 'Lobueno_Main',
      };
      if (conversationIdRef.current) {
        payload.conversation_id = conversationIdRef.current;
      }

      const res = await fetch(`${API_URL}/api/synapse/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        let detail = `El servidor respondió ${res.status}.`;
        try {
          const errBody = (await res.json()) as { detail?: unknown };
          const d = errBody?.detail;
          if (typeof d === 'string' && d.trim()) {
            detail = d.trim();
          } else if (Array.isArray(d)) {
            detail = d
              .map((item: { msg?: string }) => (typeof item?.msg === 'string' ? item.msg : JSON.stringify(item)))
              .join(' ');
          }
        } catch {
          /* cuerpo no JSON */
        }
        throw new Error(detail);
      }

      const data: SynapseResponse = await res.json();
      if (typeof data.conversation_id === 'string' && data.conversation_id.length > 0) {
        conversationIdRef.current = data.conversation_id;
      }
      setResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido al procesar la consulta.');
      console.error('[Synapse Hook Error]', err);
    } finally {
      setIsLoading(false);
    }
  };

  return { askSynapse, isLoading, error, response };
}

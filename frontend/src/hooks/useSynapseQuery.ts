'use client';

import { useState, useRef } from 'react';
import { SynapseResponse } from '@/types/synapse';

export function useSynapseQuery() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<SynapseResponse | null>(null);
  /** Continuidad Cortex Agent: se envía en cada ask tras la primera respuesta */
  const conversationIdRef = useRef<string | null>(null);

  // undefined → dev local. '' → mismo origen (nginx en EC2: /api → FastAPI).
  const raw = process.env.NEXT_PUBLIC_API_URL;
  let API_URL: string;
  if (raw === undefined) {
    API_URL = 'http://127.0.0.1:8000';
  } else if (raw.trim() === '') {
    API_URL = '';
  } else {
    const t = raw.trim();
    API_URL = t.startsWith('http') ? t : `https://${t}`;
  }

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
        throw new Error('No se pudo conectar con el motor de Synapse.');
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

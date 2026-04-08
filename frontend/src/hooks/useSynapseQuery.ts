'use client';

import { useState } from 'react';
import { SynapseResponse } from '@/types/synapse';

export function useSynapseQuery() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<SynapseResponse | null>(null);

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
      const res = await fetch(`${API_URL}/api/synapse/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query,
          tenant_id: 'Lobueno_Main', // Aquí iría el ID del cliente logueado
        }),
      });

      if (!res.ok) {
        throw new Error('No se pudo conectar con el motor de Synapse.');
      }

      const data: SynapseResponse = await res.json();
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

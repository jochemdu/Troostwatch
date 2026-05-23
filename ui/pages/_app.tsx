import type { AppProps } from 'next/app';
import '../styles/globals.css';
import { useEffect, useRef, useState, createContext } from 'react';
import { createLotSocket } from '../lib/ws';
import type { LotEvent } from '../lib/types';

export const LotEventContext = createContext<{ events: LotEvent[] }>({ events: [] });

export default function App({ Component, pageProps }: AppProps) {
  const wsRef = useRef<WebSocket | null>(null);
  const [events, setEvents] = useState<LotEvent[]>([]);

  useEffect(() => {
    wsRef.current = createLotSocket(
      (event) => {
        setEvents((prev) => [event, ...prev].slice(0, 100)); // keep last 100 events globally
      },
      (status) => {
        // Optionally handle status globally
        // console.log('WebSocket status:', status);
      }
    );
    return () => {
      wsRef.current?.close();
    };
  }, []);

  return (
    <LotEventContext.Provider value={{ events }}>
      <Component {...pageProps} />
    </LotEventContext.Provider>
  );
}

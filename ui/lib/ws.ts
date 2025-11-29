/**
 * WebSocket client for real-time lot updates.
 *
 * Uses LotEvent from types.ts which references the generated LotView type.
 */
import type { LotEvent } from './types';

// Re-export for convenience
export type { LotEvent };

type Callback = (event: LotEvent) => void;

type StatusCallback = (state: 'connecting' | 'open' | 'closed' | 'error') => void;

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8001/ws/lots';

export function createLotSocket(onEvent: Callback, onStatus?: StatusCallback): WebSocket {
  const socket = new WebSocket(WS_URL);

  onStatus?.('connecting');

  socket.addEventListener('open', () => {
    onStatus?.('open');
  });

  socket.addEventListener('message', (event) => {
    try {
      const parsed = JSON.parse(event.data) as LotEvent;
      onEvent(parsed);
    } catch (error) {
      onStatus?.('error');
    }
  });

  socket.addEventListener('close', () => onStatus?.('closed'));
  socket.addEventListener('error', () => onStatus?.('error'));

  return socket;
}

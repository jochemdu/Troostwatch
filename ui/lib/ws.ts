export type LotEvent = {
  id: string;
  status: string;
  current_bid?: number;
  buyer?: string;
  started_at?: string;
  ends_at?: string;
  message?: string;
};

type Callback = (event: LotEvent) => void;

type StatusCallback = (state: 'connecting' | 'open' | 'closed' | 'error') => void;

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000/ws/lots';

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

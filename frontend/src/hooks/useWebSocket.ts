/** Hook for WebSocket connection management. */

export function useWebSocket(_url: string) {
  // Stub — implementing Day 7
  return { connected: false, send: (_data: unknown) => {}, lastMessage: null };
}

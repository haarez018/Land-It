/** WebSocket connection manager for real-time streaming. */

export class WSConnection {
  private ws: WebSocket | null = null;

  connect(url: string, onMessage: (data: unknown) => void) {
    this.ws = new WebSocket(url);
    this.ws.onmessage = (e) => onMessage(JSON.parse(e.data));
  }

  send(data: unknown) {
    this.ws?.send(JSON.stringify(data));
  }

  close() {
    this.ws?.close();
    this.ws = null;
  }
}

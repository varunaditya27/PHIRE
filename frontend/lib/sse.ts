// Minimal Server-Sent Events client over fetch, so POST endpoints (chat) can stream too --
// the browser's EventSource only supports GET.

export interface SSEFrame {
  event: string;
  data: unknown;
}

/** Read an SSE response, calling onFrame per event; resolves when the server closes the stream. */
export async function readSSE(
  url: string,
  init: RequestInit,
  onFrame: (frame: SSEFrame) => void
): Promise<void> {
  const response = await fetch(url, {
    ...init,
    headers: { Accept: "text/event-stream", ...init.headers },
  });
  if (!response.ok || !response.body) {
    throw new Error(`Stream failed: ${response.status} ${response.statusText}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) return;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      let event = "message";
      let data = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (data) onFrame({ event, data: JSON.parse(data) });
    }
  }
}

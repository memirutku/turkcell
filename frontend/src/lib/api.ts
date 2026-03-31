import { HealthResponse, StructuredData } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Fetch health status from the backend API.
 * Uses the Next.js rewrite proxy in development, direct URL otherwise.
 */
export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  return response.json();
}

/**
 * Stream chat response via SSE from the backend.
 * Uses fetch + ReadableStream (not EventSource, which only supports GET).
 */
export async function streamChat(
  message: string,
  sessionId: string,
  customerId: string | null,
  onToken: (token: string) => void,
  onDone: () => void,
  onError: (error: string) => void,
  onStructured?: (data: StructuredData) => void,
): Promise<void> {
  const body: Record<string, string> = {
    message,
    session_id: sessionId,
  };
  if (customerId) {
    body.customer_id = customerId;
  }

  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    if (response.status === 503) {
      onError("Asistan su an kullanilamiyor. Lutfen daha sonra tekrar deneyin.");
    } else {
      onError("Sunucu hatasi. Lutfen tekrar deneyin.");
    }
    return;
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse complete SSE lines from buffer
    const lines = buffer.split("\n");
    buffer = lines.pop() || ""; // Keep incomplete last line in buffer

    let currentEvent = "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        const dataStr = line.slice(6);
        try {
          const data = JSON.parse(dataStr);
          if (currentEvent === "token" && data.content) {
            onToken(data.content);
          } else if (currentEvent === "done") {
            onDone();
            return;
          } else if (currentEvent === "structured") {
            if (onStructured) {
              onStructured(data as StructuredData);
            }
          } else if (currentEvent === "error") {
            onError(data.message || "Bir hata olustu. Lutfen tekrar deneyin.");
            return;
          }
        } catch {
          // Skip malformed JSON lines
        }
      }
    }
  }

  // If we reach here without a done event, still notify
  onDone();
}

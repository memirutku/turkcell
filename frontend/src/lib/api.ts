import { HealthResponse, StructuredData, ActionProposal, ActionResult } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getWsBaseUrl(): string {
  const apiUrl = API_BASE_URL.replace(/\/+$/, "");
  return apiUrl.replace(/^https:/, "wss:").replace(/^http:/, "ws:");
}

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
      onError("Asistan şu an kullanılamıyor. Lütfen daha sonra tekrar deneyin.");
    } else {
      onError("Sunucu hatası. Lütfen tekrar deneyin.");
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
            onError(data.message || "Bir hata oluştu. Lütfen tekrar deneyin.");
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

/**
 * Stream agent chat response via SSE from the backend.
 * Handles action_proposal and action_result events in addition to standard chat events.
 */
export async function streamAgentChat(
  message: string,
  sessionId: string,
  customerId: string,
  onToken: (token: string) => void,
  onDone: () => void,
  onError: (error: string) => void,
  onActionProposal: (proposal: ActionProposal) => void,
  onActionResult: (result: ActionResult) => void,
  onStructured?: (data: StructuredData) => void,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/agent/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      customer_id: customerId,
    }),
  });

  if (!response.ok) {
    if (response.status === 503) {
      onError("Asistan şu an kullanılamıyor. Lütfen daha sonra tekrar deneyin.");
    } else {
      onError("Sunucu hatası. Lütfen tekrar deneyin.");
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
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let currentEvent = "";
    let receivedDone = false;
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
            receivedDone = true;
          } else if (currentEvent === "action_proposal") {
            onActionProposal(data as ActionProposal);
          } else if (currentEvent === "action_result") {
            onActionResult(data as ActionResult);
          } else if (currentEvent === "structured") {
            if (onStructured) {
              onStructured(data as StructuredData);
            }
          } else if (currentEvent === "error") {
            onError(data.message || "Bir hata oluştu. Lütfen tekrar deneyin.");
            return;
          }
        } catch {
          // Skip malformed JSON lines
        }
      }
    }
    if (receivedDone) {
      onDone();
      return;
    }
  }

  onDone();
}

/**
 * Confirm or reject an agent action and stream the result.
 */
export async function confirmAgentAction(
  threadId: string,
  approved: boolean,
  onToken: (token: string) => void,
  onDone: () => void,
  onError: (error: string) => void,
  onActionResult: (result: ActionResult) => void,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/agent/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      thread_id: threadId,
      approved,
    }),
  });

  if (!response.ok) {
    onError("Onay işlemi sırasında bir sorun oluştu. Lütfen tekrar deneyin.");
    return;
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let currentEvent = "";
    let receivedDone = false;
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
            receivedDone = true;
          } else if (currentEvent === "action_result") {
            onActionResult(data as ActionResult);
          } else if (currentEvent === "error") {
            onError(data.message || "Bir hata oluştu. Lütfen tekrar deneyin.");
            return;
          }
        } catch {
          // Skip malformed JSON lines
        }
      }
    }
    if (receivedDone) {
      onDone();
      return;
    }
  }

  onDone();
}

/**
 * Fetch customer details from the backend (includes current tariff).
 */
export async function fetchCustomer(customerId: string): Promise<{ id: string; name: string; tariff: { name: string } | null }> {
  const response = await fetch(`${API_BASE_URL}/api/bss/customers/${customerId}`);
  if (!response.ok) throw new Error(`Customer fetch failed: ${response.status}`);
  return response.json();
}

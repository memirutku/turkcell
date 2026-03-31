import { create } from "zustand";
import { Message } from "@/types";
import { streamChat } from "@/lib/api";

const SESSION_STORAGE_KEY = "turkcell-chat-session-id";

function getOrCreateSessionId(): string {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem(SESSION_STORAGE_KEY);
    if (stored) return stored;
    const newId = crypto.randomUUID();
    localStorage.setItem(SESSION_STORAGE_KEY, newId);
    return newId;
  }
  return typeof crypto !== "undefined" ? crypto.randomUUID() : "default-session";
}

interface ChatStore {
  messages: Message[];
  isStreaming: boolean;
  sessionId: string;
  error: string | null;
  customerId: string | null;
  addMessage: (role: "user" | "assistant", content: string) => string; // returns message id
  appendToLastMessage: (token: string) => void;
  setStreaming: (streaming: boolean) => void;
  setError: (error: string | null) => void;
  setCustomerId: (id: string | null) => void;
  sendMessage: (message: string) => Promise<void>;
  clearMessages: () => void;
  resetSession: () => void;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  isStreaming: false,
  sessionId: getOrCreateSessionId(),
  error: null,
  customerId: "cust-001",

  addMessage: (role, content) => {
    const id = crypto.randomUUID();
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id,
          role,
          content,
          timestamp: Date.now(),
          isStreaming: role === "assistant",
        },
      ],
    }));
    return id;
  },

  appendToLastMessage: (token) =>
    set((state) => {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, content: last.content + token };
      }
      return { messages: msgs };
    }),

  setStreaming: (isStreaming) => set({ isStreaming }),

  setError: (error) => set({ error }),

  setCustomerId: (id) => {
    const newSessionId = crypto.randomUUID();
    if (typeof window !== "undefined") {
      localStorage.setItem(SESSION_STORAGE_KEY, newSessionId);
    }
    set({
      customerId: id,
      messages: [],
      error: null,
      sessionId: newSessionId,
      isStreaming: false,
    });
  },

  sendMessage: async (message) => {
    const { sessionId, customerId, addMessage, appendToLastMessage, setStreaming, setError } = get();
    setError(null);
    setStreaming(true);
    addMessage("user", message);
    addMessage("assistant", "");

    try {
      await streamChat(
        message,
        sessionId,
        customerId,
        (token) => appendToLastMessage(token),
        () => {
          // Mark last message as not streaming
          set((state) => {
            const msgs = [...state.messages];
            const last = msgs[msgs.length - 1];
            if (last?.role === "assistant") {
              msgs[msgs.length - 1] = { ...last, isStreaming: false };
            }
            return { messages: msgs };
          });
          setStreaming(false);
        },
        (errorMsg) => {
          setError(errorMsg);
          setStreaming(false);
          // Remove the empty assistant message on error
          set((state) => {
            const msgs = [...state.messages];
            const last = msgs[msgs.length - 1];
            if (last?.role === "assistant" && last.content === "") {
              msgs.pop();
            }
            return { messages: msgs };
          });
        }
      );
    } catch {
      setError("Bir hata olustu. Lutfen tekrar deneyin.");
      setStreaming(false);
    }
  },

  clearMessages: () => set({ messages: [], error: null }),

  resetSession: () => {
    const newId = crypto.randomUUID();
    if (typeof window !== "undefined") {
      localStorage.setItem(SESSION_STORAGE_KEY, newId);
    }
    set({
      messages: [],
      error: null,
      sessionId: newId,
      isStreaming: false,
    });
  },
}));

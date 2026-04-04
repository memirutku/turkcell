"use client";
import { useState, useRef, useCallback, useEffect } from "react";
import { LiveConversationState, ActionProposal, ActionResult } from "@/types";
import { useChatStore } from "@/stores/chatStore";
import { startPCMCapture, PCMPlayer } from "@/lib/pcmAudioUtils";
import { checkMicrophoneSupport, checkSecureContext } from "@/lib/audioUtils";
import { getWsBaseUrl } from "@/lib/api";

/**
 * Hook for Gemini Live API real-time voice conversation.
 *
 * Unlike useVoiceConversation (which uses client-side Silero VAD),
 * this hook streams raw PCM16 continuously to the backend, which
 * proxies it to Gemini Live API. Gemini handles VAD, STT, LLM,
 * and TTS in a single bidirectional session.
 */
export function useVoiceLive() {
  const [conversationState, setConversationState] = useState<LiveConversationState>("off");
  const conversationStateRef = useRef<LiveConversationState>("off");
  const wsRef = useRef<WebSocket | null>(null);
  const stopCaptureRef = useRef<(() => void) | null>(null);
  const pcmPlayerRef = useRef<PCMPlayer | null>(null);
  const isMountedRef = useRef(true);
  const isFirstTextRef = useRef(true);
  const hasServerErrorRef = useRef(false);

  useEffect(() => {
    conversationStateRef.current = conversationState;
  }, [conversationState]);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const handleWsMessage = useCallback((event: MessageEvent) => {
    if (!isMountedRef.current) return;

    // Binary data = PCM16 audio from Gemini
    if (event.data instanceof Blob) {
      event.data.arrayBuffer().then((buffer) => {
        if (!isMountedRef.current) return;
        if (conversationStateRef.current !== "off") {
          setConversationState("model-speaking");
          pcmPlayerRef.current?.enqueue(buffer);
        }
      });
      return;
    }

    // ArrayBuffer binary data
    if (event.data instanceof ArrayBuffer) {
      if (conversationStateRef.current !== "off") {
        setConversationState("model-speaking");
        pcmPlayerRef.current?.enqueue(event.data);
      }
      return;
    }

    // Text data = JSON control message
    try {
      const msg = JSON.parse(event.data);

      switch (msg.type) {
        case "input_transcript": {
          if (msg.text) {
            const store = useChatStore.getState();
            store.addMessage("user", msg.text);
          }
          break;
        }

        case "text": {
          if (msg.text !== undefined) {
            const store = useChatStore.getState();
            if (isFirstTextRef.current) {
              store.addMessage("assistant", "");
              store.setStreaming(true);
              isFirstTextRef.current = false;
            }
            store.appendToLastMessage(msg.text);
          }
          break;
        }

        case "output_transcript": {
          if (msg.text) {
            const store = useChatStore.getState();
            if (isFirstTextRef.current) {
              store.addMessage("assistant", "");
              store.setStreaming(true);
              isFirstTextRef.current = false;
            }
            store.appendToLastMessage(msg.text);
          }
          break;
        }

        case "turn_complete": {
          isFirstTextRef.current = true;
          useChatStore.setState((state) => {
            const msgs = [...state.messages];
            const last = msgs[msgs.length - 1];
            if (last?.role === "assistant") {
              msgs[msgs.length - 1] = { ...last, isStreaming: false };
            }
            return { messages: msgs };
          });
          useChatStore.getState().setStreaming(false);
          // State will transition back to "connected" when audio playback ends
          break;
        }

        case "interrupted": {
          // User interrupted the model — stop audio playback immediately
          pcmPlayerRef.current?.stop();
          isFirstTextRef.current = true;
          useChatStore.setState((state) => {
            const msgs = [...state.messages];
            const last = msgs[msgs.length - 1];
            if (last?.role === "assistant") {
              msgs[msgs.length - 1] = { ...last, isStreaming: false };
            }
            return { messages: msgs };
          });
          useChatStore.getState().setStreaming(false);
          if (conversationStateRef.current !== "off") {
            setConversationState("connected");
          }
          break;
        }

        case "action_proposal": {
          setConversationState("action-pending");
          const store = useChatStore.getState();
          const proposal: ActionProposal = {
            action_type: (msg.data?.action_type as "package_activation" | "tariff_change") || "package_activation",
            description: msg.data?.description || "",
            details: msg.data?.details || {},
            thread_id: "",
          };
          store.setPendingAction(proposal);
          store.addStructuredData({
            type: "action_proposal",
            payload: proposal,
          });
          const title = proposal.action_type === "package_activation"
            ? "Paket Tanimlama"
            : "Tarife Degisikligi";
          store.announce(
            `Islem onerisi: ${title}. ${proposal.description}. Onaylamak icin Evet Onayla butonunu, iptal etmek icin Vazgec butonunu kullanin.`
          );
          break;
        }

        case "action_result": {
          const store = useChatStore.getState();
          const result: ActionResult = {
            success: !!msg.data?.success,
            action_type: (msg.data?.action_type as "package_activation" | "tariff_change") || "package_activation",
            description: msg.data?.description || "",
            details: msg.data?.details || {},
          };
          store.addStructuredData({
            type: "action_result",
            payload: result,
          });
          store.setPendingAction(null);
          if (result.success) {
            store.announce(`Islem basarili: ${result.description}`);
          } else {
            store.announce(`Islem basarisiz: ${result.description}`);
          }
          if (conversationStateRef.current === "action-pending") {
            setConversationState("connected");
          }
          break;
        }

        case "error": {
          hasServerErrorRef.current = true;
          useChatStore.getState().setError(
            msg.message || "Bir hata olustu. Lutfen tekrar deneyin."
          );
          break;
        }
      }
    } catch {
      // Ignore malformed JSON
    }
  }, []);

  const startConversation = useCallback(async () => {
    const store = useChatStore.getState();

    if (!checkSecureContext()) {
      store.setError("Ses ozelligi yalnizca guvenli baglantilarda (HTTPS veya localhost) kullanilabilir.");
      return;
    }
    if (!checkMicrophoneSupport()) {
      store.setError("Tarayiciniz ses kaydini desteklemiyor. Lutfen guncel bir tarayici kullanin.");
      return;
    }

    setConversationState("connecting");

    // Create PCM player with callback for when playback ends
    const player = new PCMPlayer(() => {
      if (isMountedRef.current && conversationStateRef.current !== "off") {
        setConversationState("connected");
      }
    });
    pcmPlayerRef.current = player;

    // Connect WebSocket
    const wsUrl = `${getWsBaseUrl()}/ws/voice-live`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      if (!isMountedRef.current) return;
      // Send init message
      const initMsg = {
        type: "init",
        session_id: useChatStore.getState().sessionId,
        customer_id: useChatStore.getState().customerId,
      };
      ws.send(JSON.stringify(initMsg));

      // Start mic capture
      // Register live confirmation callback so UI buttons route through WebSocket
      store.setLiveConfirmCallback((approved: boolean) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "confirmation", approved }));
        }
        if (conversationStateRef.current === "action-pending") {
          setConversationState("connected");
        }
      });

      startPCMCapture((pcmData) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(pcmData);
        }
      }).then((stopFn) => {
        stopCaptureRef.current = stopFn;
        if (isMountedRef.current) {
          setConversationState("connected");
          store.announce("Sesli konusma modu aktif.");
        }
      }).catch((err) => {
        console.error("Mic capture failed:", err);
        store.setError("Mikrofon erisimi saglanamadi. Lutfen izinleri kontrol edin.");
        setConversationState("off");
      });
    };

    ws.onmessage = handleWsMessage;

    ws.onclose = () => {
      if (!isMountedRef.current) return;
      useChatStore.getState().setLiveConfirmCallback(null);
      if (conversationStateRef.current !== "off") {
        if (!hasServerErrorRef.current) {
          store.setError("Ses baglantisi kapandi.");
        }
        hasServerErrorRef.current = false;
        stopCapture();
        setConversationState("off");
      }
    };

    ws.onerror = () => {
      // onclose handles the error state
    };

    wsRef.current = ws;
  }, [handleWsMessage]);

  const stopCapture = useCallback(() => {
    if (stopCaptureRef.current) {
      stopCaptureRef.current();
      stopCaptureRef.current = null;
    }
  }, []);

  const stopConversation = useCallback(() => {
    stopCapture();
    pcmPlayerRef.current?.stop();
    pcmPlayerRef.current?.destroy();
    pcmPlayerRef.current = null;
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    useChatStore.getState().setLiveConfirmCallback(null);
    setConversationState("off");
  }, [stopCapture]);

  const sendConfirmation = useCallback((approved: boolean) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "confirmation", approved }));
    }
    if (conversationStateRef.current === "action-pending") {
      setConversationState("connected");
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCapture();
      pcmPlayerRef.current?.destroy();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      useChatStore.getState().setLiveConfirmCallback(null);
    };
  }, [stopCapture]);

  return {
    conversationState,
    startConversation,
    stopConversation,
    sendConfirmation,
    // Compatibility: no VAD in Live API mode
    isVADLoading: false,
    isVADErrored: false,
  };
}

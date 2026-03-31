"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { VoiceState, VoiceWebSocketMessage } from "@/types";
import { useChatStore } from "@/stores/chatStore";
import { checkMicrophoneSupport, checkSecureContext, getAudioMimeType } from "@/lib/audioUtils";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getWsBaseUrl(): string {
  return API_BASE_URL.replace(/^http:\/\//, "ws://").replace(/^https:\/\//, "wss://");
}

const MAX_RECONNECT_ATTEMPTS = 3;
const RECONNECT_DELAYS = [1000, 2000, 4000]; // exponential backoff

export function useVoiceChat(): {
  voiceState: VoiceState;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  isVoiceSupported: boolean;
  mediaStream: MediaStream | null;
  mediaRecorder: MediaRecorder | null;
} {
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [mediaStream, setMediaStream] = useState<MediaStream | null>(null);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [isVoiceSupported] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return checkMicrophoneSupport() && checkSecureContext();
  });

  const wsRef = useRef<WebSocket | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isFirstTokenRef = useRef(true);
  const isMountedRef = useRef(true);

  // Read store values
  const sessionId = useChatStore((s) => s.sessionId);
  const customerId = useChatStore((s) => s.customerId);

  const cleanup = useCallback(() => {
    // Stop media tracks
    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
    }
    setMediaStream(null);
    setMediaRecorder(null);
    audioChunksRef.current = [];
  }, [mediaStream]);

  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const wsUrl = `${getWsBaseUrl()}/ws/voice`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      reconnectAttemptRef.current = 0;
      // Send init message
      const initMsg: VoiceWebSocketMessage = {
        type: "init",
        session_id: useChatStore.getState().sessionId,
        customer_id: useChatStore.getState().customerId,
      };
      ws.send(JSON.stringify(initMsg));
    };

    ws.onmessage = (event: MessageEvent) => {
      if (!isMountedRef.current) return;

      // Binary data = TTS audio
      if (event.data instanceof Blob) {
        const audioUrl = URL.createObjectURL(event.data);
        const audio = new Audio(audioUrl);
        setVoiceState("playing");

        audio.onended = () => {
          if (isMountedRef.current) {
            setVoiceState("idle");
          }
          URL.revokeObjectURL(audioUrl);
        };

        audio.onerror = () => {
          if (isMountedRef.current) {
            setVoiceState("idle");
          }
          URL.revokeObjectURL(audioUrl);
        };

        audio.play().catch(() => {
          // Auto-play blocked by browser
          if (isMountedRef.current) {
            setVoiceState("idle");
          }
          URL.revokeObjectURL(audioUrl);
        });
        return;
      }

      // Text data = JSON message
      try {
        const msg: VoiceWebSocketMessage = JSON.parse(event.data);

        switch (msg.type) {
          case "transcription": {
            if (msg.text) {
              const store = useChatStore.getState();
              store.addMessage("user", msg.text);
              store.setStreaming(true);
              isFirstTokenRef.current = true;
            }
            break;
          }

          case "token": {
            if (msg.content !== undefined) {
              const store = useChatStore.getState();
              if (isFirstTokenRef.current) {
                store.addMessage("assistant", "");
                isFirstTokenRef.current = false;
              }
              store.appendToLastMessage(msg.content);
            }
            break;
          }

          case "response_end": {
            // Mark last message as not streaming
            useChatStore.setState((state) => {
              const msgs = [...state.messages];
              const last = msgs[msgs.length - 1];
              if (last?.role === "assistant") {
                msgs[msgs.length - 1] = { ...last, isStreaming: false };
              }
              return { messages: msgs };
            });
            useChatStore.getState().setStreaming(false);
            // State transitions to "playing" when audio arrives, or "idle" on audio_done
            break;
          }

          case "audio_done": {
            // TTS audio finished or was unavailable
            setVoiceState((current) => {
              // If we're already playing, let audio.onended handle it
              if (current === "playing") return current;
              return "idle";
            });
            break;
          }

          case "error": {
            useChatStore.getState().setError(
              msg.message || "Bir hata olustu. Lutfen tekrar deneyin."
            );
            setVoiceState("idle");
            break;
          }
        }
      } catch {
        // Ignore malformed JSON
      }
    };

    ws.onclose = () => {
      if (!isMountedRef.current) return;

      // Attempt reconnect with backoff
      if (reconnectAttemptRef.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = RECONNECT_DELAYS[reconnectAttemptRef.current] || 4000;
        reconnectAttemptRef.current++;
        reconnectTimerRef.current = setTimeout(() => {
          if (isMountedRef.current) {
            connectWebSocket();
          }
        }, delay);
      }
    };

    ws.onerror = () => {
      // onclose will be called after onerror
    };

    wsRef.current = ws;
  }, []);

  // Connect WebSocket on mount, clean up on unmount
  useEffect(() => {
    isMountedRef.current = true;
    connectWebSocket();

    return () => {
      isMountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connectWebSocket]);

  const startRecording = useCallback(async () => {
    const store = useChatStore.getState();

    // Check secure context
    if (!checkSecureContext()) {
      store.setError(
        "Ses ozelligi yalnizca guvenli baglantilarda (HTTPS veya localhost) kullanilabilir."
      );
      return;
    }

    // Check browser support
    if (!checkMicrophoneSupport()) {
      store.setError(
        "Tarayiciniz ses kaydini desteklemiyor. Lutfen guncel bir tarayici kullanin."
      );
      return;
    }

    // Ensure WebSocket is connected
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      connectWebSocket();
      // Give it a moment to connect
      await new Promise<void>((resolve) => setTimeout(resolve, 500));
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        store.setError(
          "Ses baglantisi kurulamadi. Lutfen sayfayi yenileyip tekrar deneyin."
        );
        return;
      }
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
        },
      });

      const mimeType = getAudioMimeType();
      const recorder = new MediaRecorder(stream, { mimeType });
      audioChunksRef.current = [];

      recorder.ondataavailable = (e: BlobEvent) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = () => {
        // Collect audio and send via WebSocket
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        audioChunksRef.current = [];

        if (audioBlob.size > 100 && wsRef.current?.readyState === WebSocket.OPEN) {
          setVoiceState("processing");
          wsRef.current.send(audioBlob);
        } else if (audioBlob.size <= 100) {
          store.setError(
            "Ses algilanamadi. Lutfen mikrofonunuza yakin konusun ve tekrar deneyin."
          );
          setVoiceState("idle");
        } else {
          setVoiceState("idle");
        }

        // Stop media tracks
        stream.getTracks().forEach((track) => track.stop());
        setMediaStream(null);
        setMediaRecorder(null);
      };

      recorder.start(250); // Collect data every 250ms for chunks
      setMediaStream(stream);
      setMediaRecorder(recorder);
      setVoiceState("recording");
    } catch (err: unknown) {
      const error = err as DOMException;
      if (error.name === "NotAllowedError") {
        store.setError(
          "Mikrofon erisimi reddedildi. Tarayici ayarlarindan mikrofon iznini etkinlestirin."
        );
      } else if (error.name === "NotFoundError") {
        store.setError(
          "Mikrofon bulunamadi. Lutfen bir mikrofon baglayin."
        );
      } else {
        store.setError(
          "Mikrofon erisiminde bir hata olustu. Lutfen tekrar deneyin."
        );
      }
      setVoiceState("idle");
    }
  }, [connectWebSocket]);

  const stopRecording = useCallback(() => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
    }
  }, [mediaRecorder]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);

  return {
    voiceState,
    startRecording,
    stopRecording,
    isVoiceSupported,
    mediaStream,
    mediaRecorder,
  };
}

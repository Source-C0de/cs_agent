/**
 * Streaming client for the Green Lab FastAPI brain.
 *
 * The chat stream uses SSE (`text/event-stream`) with `event: token` and
 * `event: done`. We expose `useChatStream()` so any React component can consume
 * it without baking assumptions about the protocol.
 */
"use client";

import { useCallback, useState } from "react";

export type Citation = {
  doc_id: string;
  section?: string | null;
  snippet?: string | null;
  score?: number;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  requiresHuman?: boolean;
  intent?: string | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export function useChatStream(customerId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = useCallback(
    async (input: string, conversationId?: string) => {
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: input,
      };
      const assistantId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        userMsg,
        { id: assistantId, role: "assistant", content: "" },
      ]);
      setStreaming(true);
      setError(null);

      try {
        const r = await fetch(`${API_BASE}/api/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            customer_id: customerId,
            message: input,
            conversation_id: conversationId,
            stream: true,
          }),
        });

        if (!r.body) throw new Error("No stream");

        const reader = r.body.getReader();
        const decoder = new TextDecoder();
        let acc = "";
        let buffer = "";

        // eslint-disable-next-line no-constant-condition
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          let nlIdx;
          while ((nlIdx = buffer.indexOf("\n\n")) !== -1) {
            const frame = buffer.slice(0, nlIdx);
            buffer = buffer.slice(nlIdx + 2);
            const line = frame.split("\n").find((l) => l.startsWith("data:"));
            if (!line) continue;
            const payload = JSON.parse(line.slice(5).trim());
            if (typeof payload.token === "string") {
              acc += payload.token;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId ? { ...m, content: acc } : m,
                ),
              );
            } else if (payload.requires_human !== undefined) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        requiresHuman: !!payload.requires_human,
                        intent: payload.intent,
                        citations: payload.citations ?? [],
                      }
                    : m,
                ),
              );
            }
          }
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Unknown error");
      } finally {
        setStreaming(false);
      }
    },
    [customerId],
  );

  return { messages, send, streaming, error };
}
"use client";

import { FormEvent, useState } from "react";
import { useChatStream } from "../../lib/api";

// Demo customer. Phase 2 will swap in a Clerk auth flow + real customer id.
const DEMO_CUSTOMER = "CUST-0001";

export default function Widget() {
  const { messages, send, streaming, error } = useChatStream(DEMO_CUSTOMER);
  const [input, setInput] = useState("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");
    await send(text);
  }

  return (
    <div className="min-h-screen flex flex-col items-stretch max-w-3xl mx-auto p-6">
      <header className="mb-4">
        <h1 className="text-2xl font-semibold text-brand-dark">Green Lab Support</h1>
        <p className="text-sm text-slate-500">
          Ask about samples, methods, pricing, or book a consultation.
        </p>
      </header>

      <div className="flex-1 overflow-y-auto rounded-lg border border-slate-200 bg-white p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-slate-400 text-sm">
            Try: &ldquo;What container do I need for PFAS in drinking water?&rdquo;
          </div>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={
              m.role === "user"
                ? "bg-brand-light/20 p-3 rounded-md self-end max-w-[85%]"
                : "bg-slate-50 p-3 rounded-md max-w-[85%]"
            }
          >
            <div className="text-xs uppercase tracking-wide text-slate-500 mb-1">
              {m.role === "user" ? "You" : "Green Lab"}
            </div>
            <div className="whitespace-pre-wrap">{m.content}</div>
            {m.citations && m.citations.length > 0 && (
              <div className="mt-2">
                {m.citations.map((c) => (
                  <span key={c.doc_id + (c.section ?? "")} className="citation">
                    [{c.doc_id}{c.section ? `#${c.section}` : ""}]
                  </span>
                ))}
              </div>
            )}
            {m.requiresHuman && (
              <div className="mt-2 text-xs text-amber-700 bg-amber-50 px-2 py-1 rounded">
                This conversation has been escalated to a Green Lab team member.
              </div>
            )}
          </div>
        ))}
        {error && (
          <div className="text-sm text-red-600">Error: {error}</div>
        )}
      </div>

      <form onSubmit={onSubmit} className="mt-4 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a question…"
          className="flex-1 rounded-md border border-slate-300 px-3 py-2"
          disabled={streaming}
        />
        <button
          type="submit"
          disabled={streaming || !input.trim()}
          className="rounded-md bg-brand text-white px-4 py-2 disabled:opacity-50"
        >
          {streaming ? "Thinking…" : "Send"}
        </button>
      </form>
    </div>
  );
}
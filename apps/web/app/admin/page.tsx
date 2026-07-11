"use client";

import { useEffect, useState } from "react";

type AuditEntry = {
  id: number;
  ts: string;
  customer_id?: string | null;
  conversation_id?: string | null;
  node: string;
  decision: string;
  summary?: string | null;
  latency_ms?: number | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export default function Admin() {
  const [rows, setRows] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Phase 1: stub with empty list. Phase 2 will add a real endpoint that
    // surfaces the audit_logs table with pagination + filters.
    setLoading(false);
  }, []);

  return (
    <div className="min-h-screen max-w-5xl mx-auto p-6">
      <h1 className="text-2xl font-semibold text-brand-dark mb-2">
        HITL Queue / Audit
      </h1>
      <p className="text-sm text-slate-500 mb-6">
        Every agent decision is written to the audit log (HIPAA §164.312(b)).
        Phase 2 will surface all rows here with filters by customer,
        conversation, and decision.
      </p>

      {loading ? (
        <p className="text-slate-400">Loading…</p>
      ) : (
        <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-slate-400">
          Audit viewer endpoint ships in Phase 2. (See{" "}
          <code className="rounded bg-slate-100 px-1">/api/v1/audit</code>{" "}
          TODO in <code>app/routes/audit.py</code>.)
        </div>
      )}
    </div>
  );
}
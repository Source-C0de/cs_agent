import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-6 p-12">
      <h1 className="text-4xl font-bold text-brand-dark">Green Lab Support</h1>
      <p className="text-slate-600 max-w-prose text-center">
        Multi-channel, HIPAA-grade customer support AI agent for Green Lab
        (lab/research services). Phase 1 ships the web chat widget.
      </p>
      <div className="flex gap-4">
        <Link
          href="/widget"
          className="rounded-md bg-brand text-white px-4 py-2 hover:bg-brand-dark"
        >
          Open chat widget
        </Link>
        <Link
          href="/admin"
          className="rounded-md border border-brand text-brand-dark px-4 py-2 hover:bg-brand-light/30"
        >
          Admin / HITL queue
        </Link>
      </div>
    </main>
  );
}
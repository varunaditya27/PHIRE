"use client";

import { useState } from "react";
import { CalendarClock, Loader2 } from "lucide-react";
import { api, DocumentRead } from "@/lib/api";

/** Asks the user for the date of a document where none could be found, instead of silently using today. */
export function DateNeededPrompt({ doc, onSaved }: { doc: DocumentRead; onSaved: (doc: DocumentRead) => void }) {
  const [date, setDate] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const today = new Date().toISOString().slice(0, 10);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!date || saving) return;
    setSaving(true);
    setError(null);
    try {
      onSaved(await api.documents.setDate(doc.id, date));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the date.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={save} className="rounded-lg border border-[var(--warning,#C79A2C)] bg-[var(--warning-soft,rgba(199,154,44,0.12))] p-3 space-y-2">
      <p className="flex items-start gap-2 text-xs text-foreground">
        <CalendarClock className="w-4 h-4 mt-0.5 flex-shrink-0" aria-hidden="true" />
        <span>
          We couldn&apos;t find a date in this document, so its readings are shown at the upload date for now. When was it
          issued?
        </span>
      </p>
      <div className="flex items-center gap-2">
        <input
          type="date"
          value={date}
          max={today}
          onChange={(e) => setDate(e.target.value)}
          aria-label={`Date of ${doc.filename}`}
          className="flex-1 rounded-md border border-border bg-background px-2 py-1.5 text-sm text-foreground"
        />
        <button
          type="submit"
          disabled={!date || saving}
          className="rounded-md bg-primary text-primary-foreground px-3 py-1.5 text-sm font-medium disabled:opacity-40 flex items-center gap-1.5 cursor-pointer"
        >
          {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          Save date
        </button>
      </div>
      {error && <p className="text-xs text-[var(--danger)]">{error}</p>}
    </form>
  );
}

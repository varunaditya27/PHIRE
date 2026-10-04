"use client";

import { useState } from "react";
import { api, EvidenceCitation, Claim } from "@/lib/api";
import { Search, FileSearch, CheckCircle2, AlertTriangle, HelpCircle, Sparkles, BookOpen, Layers, Loader2, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

export default function SearchPage() {
  const [activeTab, setActiveTab] = useState<"search" | "verify">("search");
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [citations, setCitations] = useState<EvidenceCitation[]>([]);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Claim verification state
  const [claimInput, setClaimInput] = useState("");
  const [verifiedClaim, setVerifiedClaim] = useState<Claim | null>(null);
  const [loadingVerify, setLoadingVerify] = useState(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loadingSearch) return;

    setLoadingSearch(true);
    setSearchError(null);
    try {
      const results = await api.evidence.search(query.trim(), topK);
      setCitations(results);
    } catch (err: any) {
      setSearchError(err.message || "Failed to retrieve evidence citations.");
    } finally {
      setLoadingSearch(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!claimInput.trim() || loadingVerify) return;

    setLoadingVerify(true);
    setVerifyError(null);
    try {
      const res = await api.evidence.verify(claimInput.trim());
      setVerifiedClaim(res.claim);
    } catch (err: any) {
      setVerifyError(err.message || "Failed to verify claim against evidence.");
    } finally {
      setLoadingVerify(false);
    }
  };

  const getStatusBadge = (status: Claim["status"]) => {
    switch (status) {
      case "SUPPORTED":
        return {
          color: "bg-[var(--positive-soft)] text-[var(--positive)] border border-[var(--positive)]",
          icon: CheckCircle2,
          label: "Supported",
        };
      case "DERIVED":
        return {
          color: "bg-[var(--info-soft)] text-[var(--info)] border border-[var(--info)]",
          icon: Sparkles,
          label: "Derived",
        };
      case "CONFLICTING":
      case "UNSUPPORTED":
        return {
          color: "bg-[var(--danger-soft)] text-[var(--danger)] border border-[var(--danger)]",
          icon: AlertTriangle,
          label: status,
        };
      default:
        return {
          color: "bg-muted text-muted-foreground border border-border",
          icon: HelpCircle,
          label: status,
        };
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-medium tracking-tight text-foreground font-[family-name:var(--font-editorial)]">Evidence & Claim Explorer</h1>
        <p className="text-muted-foreground mt-1">
          Perform direct hybrid (BM25 + semantic) evidence retrieval and test NLI claim verification directly.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border space-x-6">
        <button
          onClick={() => setActiveTab("search")}
          className={cn(
            "pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-all cursor-pointer",
            activeTab === "search"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          <Search className="w-4 h-4" />
          Hybrid Evidence Search
        </button>
        <button
          onClick={() => setActiveTab("verify")}
          className={cn(
            "pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-all cursor-pointer",
            activeTab === "verify"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          <FileSearch className="w-4 h-4" />
          Claim Verifier
        </button>
      </div>

      {/* Tab 1: Search */}
      {activeTab === "search" && (
        <div className="space-y-6">
          <form onSubmit={handleSearch} className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-3.5 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search clinical records and references (e.g. 'HbA1c normal range' or 'Lisinopril dosage')..."
                className="w-full rounded-xl border border-border bg-card pl-10 pr-4 py-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 transition-all placeholder:text-muted-foreground"
              />
            </div>
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="rounded-xl border border-border bg-card px-3 py-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 cursor-pointer"
            >
              <option value={3}>Top 3</option>
              <option value={5}>Top 5</option>
              <option value={10}>Top 10</option>
            </select>
            <button
              type="submit"
              disabled={loadingSearch || !query.trim()}
              className="rounded-xl bg-primary text-primary-foreground px-6 py-3 text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 cursor-pointer shadow-sm"
            >
              {loadingSearch ? <Loader2 className="w-4 h-4 animate-spin" /> : "Search"}
            </button>
          </form>

          {searchError && (
            <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 text-sm">
              {searchError}
            </div>
          )}

          {/* Results */}
          <div className="space-y-4">
            {citations.length > 0 ? (
              citations.map((cite, i) => (
                <div
                  key={cite.evidence_passage_id || i}
                  className="p-5 rounded-xl bg-card border border-border space-y-3 shadow-sm hover:border-primary/40 transition-colors"
                >
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold px-2 py-0.5 rounded bg-secondary text-secondary-foreground">
                        {cite.source_filename || "Knowledge Base"}
                      </span>
                      {cite.page_number && <span>Page {cite.page_number}</span>}
                    </div>
                    <span className="font-mono text-[var(--evidence)] font-medium">
                      Match score: {(cite.score * 100).toFixed(1)}%
                    </span>
                  </div>

                  <p className="text-sm text-foreground/90 leading-relaxed font-mono bg-muted/30 p-3.5 rounded-lg border border-border/50">
                    "{cite.text}"
                  </p>

                  <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1">
                    <span>ID: {cite.evidence_passage_id}</span>
                    <span>Authority: {cite.authority}</span>
                  </div>
                </div>
              ))
            ) : (
              !loadingSearch && (
                <div className="p-8 text-center border border-border rounded-xl bg-card text-muted-foreground text-sm">
                  Enter a query above to retrieve matching evidence chunks from indexed documents.
                </div>
              )
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Verify Claim */}
      {activeTab === "verify" && (
        <div className="space-y-6">
          <form onSubmit={handleVerify} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Atomic Claim Statement
              </label>
              <textarea
                value={claimInput}
                onChange={(e) => setClaimInput(e.target.value)}
                rows={3}
                placeholder="e.g. 'Patient's fasting blood glucose was 110 mg/dL on the last visit.'"
                className="w-full rounded-xl border border-border bg-card px-4 py-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 transition-all placeholder:text-muted-foreground"
              />
            </div>
            <button
              type="submit"
              disabled={loadingVerify || !claimInput.trim()}
              className="rounded-xl bg-primary text-primary-foreground px-6 py-2.5 text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 cursor-pointer shadow-sm"
            >
              {loadingVerify ? <Loader2 className="w-4 h-4 animate-spin" /> : "Verify Claim"}
            </button>
          </form>

          {verifyError && (
            <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 text-sm">
              {verifyError}
            </div>
          )}

          {verifiedClaim && (
            <div className="p-6 rounded-2xl bg-card border border-border shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-foreground text-base">Verification Result</h3>
                {(() => {
                  const badge = getStatusBadge(verifiedClaim.status);
                  const Icon = badge.icon;
                  return (
                    <span className={cn("inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border", badge.color)}>
                      <Icon className="w-3.5 h-3.5 mr-1.5" />
                      {badge.label}
                    </span>
                  );
                })()}
              </div>

              <div className="p-4 rounded-xl bg-muted/40 border border-border/70 text-sm font-medium text-foreground">
                "{verifiedClaim.statement}"
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs">
                <div className="p-3 rounded-lg bg-secondary/50 border border-border">
                  <span className="text-muted-foreground block mb-1">NLI Confidence Score</span>
                  <span className="font-bold text-lg text-foreground font-[family-name:var(--font-mono)]">
                    {verifiedClaim.confidence !== null ? `${(verifiedClaim.confidence * 100).toFixed(1)}%` : "N/A"}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-secondary/50 border border-border">
                  <span className="text-muted-foreground block mb-1">Evidence Source</span>
                  <span className="font-medium text-foreground truncate block">
                    {verifiedClaim.source_filenames?.join(", ") || verifiedClaim.source_url || "Knowledge graph fact / no direct citation"}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

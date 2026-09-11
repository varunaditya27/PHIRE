"use client";

import { useState, useEffect, useRef } from "react";
import { api, DocumentRead, DocumentUploadResponse } from "@/lib/api";
import { UploadCloud, FileText, CheckCircle2, Clock, AlertCircle, RefreshCw, Loader2, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import Link from "next/link";

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentRead[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reportDate, setReportDate] = useState(todayISO());
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load documents from localStorage cache if any (since there's no list documents endpoint).
  // The cache is keyed by document id, which no longer resolves after a
  // backend/DB reset -- reconcile against the backend once on mount and
  // drop any card whose document is gone, instead of leaving stale cards
  // around until someone manually clears localStorage.
  useEffect(() => {
    const saved = localStorage.getItem("phire_documents");
    if (!saved) return;

    let cached: DocumentRead[];
    try {
      cached = JSON.parse(saved);
    } catch (e) {
      console.error("Failed to parse saved docs", e);
      return;
    }
    setDocuments(cached);

    (async () => {
      const results = await Promise.all(
        cached.map(async (doc) => {
          try {
            return await api.documents.get(doc.id);
          } catch {
            return null; // document no longer exists on the backend
          }
        })
      );
      const stillValid = results.filter((d): d is DocumentRead => d !== null);
      if (stillValid.length !== cached.length) {
        saveDocuments(stillValid);
      }
    })();
  }, []);

  const saveDocuments = (docs: DocumentRead[]) => {
    setDocuments(docs);
    localStorage.setItem("phire_documents", JSON.stringify(docs));
  };

  // Polling for active processing documents
  useEffect(() => {
    const activeDocs = documents.filter(
      (d) => d.status === "uploaded" || d.status === "processing"
    );

    if (activeDocs.length === 0) return;

    const interval = setInterval(async () => {
      let updated = false;
      const newDocs = await Promise.all(
        documents.map(async (doc) => {
          if (doc.status === "uploaded" || doc.status === "processing") {
            try {
              const fresh = await api.documents.get(doc.id);
              if (fresh.status !== doc.status) {
                updated = true;
                return fresh;
              }
            } catch (err) {
              console.error(`Failed to poll status for doc ${doc.id}:`, err);
            }
          }
          return doc;
        })
      );

      if (updated) {
        saveDocuments(newDocs);
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [documents]);

  const handleFileUpload = async (file: File) => {
    if (!file) return;

    // Check allowed types: pdf, png, jpeg
    const allowed = ["application/pdf", "image/png", "image/jpeg", "image/jpg"];
    if (!allowed.includes(file.type)) {
      setErrorMessage("Unsupported file type. Please upload a PDF, PNG, or JPEG.");
      return;
    }

    setUploading(true);
    setErrorMessage(null);

    try {
      const res: DocumentUploadResponse = await api.documents.upload(file, reportDate);
      const newDoc: DocumentRead = {
        id: res.id,
        filename: res.filename,
        content_type: file.type,
        status: "uploaded",
        report_date: res.report_date,
        uploaded_at: new Date().toISOString(),
        processed_at: null,
        error_message: null,
      };

      const nextDocs = [newDoc, ...documents];
      saveDocuments(nextDocs);

      // Trigger processing
      try {
        await api.documents.process(res.id);
      } catch (err) {
        console.log("Processing triggered or already queued:", err);
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to upload document.");
    } finally {
      setUploading(false);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const getStatusDisplay = (status: DocumentRead["status"]) => {
    switch (status) {
      case "processed":
        return {
          color: "bg-[var(--positive-soft)] text-[var(--positive)] border border-[var(--positive)]",
          icon: CheckCircle2,
          label: "Processed",
        };
      case "processing":
        return {
          color: "bg-[var(--info-soft)] text-[var(--info)] border border-[var(--info)] animate-pulse",
          icon: Loader2,
          label: "Ingesting & Extracting",
        };
      case "failed":
        return {
          color: "bg-[var(--danger-soft)] text-[var(--danger)] border border-[var(--danger)]",
          icon: AlertCircle,
          label: "Failed",
        };
      default:
        return {
          color: "bg-muted text-muted-foreground border border-border",
          icon: Clock,
          label: "Uploaded",
        };
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl tracking-tight text-foreground font-[family-name:var(--font-editorial)] font-medium">Document Ingestion</h1>
        <p className="text-muted-foreground mt-1">
          Upload medical lab reports, discharge summaries, or clinical records to automatically extract observations and generate your health graph.
        </p>
      </div>

      {errorMessage && (
        <div className="p-4 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 flex items-start text-rose-700 dark:text-rose-300 text-sm">
          <AlertCircle className="h-5 w-5 mr-3 flex-shrink-0 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Report Date Selector */}
      <div className="flex items-center gap-3 p-4 rounded-xl bg-card border border-border">
        <label htmlFor="report-date" className="text-sm font-medium text-foreground whitespace-nowrap">
          Report date
        </label>
        <input
          id="report-date"
          type="date"
          value={reportDate}
          max={todayISO()}
          onChange={(e) => setReportDate(e.target.value || todayISO())}
          className="px-3 py-1.5 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
        />
        <span className="text-xs text-muted-foreground">
          The clinical date this report is from. Defaults to today if left unchanged — used as the reference date for every fact extracted from it.
        </span>
      </div>

      {/* Upload Drop Zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          "border-2 border-dashed rounded-2xl p-10 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-200",
          dragActive
            ? "border-primary bg-primary/5 scale-[1.01]"
            : "border-border bg-card hover:border-primary/50 hover:bg-muted/30"
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              handleFileUpload(e.target.files[0]);
            }
          }}
          className="hidden"
        />

        <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center text-primary mb-4">
          {uploading ? (
            <Loader2 className="w-8 h-8 animate-spin" />
          ) : (
            <UploadCloud className="w-8 h-8" />
          )}
        </div>

        <h3 className="text-lg font-semibold text-foreground">
          {uploading ? "Uploading & Ingesting..." : "Click to upload or drag & drop"}
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          PDF, PNG, or JPEG lab reports (up to 25MB)
        </p>
      </div>

      {/* Uploaded Documents List */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-foreground flex items-center">
          <FileText className="w-5 h-5 mr-2 text-foreground" />
          Uploaded Records ({documents.length})
        </h2>

        {documents.length === 0 ? (
          <div className="p-8 text-center border border-border rounded-xl bg-card text-muted-foreground text-sm">
            No medical documents uploaded yet. Upload a lab report or clinical summary above to build your health timeline.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {documents.map((doc) => {
              const statusDisplay = getStatusDisplay(doc.status);
              const Icon = statusDisplay.icon;
              return (
                <div
                  key={doc.id}
                  className="p-5 rounded-xl bg-card border border-border shadow-sm flex flex-col justify-between space-y-4 hover:border-primary/40 transition-colors"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div className="p-2.5 rounded-lg bg-secondary text-secondary-foreground mt-0.5">
                        <FileText className="w-5 h-5" />
                      </div>
                      <div>
                        <h4 className="font-semibold text-foreground text-sm truncate max-w-[220px]">
                          {doc.filename}
                        </h4>
                        <span className="text-xs text-muted-foreground block">
                          Report date:{" "}
                          {new Date(doc.report_date).toLocaleDateString(undefined, {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                          })}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          Uploaded{" "}
                          {new Date(doc.uploaded_at).toLocaleDateString(undefined, {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                    </div>

                    <span
                      className={cn(
                        "inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border",
                        statusDisplay.color
                      )}
                    >
                      <Icon className={cn("w-3.5 h-3.5 mr-1.5", doc.status === "processing" && "animate-spin")} />
                      {statusDisplay.label}
                    </span>
                  </div>

                  {doc.error_message && (
                    <div className="text-xs text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/30 p-2.5 rounded-lg border border-rose-200 dark:border-rose-900">
                      {doc.error_message}
                    </div>
                  )}

                  {doc.status === "processed" && (
                    <div className="flex items-center justify-between pt-2 border-t border-border text-xs text-muted-foreground">
                      <span>Indexed into Graph & Vectors</span>
                      <Link
                        href="/"
                        className="text-primary hover:underline flex items-center font-medium"
                      >
                        View in Timeline <ArrowRight className="w-3.5 h-3.5 ml-1" />
                      </Link>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

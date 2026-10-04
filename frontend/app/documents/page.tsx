"use client";

import { useState, useEffect, useRef } from "react";
import { api, DocumentRead, DocumentUploadResponse, ProgressEvent } from "@/lib/api";
import { ProgressSteps } from "@/components/progress-steps";
import { UploadCloud, FileText, CheckCircle2, Clock, AlertCircle, RefreshCw, Loader2, ArrowRight, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import Link from "next/link";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentRead[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // The backend is the source of truth, so the list survives reloads and other devices.
  useEffect(() => {
    api.documents
      .list()
      .then(setDocuments)
      .catch((err) => setErrorMessage(err instanceof Error ? err.message : "Failed to load documents."));
  }, []);

  const [progress, setProgress] = useState<Record<string, ProgressEvent[]>>({});
  const watching = useRef<Set<string>>(new Set());

  // Follow a document's ingestion over SSE; when the stream ends, re-read its final row.
  const watchDocument = (id: string) => {
    if (watching.current.has(id)) return;
    watching.current.add(id);
    api.documents
      .watch(id, (e) => setProgress((prev) => ({ ...prev, [id]: [...(prev[id] ?? []), e] })))
      .catch((err) => console.error(`Progress stream failed for ${id}:`, err))
      .finally(async () => {
        watching.current.delete(id);
        try {
          const fresh = await api.documents.get(id);
          setDocuments((prev) => prev.map((d) => (d.id === id ? fresh : d)));
        } catch (err) {
          console.error(`Failed to refresh doc ${id}:`, err);
        }
      });
  };

  // Resume watching documents that were still in flight when the page was opened.
  useEffect(() => {
    documents
      .filter((d) => d.status === "uploaded" || d.status === "processing")
      .forEach((d) => watchDocument(d.id));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documents.length]);

  // Removes the document server-side (vectors, graph facts, file), then from the local list.
  const handleDelete = async (doc: DocumentRead) => {
    if (!window.confirm(`Delete "${doc.filename}" and all data extracted from it?`)) return;
    setErrorMessage(null);
    try {
      await api.documents.remove(doc.id);
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to delete document.");
    }
  };

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
      const res: DocumentUploadResponse = await api.documents.upload(file);
      const newDoc: DocumentRead = {
        id: res.id,
        filename: res.filename,
        content_type: file.type,
        status: "uploaded",
        uploaded_at: new Date().toISOString(),
        processed_at: null,
        error_message: null,
      };

      setDocuments((prev) => [newDoc, ...prev]);

      // Upload already queues processing server-side; just follow it.
      watchDocument(res.id);
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
                        <span className="text-xs text-muted-foreground">
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

                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          "inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border",
                          statusDisplay.color
                        )}
                      >
                        <Icon className={cn("w-3.5 h-3.5 mr-1.5", doc.status === "processing" && "animate-spin")} />
                        {statusDisplay.label}
                      </span>
                      {doc.status !== "processing" && (
                        <button
                          type="button"
                          onClick={() => handleDelete(doc)}
                          aria-label={`Delete ${doc.filename}`}
                          className="p-1.5 rounded-md text-muted-foreground hover:text-[var(--danger)] hover:bg-[var(--danger-soft)] transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>

                  {doc.error_message && (
                    <div className="text-xs text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/30 p-2.5 rounded-lg border border-rose-200 dark:border-rose-900">
                      {doc.error_message}
                    </div>
                  )}

                  {(doc.status === "uploaded" || doc.status === "processing") && (progress[doc.id]?.length ?? 0) > 0 && (
                    <div className="pt-2 border-t border-border">
                      <ProgressSteps steps={progress[doc.id]} />
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

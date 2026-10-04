// Types matching the backend Pydantic models

import { readSSE } from "@/lib/sse";

export interface HealthStatus {
  status: "ok" | "degraded";
  database: boolean;
  ollama: boolean;
  vector_store: boolean;
  graph: boolean;
  detail: Record<string, string>;
}

export interface Claim {
  id: string | null;
  statement: string;
  status: "SUPPORTED" | "DERIVED" | "INFERRED" | "UNCERTAIN" | "CONFLICTING" | "UNSUPPORTED";
  confidence: number | null;
  source_url: string | null;
  source_filename: string | null;
  /** Every uploaded document the claim rests on; a trend spans the documents of both readings. */
  source_filenames: string[];
  source_span: [number, number] | null;
}

export interface ChatResponse {
  id: string;
  answer: string;
  claims: Claim[];
  citations: any[];
  created_at: string;
}

export interface ChatMessageRead {
  id: string;
  role: "user" | "assistant";
  content: string;
  claims: Claim[] | null;
  created_at: string;
}

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  status: string;
}

export interface DocumentRead {
  id: string;
  filename: string;
  content_type: string;
  status: "uploaded" | "processing" | "processed" | "failed";
  uploaded_at: string;
  processed_at: string | null;
  error_message: string | null;
}

export interface ObservationRead {
  id: string;
  document_id: string | null;
  type: "lab" | "medication" | "condition" | "symptom" | "vital";
  name: string;
  value: string;
  value_numeric: number | null;
  unit: string | null;
  reference_range: string | null;
  interpretation: string | null;
  status: string | null;
  observed_date: string;
}

export interface TimelinePoint {
  observed_date: string;
  value_numeric: number | null;
  value: string;
  unit: string | null;
  observation_id: string;
}

export interface TimelineSeries {
  name: string;
  type: string;
  points: TimelinePoint[];
}

export interface TimelineResponse {
  series: TimelineSeries[];
  generated_at: string;
}

export interface EvidenceCitation {
  evidence_passage_id: string;
  document_id: string | null;
  text: string;
  source_url: string | null;
  source_filename: string | null;
  authority: number;
  page_number: number | null;
  score: number;
}

/** One backend stage update from an SSE progress stream. */
export interface ProgressEvent {
  stage: string;
  message: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Custom fetch wrapper
async function fetchAPI<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const headers = {
    ...(!(options.body instanceof FormData) && { "Content-Type": "application/json" }),
    ...options.headers,
  };

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    let errorDetail = "API Error";
    try {
      const errorData = await response.json();
      errorDetail = JSON.stringify(errorData.detail) || errorDetail;
    } catch {
      errorDetail = response.statusText;
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  health: {
    check: () => fetchAPI<HealthStatus>("/api/health", { method: "POST" }),
    ping: () => fetchAPI<{ status: string }>("/api/ping"),
  },
  chat: {
    send: (message: string) => fetchAPI<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
    /** Persisted conversation, oldest first, to rebuild the chat after a reload. */
    history: () => fetchAPI<ChatMessageRead[]>("/api/chat/messages"),
    /** Same turn as send(), reporting each pipeline stage while it runs. */
    stream: async (message: string, onProgress: (e: ProgressEvent) => void): Promise<ChatResponse> => {
      let result: ChatResponse | null = null;
      let failure: string | null = null;
      await readSSE(
        `${API_BASE_URL}/api/chat/stream`,
        { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message }) },
        (f) => {
          if (f.event === "progress") onProgress(f.data as ProgressEvent);
          else if (f.event === "result") result = f.data as ChatResponse;
          else if (f.event === "error") failure = (f.data as { message: string }).message;
        }
      );
      if (failure) throw new Error(failure);
      if (!result) throw new Error("Connection closed before an answer arrived.");
      return result;
    },
  },
  documents: {
    /** Stream ingestion stages; resolves when the server finishes (processed or failed). */
    watch: (id: string, onProgress: (e: ProgressEvent) => void, signal?: AbortSignal) =>
      readSSE(`${API_BASE_URL}/api/documents/${id}/events`, { signal }, (f) => {
        if (f.event === "progress") onProgress(f.data as ProgressEvent);
      }),
    upload: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      // Let browser set the correct content-type for FormData including boundary
      const headers = new Headers();
      // Remove content-type so browser sets it
      return fetchAPI<DocumentUploadResponse>("/api/documents/upload", {
        method: "POST",
        body: formData,
        headers: {}, // fetchAPI won't override it because it's FormData
      });
    },
    list: () => fetchAPI<DocumentRead[]>("/api/documents"),
    get: (id: string) => fetchAPI<DocumentRead>(`/api/documents/${id}`),
    /** Delete a document and everything derived from it (vectors, graph facts, file). */
    remove: async (id: string) => {
      const response = await fetch(`${API_BASE_URL}/api/documents/${id}`, { method: "DELETE" });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `Delete failed (${response.status})`);
      }
    },
    process: (id: string) => fetchAPI(`/api/documents/${id}/process`, { method: "POST" }),
  },
  observations: {
    list: (params?: { type?: string; start_date?: string; end_date?: string }) => {
      const query = new URLSearchParams(params as Record<string, string>).toString();
      return fetchAPI<ObservationRead[]>(`/api/observations${query ? `?${query}` : ""}`);
    },
  },
  timeline: {
    get: () => fetchAPI<TimelineResponse>("/api/timeline"),
  },
  evidence: {
    search: (query: string, top_k: number = 5) => {
      const q = new URLSearchParams({ query, top_k: top_k.toString() }).toString();
      return fetchAPI<EvidenceCitation[]>(`/api/search/evidence?${q}`);
    },
    verify: (claim: string) => fetchAPI<{ claim: Claim }>("/api/evidence/verify", {
      method: "POST",
      body: JSON.stringify({ claim }),
    }),
  },
  claims: {
    extract: (text: string) => fetchAPI<{ claims: Claim[] }>("/api/claims/extract", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  },
};

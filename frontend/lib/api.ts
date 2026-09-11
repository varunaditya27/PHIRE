// Types matching the backend Pydantic models

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
  source_span: string | null;
}

export interface ChatResponse {
  id: string;
  answer: string;
  claims: Claim[];
  citations: any[];
  created_at: string;
}

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  status: string;
  report_date: string;
}

export interface DocumentRead {
  id: string;
  filename: string;
  content_type: string;
  status: "uploaded" | "processing" | "processed" | "failed";
  report_date: string;
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
  },
  documents: {
    upload: async (file: File, reportDate?: string) => {
      const formData = new FormData();
      formData.append("file", file);
      // Omitted -> backend defaults to today's date.
      if (reportDate) formData.append("report_date", reportDate);
      // Let browser set the correct content-type for FormData including boundary
      return fetchAPI<DocumentUploadResponse>("/api/documents/upload", {
        method: "POST",
        body: formData,
        headers: {}, // fetchAPI won't override it because it's FormData
      });
    },
    get: (id: string) => fetchAPI<DocumentRead>(`/api/documents/${id}`),
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

"use client";

import { useState, useRef, useEffect } from "react";
import { api, ChatResponse, Claim, ProgressEvent } from "@/lib/api";
import { ProgressSteps } from "@/components/progress-steps";
import { Send, Bot, User, ShieldCheck, AlertTriangle, HelpCircle, CheckCircle2, ChevronDown, ChevronRight, FileCheck, Sparkles, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  claims?: Claim[];
  createdAt: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Hello! I am PHIRE, your evidence-attributed medical assistant. Ask me questions about your health records, lab results, or medical history.",
      createdAt: new Date().toISOString(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [steps, setSteps] = useState<ProgressEvent[]>([]);
  const [expandedClaims, setExpandedClaims] = useState<Record<string, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, steps]);

  const toggleClaimExpansion = (msgId: string) => {
    setExpandedClaims((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      createdAt: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setSteps([]);
    setLoading(true);

    try {
      const response: ChatResponse = await api.chat.stream(userMessage.content, (e) => setSteps((prev) => [...prev, e]));
      const assistantMessage: Message = {
        id: response.id || Date.now().toString(),
        role: "assistant",
        content: response.answer,
        claims: response.claims,
        createdAt: response.created_at || new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
      // Auto-expand claims audit for new message if claims exist
      if (response.claims && response.claims.length > 0) {
        setExpandedClaims((prev) => ({ ...prev, [assistantMessage.id]: true }));
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: "assistant",
          content: `Error: ${err.message || "Failed to reach PHIRE backend."}`,
          createdAt: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
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
          label: "Graph Derived",
        };
      case "INFERRED":
        return {
          color: "bg-[var(--info-soft)] text-[var(--info)] border border-[var(--info)]",
          icon: HelpCircle,
          label: "Inferred",
        };
      case "CONFLICTING":
      case "UNSUPPORTED":
        return {
          color: "bg-[var(--danger-soft)] text-[var(--danger)] border border-[var(--danger)]",
          icon: AlertTriangle,
          label: status === "CONFLICTING" ? "Conflicting" : "Unsupported",
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
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="border-b border-border px-8 py-4 bg-card">
        <h1 className="text-xl font-medium tracking-tight text-foreground flex items-center font-[family-name:var(--font-editorial)]">
          <ShieldCheck className="w-5 h-5 mr-2 text-[var(--evidence)]" />
          Evidence-Attributed Medical Chat
        </h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          Every statement is extracted into atomic claims and cross-verified against your clinical records.
        </p>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 max-w-4xl w-full mx-auto custom-scrollbar">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              "flex gap-4",
              msg.role === "user" ? "justify-end" : "justify-start"
            )}
          >
            {msg.role === "assistant" && (
              <div className="w-9 h-9 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0 text-primary">
                <Bot className="w-5 h-5" />
              </div>
            )}

            <div
              className={cn(
                "rounded-2xl px-5 py-4 max-w-2xl shadow-sm space-y-3",
                msg.role === "user"
                  ? "bg-primary text-primary-foreground rounded-br-none"
                  : "bg-card border border-border text-foreground rounded-bl-none"
              )}
            >
              <div className="whitespace-pre-wrap leading-relaxed text-sm">
                {msg.content}
              </div>

              {/* Claims / Evidence Audit Trail */}
              {msg.role === "assistant" && msg.claims && msg.claims.length > 0 && (
                <div className="pt-3 border-t border-border/80 text-xs">
                  <button
                    onClick={() => toggleClaimExpansion(msg.id)}
                    className="flex items-center font-semibold text-[var(--evidence)] hover:text-[var(--evidence-hover)] transition-colors cursor-pointer py-1"
                  >
                    {expandedClaims[msg.id] ? (
                      <ChevronDown className="w-3.5 h-3.5 mr-1.5" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5 mr-1.5" />
                    )}
                    <span>
                      Claim Verification Audit ({msg.claims.length} {msg.claims.length === 1 ? "claim" : "claims"})
                    </span>
                  </button>

                  {expandedClaims[msg.id] && (
                    <div className="mt-2 space-y-2.5">
                      {msg.claims.map((claim, idx) => {
                        const badge = getStatusBadge(claim.status);
                        const Icon = badge.icon;
                        return (
                          <div
                            key={idx}
                            className="p-3 rounded-lg bg-muted/40 border border-border/60 space-y-1.5"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border", badge.color)}>
                                <Icon className="w-3 h-3 mr-1" />
                                {badge.label}
                              </span>
                              {claim.confidence !== null && (
                                <span className="text-[11px] text-muted-foreground font-mono">
                                  {(claim.confidence * 100).toFixed(0)}% confidence
                                </span>
                              )}
                            </div>

                            <p className="text-foreground/90 font-medium text-[13px]">
                              "{claim.statement}"
                            </p>

                            {(claim.source_filename || claim.source_span) && (
                              <div className="flex items-center text-[11px] text-[var(--evidence)] gap-1.5 pt-1">
                                <FileCheck className="w-3.5 h-3.5 flex-shrink-0" />
                                <span className="truncate font-[family-name:var(--font-mono)]">
                                  {claim.source_filename || "Clinical graph fact"}
                                  {claim.source_span ? ` (${claim.source_span})` : ""}
                                </span>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>

            {msg.role === "user" && (
              <div className="w-9 h-9 rounded-full bg-secondary border border-border flex items-center justify-center flex-shrink-0 text-secondary-foreground">
                <User className="w-5 h-5" />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-4 justify-start items-center">
            <div className="w-9 h-9 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0 text-primary">
              <Bot className="w-5 h-5" />
            </div>
            <div className="bg-card border border-border rounded-2xl rounded-bl-none px-5 py-4 text-muted-foreground text-sm">
              {steps.length > 0 ? (
                <ProgressSteps steps={steps} />
              ) : (
                <span className="flex items-center gap-3">
                  <Loader2 className="w-4 h-4 animate-spin text-primary" />
                  Connecting to PHIRE...
                </span>
              )}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <div className="p-4 border-t border-border bg-card">
        <form
          onSubmit={handleSend}
          className="max-w-4xl mx-auto flex items-center gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about medications, lab results, conditions..."
            disabled={loading}
            className="flex-1 rounded-xl border border-border bg-background px-4 py-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 transition-all placeholder:text-muted-foreground"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-xl bg-primary text-primary-foreground p-3 hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center cursor-pointer shadow-sm"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  );
}

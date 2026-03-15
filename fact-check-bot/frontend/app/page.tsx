"use client";

import { useState, useRef, useEffect } from "react";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://127.0.0.1:8000/ws";

type Source = {
  title: string;
  url: string;
  snippet: string;
};

type CheckResult = {
  original_post: string;
  is_claim: boolean;
  extracted_claim: string | null;
  verdict: "TRUE" | "FALSE" | "UNVERIFIABLE" | "NOT_A_CLAIM";
  response: string;
  sources: Source[];
  confidence: number;
  latency_ms: number;
  bart_label: string | null;
  bart_score: number | null;
  detection_method: string | null;
  from_cache?: boolean;
};

type ProgressStep = {
  stage: string;
  message: string;
  done: boolean;
};

type Message = {
  id: string;
  role: "user" | "bot";
  text?: string;
  result?: CheckResult;
  steps?: ProgressStep[];
  isThinking?: boolean;
};

const STAGE_ICONS: Record<string, string> = {
  received: "📥",
  normalizing: "🧹",
  classifying: "🧠",
  extracting: "🔎",
  retrieving: "🌐",
  generating: "✍️",
  complete: "✅",
  error: "❌",
};

const VERDICT_CONFIG = {
  TRUE: {
    border: "border-l-green-500",
    badge: "bg-green-500/20 text-green-400 ring-1 ring-green-500/30",
    icon: "✅",
    label: "TRUE",
  },
  FALSE: {
    border: "border-l-red-500",
    badge: "bg-red-500/20 text-red-400 ring-1 ring-red-500/30",
    icon: "❌",
    label: "FALSE",
  },
  UNVERIFIABLE: {
    border: "border-l-amber-500",
    badge: "bg-amber-500/20 text-amber-400 ring-1 ring-amber-500/30",
    icon: "⚠️",
    label: "UNVERIFIABLE",
  },
  NOT_A_CLAIM: {
    border: "border-l-gray-500",
    badge: "bg-gray-500/20 text-gray-400 ring-1 ring-gray-500/30",
    icon: "💬",
    label: "NOT A CLAIM",
  },
};

function ThinkingBubble({ steps }: { steps: ProgressStep[] }) {
  return (
    <div className="flex gap-3 mb-6">
      <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-sm flex-shrink-0 mt-0.5">
        🤖
      </div>
      <div className="bg-gray-900 border border-gray-800 rounded-2xl rounded-tl-none px-5 py-4 max-w-lg">
        {steps.length === 0 ? (
          <div className="flex gap-1.5 items-center py-1">
            <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
            <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
            <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
          </div>
        ) : (
          <div className="space-y-0">
            {steps.map((step, i) => (
              <div key={i}>
                {i > 0 && (
                  <div className="ml-[7px] w-px h-3 bg-gradient-to-b from-green-500/40 to-gray-700/40" />
                )}
                <div className="flex items-center gap-3 text-xs">
                  {step.done ? (
                    <span className="w-4 h-4 rounded-full bg-green-500/20 flex items-center justify-center text-green-400 text-[10px] flex-shrink-0">✓</span>
                  ) : (
                    <span className="w-4 h-4 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                      <span className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
                    </span>
                  )}
                  <span className={step.done ? "text-gray-500" : "text-gray-200"}>
                    {step.message}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ResultBubble({ result }: { result: CheckResult }) {
  const config = VERDICT_CONFIG[result.verdict];
  return (
    <div className="flex gap-3 mb-6">
      <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-sm flex-shrink-0 mt-0.5">
        🤖
      </div>
      <div className={`bg-gray-900 border border-gray-800 border-l-4 ${config.border} rounded-xl px-5 py-5 max-w-lg space-y-4`}>
        {/* Verdict */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${config.badge}`}>
            {config.icon} {config.label}
          </span>
          <span className="text-xs text-gray-500">
            {Math.round(result.confidence * 100)}% confident
          </span>
          {result.from_cache && (
            <span className="text-xs text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded-full">⚡ cached</span>
          )}
        </div>

        {/* Response */}
        <p className="text-sm text-white leading-relaxed">{result.response}</p>

        {/* Extracted Claim */}
        {result.extracted_claim && (
          <div className="bg-gray-800/60 rounded-lg px-4 py-3 border border-gray-700/50">
            <p className="text-[10px] text-gray-500 uppercase font-semibold tracking-wider mb-1">Extracted Claim</p>
            <p className="text-sm text-gray-300">{result.extracted_claim}</p>
          </div>
        )}

        {/* Sources */}
        {result.sources.length > 0 && (
          <div className="space-y-2">
            <p className="text-[10px] text-gray-500 uppercase font-semibold tracking-wider">Sources</p>
            {result.sources.map((src, i) => (
              <a
                key={i}
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex gap-3 items-start bg-gray-800/40 hover:bg-gray-800/70 border border-gray-700/40 hover:border-gray-600/60 rounded-lg px-4 py-3 transition-all group"
              >
                <span className="text-xs text-gray-600 font-mono mt-0.5 flex-shrink-0">{i + 1}</span>
                <div className="min-w-0">
                  <p className="text-xs font-medium text-blue-400 group-hover:text-blue-300 transition-colors truncate">{src.title}</p>
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">{src.snippet}</p>
                </div>
              </a>
            ))}
          </div>
        )}

        {/* Meta */}
        <div className="flex flex-wrap gap-4 text-[11px] text-gray-600 border-t border-gray-800 pt-3">
          <span>⏱ {(result.latency_ms / 1000).toFixed(1)}s</span>
          {result.bart_label && (
            <span>BART: {result.bart_label} ({result.bart_score?.toFixed(2)})</span>
          )}
          {result.detection_method && (
            <span>Method: {result.detection_method}</span>
          )}
        </div>
      </div>
    </div>
  );
}

function UserBubble({ text }: { text: string }) {
  return (
    <div className="flex gap-3 mb-6 justify-end">
      <div className="bg-blue-600 rounded-2xl rounded-tr-none px-4 py-3 max-w-lg">
        <p className="text-sm text-white">{text}</p>
      </div>
      <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-sm flex-shrink-0 mt-0.5">
        👤
      </div>
    </div>
  );
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const [processing, setProcessing] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const thinkingIdRef = useRef<string | null>(null);

  useEffect(() => {
    connectWebSocket();
    return () => {
      wsRef.current?.close();
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function connectWebSocket() {
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onclose = () => {
      setConnected(false);
      setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = () => {
      setConnected(false);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.stage === "complete") {
        const thinkingId = thinkingIdRef.current;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === thinkingId
              ? { ...m, isThinking: false, result: data.result }
              : m
          )
        );
        setProcessing(false);
        thinkingIdRef.current = null;
      } else if (data.stage === "error") {
        const thinkingId = thinkingIdRef.current;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === thinkingId
              ? {
                  ...m,
                  isThinking: false,
                  result: {
                    original_post: "",
                    is_claim: false,
                    extracted_claim: null,
                    verdict: "NOT_A_CLAIM" as const,
                    response: `Error: ${data.message}`,
                    sources: [],
                    confidence: 0,
                    latency_ms: 0,
                    bart_label: null,
                    bart_score: null,
                    detection_method: null,
                  },
                }
              : m
          )
        );
        setProcessing(false);
        thinkingIdRef.current = null;
      } else {
        const thinkingId = thinkingIdRef.current;
        setMessages((prev) =>
          prev.map((m) => {
            if (m.id !== thinkingId) return m;
            const existingSteps = m.steps || [];
            const updatedSteps = existingSteps.map((s) => ({ ...s, done: true }));
            updatedSteps.push({
              stage: data.stage,
              message: data.message,
              done: false,
            });
            return { ...m, steps: updatedSteps };
          })
        );
      }
    };

    wsRef.current = ws;
  }

  const handleSend = () => {
    if (!input.trim() || !connected || processing) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      text: input.trim(),
    };

    const thinkingId = crypto.randomUUID();
    thinkingIdRef.current = thinkingId;

    const thinkingMsg: Message = {
      id: thinkingId,
      role: "bot",
      isThinking: true,
      steps: [],
    };

    setMessages((prev) => [...prev, userMsg, thinkingMsg]);
    setProcessing(true);

    wsRef.current?.send(JSON.stringify({ post: input.trim() }));
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <main className="h-screen flex flex-col bg-gray-950 text-white">
      {/* Header */}
      <div className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-xl">🔍</span>
          <div>
            <h1 className="text-sm font-bold text-white">Fact-Check Bot</h1>
            <p className="text-xs text-gray-400">AI-powered claim verification</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-400 animate-pulse" : "bg-red-500"}`} />
          <span className="text-xs text-gray-400">{connected ? "Connected" : "Reconnecting..."}</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-8">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
            <span className="text-5xl">🔍</span>
            <h2 className="text-lg font-semibold text-gray-300">
              Paste any social media post
            </h2>
            <p className="text-sm text-gray-500 max-w-sm">
              I will tell you if the claim is TRUE, FALSE, or UNVERIFIABLE — with sources.
            </p>
            <div className="grid grid-cols-1 gap-2 mt-4 w-full max-w-sm">
              {[
                "Einstein failed math in school",
                "The Great Wall of China is visible from space",
                "Elon Musk bought Twitter for $44 billion",
              ].map((example) => (
                <button
                  key={example}
                  onClick={() => setInput(example)}
                  className="text-xs text-left bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg px-3 py-2 text-gray-300 transition-colors"
                >
                  &quot;{example}&quot;
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => {
          if (msg.role === "user") {
            return <UserBubble key={msg.id} text={msg.text || ""} />;
          }
          if (msg.isThinking || (!msg.result && !msg.isThinking)) {
            return <ThinkingBubble key={msg.id} steps={msg.steps || []} />;
          }
          if (msg.result) {
            return <ResultBubble key={msg.id} result={msg.result} />;
          }
          return null;
        })}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-800 px-6 py-4 flex-shrink-0 bg-gray-900">
        <div className="flex gap-3 max-w-3xl mx-auto">
          <textarea
            className="flex-1 bg-gray-800 text-white rounded-xl border border-gray-700 px-4 py-3 text-sm resize-none focus:outline-none focus:border-blue-500 transition-colors"
            rows={1}
            placeholder="Paste a social media post to fact-check..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || !connected || processing}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold px-5 rounded-xl transition-colors text-sm flex-shrink-0"
          >
            {processing ? "..." : "Send"}
          </button>
        </div>
        <p className="text-xs text-gray-600 text-center mt-2">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </main>
  );
}

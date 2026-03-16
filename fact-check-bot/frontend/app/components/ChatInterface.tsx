"use client";

import { useState, useRef, useEffect } from "react";
import { UserBubble } from "./UserBubble";
import { ResultBubble } from "./ResultBubble";
import { ThinkingBubble } from "./ThinkingBubble";

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

export function ChatInterface() {
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
    <main className="h-screen flex flex-col bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950 text-white">
      {/* Header */}
      <div className="bg-gradient-to-r from-gray-900/80 to-gray-800/80 backdrop-blur-md border-b border-gray-800 px-6 py-4 flex items-center justify-between flex-shrink-0 sticky top-0 z-10">
        <div className="flex items-center gap-4">
          <div className="text-3xl">🔍</div>
          <div>
            <h1 className="text-lg font-bold text-white bg-gradient-to-r from-blue-200 to-purple-200 bg-clip-text text-transparent">
              Fact-Check Bot
            </h1>
            <p className="text-xs text-gray-400">Social media claim verification</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              connected
                ? "bg-gradient-to-br from-green-400 to-teal-400 animate-pulse shadow-lg shadow-green-400/50"
                : "bg-red-500 shadow-lg shadow-red-500/50"
            }`}
          />
          <span className="text-xs text-gray-400 font-medium">
            {connected ? "Connected" : "Reconnecting..."}
          </span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-8 scroll-smooth">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-6 animate-fadeIn">
            <div className="text-7xl mb-4">🔍</div>
            <div className="space-y-2 max-w-2xl">
              <h2 className="text-3xl font-bold bg-gradient-to-r from-blue-200 via-purple-200 to-pink-200 bg-clip-text text-transparent">
                Welcome to Fact-Check Bot
              </h2>
              <p className="text-base text-gray-300">
                Paste any social media post to instantly verify claims with AI-powered analysis.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-md mt-6">
              {[
                "Einstein failed math in school",
                "The Great Wall of China is visible from space",
                "Elon Musk bought Twitter for $44 billion",
                "The human brain uses only 10% of its capacity",
              ].map((example) => (
                <button
                  key={example}
                  onClick={() => setInput(example)}
                  className="text-xs text-left bg-gradient-to-br from-gray-800 to-gray-900 hover:from-purple-900/50 hover:to-gray-800 border border-gray-700 hover:border-purple-500/50 rounded-lg px-4 py-3 text-gray-300 transition-all transform hover:scale-105 hover:shadow-lg hover:shadow-purple-500/10"
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
            return (
              <ResultBubble
                key={msg.id}
                result={msg.result}
                isStreaming={msg === messages[messages.length - 2]}
              />
            );
          }
          return null;
        })}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-800 px-6 py-4 flex-shrink-0 bg-gradient-to-t from-gray-900/80 to-gray-900/40 backdrop-blur-md">
        <div className="flex gap-3 max-w-4xl mx-auto">
          <textarea
            className="flex-1 bg-gray-800/80 backdrop-blur text-white rounded-xl border border-gray-700 focus:border-purple-500/50 px-4 py-3 text-sm resize-none focus:outline-none transition-all duration-200 placeholder-gray-500 hover:border-gray-600"
            rows={1}
            placeholder="Paste a social media post to fact-check..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || !connected || processing}
            className="bg-gradient-to-br from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:from-gray-700 disabled:to-gray-700 disabled:text-gray-500 text-white font-bold px-6 rounded-xl transition-all text-sm flex-shrink-0 transform hover:scale-105 active:scale-95 disabled:scale-100 shadow-lg shadow-blue-600/50 hover:shadow-blue-600/70 disabled:shadow-none"
          >
            {processing ? (
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 bg-white rounded-full animate-bounce" />
              </span>
            ) : (
              "Send"
            )}
          </button>
        </div>
        <p className="text-xs text-gray-500 text-center mt-2 font-medium">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </main>
  );
}

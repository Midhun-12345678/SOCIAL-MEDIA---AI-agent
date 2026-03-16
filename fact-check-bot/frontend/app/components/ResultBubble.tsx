"use client";

import { useState, useEffect } from "react";
import { SourceCard } from "./SourceCard";

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

const VERDICT_CONFIG = {
  TRUE: {
    badge: "bg-gradient-to-r from-green-500/20 to-teal-500/20 text-green-400 border border-green-500/30",
    icon: "✅",
    label: "TRUE",
    dot: "bg-green-500",
  },
  FALSE: {
    badge: "bg-gradient-to-r from-red-500/20 to-pink-500/20 text-red-400 border border-red-500/30",
    icon: "❌",
    label: "FALSE",
    dot: "bg-red-500",
  },
  UNVERIFIABLE: {
    badge: "bg-gradient-to-r from-amber-500/20 to-orange-500/20 text-amber-400 border border-amber-500/30",
    icon: "⚠️",
    label: "UNVERIFIABLE",
    dot: "bg-amber-500",
  },
  NOT_A_CLAIM: {
    badge: "bg-gradient-to-r from-gray-500/20 to-slate-500/20 text-gray-400 border border-gray-500/30",
    icon: "💬",
    label: "NOT A CLAIM",
    dot: "bg-gray-500",
  },
};

function StreamingText({ text }: { text: string }) {
  const [displayText, setDisplayText] = useState("");
  const [isStreaming, setIsStreaming] = useState(true);

  useEffect(() => {
    if (!text || displayText.length === text.length) {
      setIsStreaming(false);
      return;
    }

    const timer = setTimeout(() => {
      setDisplayText((prev) => {
        const nextChar = text[prev.length];
        return prev + nextChar;
      });
    }, 15);

    return () => clearTimeout(timer);
  }, [text, displayText]);

  return (
    <span>
      {displayText}
      {isStreaming && <span className="animate-pulse">▌</span>}
    </span>
  );
}

export function ResultBubble({ result, isStreaming }: { result: CheckResult; isStreaming?: boolean }) {
  const config = VERDICT_CONFIG[result.verdict];
  const [sourcesExpanded, setSourcesExpanded] = useState(false);

  return (
    <div className="flex gap-3 mb-6 animate-fadeIn">
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center text-sm flex-shrink-0 mt-0.5 shadow-lg shadow-purple-600/50">
        🤖
      </div>
      <div className="bg-gradient-to-br from-gray-800 to-gray-900 border border-gray-700 rounded-3xl rounded-tl-none px-5 py-5 max-w-2xl space-y-4 shadow-lg shadow-purple-600/10">
        {/* Verdict - Inline and compact */}
        <div className="flex items-center gap-3 flex-wrap">
          <span className={`text-xs font-bold px-3 py-1.5 rounded-full ${config.badge} transition-all`}>
            <span className={`${config.dot} w-1.5 h-1.5 rounded-full inline-block mr-1.5 align-middle animate-pulse`} />
            {config.icon} {config.label}
          </span>
          <span className="text-xs text-gray-400">{Math.round(result.confidence * 100)}% confidence</span>
          {result.from_cache && (
            <span className="text-xs text-cyan-400 bg-cyan-400/10 px-2.5 py-1 rounded-full font-semibold">⚡ cached</span>
          )}
        </div>

        {/* Response with streaming text */}
        <div className="space-y-2">
          <p className="text-sm text-white leading-relaxed font-light">
            {isStreaming ? (
              <StreamingText text={result.response} />
            ) : (
              result.response
            )}
          </p>
        </div>

        {/* Extracted Claim - Subtle */}
        {result.extracted_claim && (
          <div className="bg-gray-800/60 rounded-lg px-4 py-3 border border-gray-700/50 hover:border-purple-500/30 transition-all">
            <p className="text-[10px] text-gray-500 uppercase font-bold tracking-widest mb-1.5">Claim</p>
            <p className="text-xs text-gray-300 italic">&quot;{result.extracted_claim}&quot;</p>
          </div>
        )}

        {/* Sources - Collapsible */}
        {result.sources.length > 0 && (
          <div className="space-y-2 border-t border-gray-700/50 pt-4">
            <button
              onClick={() => setSourcesExpanded(!sourcesExpanded)}
              className="text-xs font-semibold text-gray-400 hover:text-purple-400 transition-colors flex items-center gap-2 group"
            >
              <span className="group-hover:translate-x-0.5 transition-transform">📚</span>
              Sources ({result.sources.length})
              <span className={`transition-transform ${sourcesExpanded ? "rotate-180" : ""}`}>▼</span>
            </button>

            {sourcesExpanded && (
              <div className="space-y-2 mt-3 animate-fadeIn">
                {result.sources.map((src, i) => (
                  <SourceCard key={i} source={src} index={i} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Meta - Subtle footer */}
        <div className="flex flex-wrap gap-4 text-[10px] text-gray-600 border-t border-gray-700/50 pt-2.5">
          <span className="hover:text-gray-400 transition-colors">⏱ {(result.latency_ms / 1000).toFixed(1)}s</span>
          {result.bart_label && (
            <span className="hover:text-gray-400 transition-colors">
              BART: {result.bart_label} ({result.bart_score?.toFixed(3)})
            </span>
          )}
          {result.detection_method && (
            <span className="hover:text-gray-400 transition-colors">
              {result.detection_method}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

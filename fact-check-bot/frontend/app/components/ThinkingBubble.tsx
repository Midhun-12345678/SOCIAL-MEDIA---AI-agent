"use client";

type ProgressStep = {
  stage: string;
  message: string;
  done: boolean;
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

export function ThinkingBubble({ steps }: { steps: ProgressStep[] }) {
  return (
    <div className="flex gap-3 mb-6 animate-fadeIn">
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center text-sm flex-shrink-0 mt-0.5 shadow-lg shadow-purple-600/50">
        🤖
      </div>
      <div className="bg-gradient-to-br from-gray-800 to-gray-900 border border-gray-700 rounded-3xl rounded-tl-none px-5 py-4 max-w-lg shadow-lg shadow-purple-600/10">
        {steps.length === 0 ? (
          <div className="flex gap-1.5 items-center py-1">
            <span className="w-2 h-2 bg-gradient-to-r from-blue-400 to-purple-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
            <span className="w-2 h-2 bg-gradient-to-r from-purple-400 to-pink-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
            <span className="w-2 h-2 bg-gradient-to-r from-pink-400 to-blue-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
          </div>
        ) : (
          <div className="space-y-0">
            {steps.map((step, i) => (
              <div key={i}>
                {i > 0 && (
                  <div className="ml-[7px] w-px h-3 bg-gradient-to-b from-purple-500/40 to-gray-700/40" />
                )}
                <div className="flex items-center gap-3 text-xs">
                  {step.done ? (
                    <span className="w-4 h-4 rounded-full bg-gradient-to-br from-green-500/30 to-teal-500/30 flex items-center justify-center text-green-300 text-[10px] flex-shrink-0 font-bold">✓</span>
                  ) : (
                    <span className="w-4 h-4 rounded-full bg-gradient-to-br from-blue-500/30 to-purple-500/30 flex items-center justify-center flex-shrink-0">
                      <span className="w-2 h-2 bg-gradient-to-r from-blue-400 to-purple-400 rounded-full animate-pulse" />
                    </span>
                  )}
                  <span className={step.done ? "text-gray-500" : "text-gray-200 font-medium"}>
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

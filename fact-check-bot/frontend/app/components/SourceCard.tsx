"use client";

type Source = {
  title: string;
  url: string;
  snippet: string;
};

export function SourceCard({ source, index }: { source: Source; index: number }) {
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex gap-3 items-start bg-gradient-to-br from-gray-800/50 to-gray-900/50 hover:from-purple-900/30 hover:to-gray-900/50 border border-gray-700/50 hover:border-purple-500/50 rounded-lg px-4 py-3 transition-all duration-200 group transform hover:scale-102 hover:shadow-lg hover:shadow-purple-500/10"
    >
      <span className="text-xs text-gray-500 font-mono mt-0.5 flex-shrink-0 bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent font-bold">
        {index + 1}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold text-blue-400 group-hover:text-blue-300 transition-colors truncate">
          {source.title}
        </p>
        <p className="text-xs text-gray-500 mt-1 line-clamp-2 group-hover:text-gray-400 transition-colors">
          {source.snippet}
        </p>
      </div>
      <span className="text-gray-600 group-hover:text-purple-400 transition-colors flex-shrink-0">→</span>
    </a>
  );
}

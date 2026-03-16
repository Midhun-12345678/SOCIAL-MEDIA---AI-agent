"use client";

export function UserBubble({ text }: { text: string }) {
  return (
    <div className="flex gap-3 mb-6 justify-end animate-fadeIn">
      <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-3xl rounded-tr-none px-5 py-3 max-w-xl shadow-lg shadow-blue-600/20 hover:shadow-blue-600/40 transition-all">
        <p className="text-sm text-white leading-relaxed">{text}</p>
      </div>
      <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-sm flex-shrink-0 mt-0.5">
        👤
      </div>
    </div>
  );
}

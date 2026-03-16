"use client";

import { useState } from "react";

type LandingPageProps = {
  onGetStarted: () => void;
};

export default function LandingPage({ onGetStarted }: LandingPageProps) {
  const [currentStep, setCurrentStep] = useState(0);

  const steps = [
    {
      title: "AI-Powered Claim Verification",
      subtitle: "Social Media Bot",
      description: "Instantly verify claims from Twitter, Reddit, and other social media platforms using advanced AI and real-time fact-checking.",
      icon: "🔍",
      highlights: [
        "✨ Real-time verification",
        "🌐 Multiple sources",
        "🎯 Instant results",
        "🔒 Privacy-focused",
      ],
    },
    {
      title: "How It Works",
      subtitle: "4-Step Verification Process",
      description: "Our advanced AI pipeline processes your claim through multiple stages:",
      icon: "⚙️",
      highlights: [
        "1️⃣ Extract the claim from your text",
        "2️⃣ Classify if it's a verifiable claim",
        "3️⃣ Retrieve relevant sources online",
        "4️⃣ Generate a fact-check verdict with confidence score",
      ],
    },
    {
      title: "Use Cases",
      subtitle: "When to Use Fact-Check Bot",
      description: "Perfect for journalists, students, and anyone seeking truth:",
      icon: "📊",
      highlights: [
        "📰 Verify viral news stories",
        "🎓 Research for academic work",
        "💬 Fact-check social media claims",
        "📱 Identify misinformation quickly",
      ],
    },
    {
      title: "Privacy & Transparency",
      subtitle: "Your Data is Safe",
      description: "Comprehensive information about how we process your data:",
      icon: "🔐",
      highlights: [
        "✅ Claims cached only for performance",
        "🚫 No personal data collection",
        "🌍 Uses public sources only",
        "📊 Transparent AI reasoning",
      ],
    },
  ];

  const step = steps[currentStep];
  const progress = ((currentStep + 1) / steps.length) * 100;

  return (
    <main className="h-screen flex flex-col bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950 text-white overflow-hidden">
      {/* Header with progress */}
      <div className="border-b border-gray-800 px-6 py-4 flex-shrink-0">
        <div className="max-w-2xl mx-auto">
          <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Step {currentStep + 1} of {steps.length}
          </p>
        </div>
      </div>

      {/* Main Content - Scrollable */}
      <div className="flex-1 overflow-y-auto flex items-center justify-center px-6 py-6">
        <div className="max-w-2xl w-full text-center space-y-6 animate-fadeIn py-4">
          {/* Icon */}
          <div className="text-7xl">{step.icon}</div>

          {/* Title */}
          <div className="space-y-2">
            <p className="text-sm font-semibold text-purple-400 uppercase tracking-wider">
              {step.subtitle}
            </p>
            <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-200 via-purple-200 to-pink-200 bg-clip-text text-transparent">
              {step.title}
            </h1>
          </div>

          {/* Description */}
          <p className="text-lg text-gray-300 leading-relaxed">{step.description}</p>

          {/* Highlights */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {step.highlights.map((highlight, idx) => (
              <div
                key={idx}
                className="p-4 rounded-lg bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 hover:border-purple-500/30 transition-all transform hover:scale-105 hover:shadow-lg hover:shadow-purple-500/20"
              >
                <p className="text-sm text-gray-200">{highlight}</p>
              </div>
            ))}
          </div>

          {/* Visual Divider for Chat Example (on step 1) */}
          {currentStep === 1 && (
            <div className="mt-6 pt-6 border-t border-gray-700 space-y-4">
              <p className="text-sm text-gray-400">Example Interaction:</p>
              <div className="bg-gray-800/40 rounded-lg p-4 border border-gray-700/50 space-y-3">
                <div className="flex justify-end">
                  <div className="bg-blue-600 rounded-2xl rounded-tr-none px-4 py-2 max-w-xs">
                    <p className="text-sm">Is the moon made of cheese?</p>
                  </div>
                </div>
                <div className="flex justify-start">
                  <div className="bg-gray-700 rounded-2xl rounded-tl-none px-4 py-2 max-w-xs">
                    <p className="text-sm text-gray-200">
                      <span className="font-semibold text-red-400">FALSE</span>
                      <span className="text-gray-400"> (98% confident)</span>
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Navigation Footer - Always Visible */}
      <div className="border-t border-gray-800 px-6 py-4 flex-shrink-0 bg-gradient-to-t from-gray-900 to-gray-900/50 backdrop-blur-sm sticky bottom-0">
        <div className="max-w-2xl mx-auto flex items-center justify-between gap-4">
          <button
            onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
            disabled={currentStep === 0}
            className="px-6 py-2 rounded-lg border border-gray-700 text-gray-300 hover:text-white hover:border-gray-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm font-medium"
          >
            ← Previous
          </button>

          <div className="flex gap-2">
            {steps.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentStep(idx)}
                className={`w-2 h-2 rounded-full transition-all ${
                  idx === currentStep
                    ? "w-8 bg-gradient-to-r from-blue-500 to-purple-500"
                    : "bg-gray-700 hover:bg-gray-600"
                }`}
                aria-label={`Go to step ${idx + 1}`}
              />
            ))}
          </div>

          <button
            onClick={() => {
              if (currentStep < steps.length - 1) {
                setCurrentStep(currentStep + 1);
              } else {
                onGetStarted();
              }
            }}
            className="px-6 py-2 rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold transition-all text-sm flex-shrink-0 transform hover:scale-105 active:scale-95"
          >
            {currentStep < steps.length - 1 ? "Next →" : "Get Started 🚀"}
          </button>
        </div>
      </div>
    </main>
  );
}

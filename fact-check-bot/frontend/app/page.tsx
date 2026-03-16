"use client";

import { useState } from "react";
import LandingPage from "./components/LandingPage";
import { ChatInterface } from "./components/ChatInterface";

export default function Home() {
  const [showChat, setShowChat] = useState(false);

  return showChat ? (
    <ChatInterface />
  ) : (
    <LandingPage onGetStarted={() => setShowChat(true)} />
  );
}

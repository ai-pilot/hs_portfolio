import React, { useState, useCallback } from "react";
import { AnimatePresence } from "framer-motion";
import ChatBubble from "./components/ChatBubble";
import ChatWindow from "./components/ChatWindow";
import { SoundProvider } from "./components/SoundEngine";

const API_BASE = window.ORIENT_EXPRESS_API || "";

export default function App() {
  const [isOpen, setIsOpen] = useState(false);
  const [hasOpened, setHasOpened] = useState(false);

  const handleToggle = useCallback(() => {
    setIsOpen((prev) => {
      if (!prev) setHasOpened(true);
      return !prev;
    });
  }, []);

  return (
    <SoundProvider>
      <div className="oe-widget">
        <AnimatePresence>
          {isOpen && (
            <ChatWindow
              key="chat-window"
              apiBase={API_BASE}
              onClose={handleToggle}
              isFirstOpen={!hasOpened}
            />
          )}
        </AnimatePresence>
        <ChatBubble isOpen={isOpen} onClick={handleToggle} />
      </div>
    </SoundProvider>
  );
}

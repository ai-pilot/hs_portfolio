import React, { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import {
  Volume2,
  VolumeX,
  Trash2,
  Train,
  Minimize2,
} from "lucide-react";
import MessageList from "./MessageList";
import InputBar from "./InputBar";
import { useSound } from "./SoundEngine";
import useChat from "../hooks/useChat";

const SUGGESTIONS = [
  "Tell me about Himanshu's AI experience",
  "What projects has he built at DAMAC?",
  "What are his core skills?",
  "Explain RAG architecture",
  "What's his education?",
];

export default function ChatWindow({ apiBase, onClose, isFirstOpen }) {
  const { play, muted, toggleMute } = useSound();
  const chat = useChat(apiBase);
  const [streamingText, setStreamingText] = useState("");
  const [thinkingText, setThinkingText] = useState("");
  const [showWelcome, setShowWelcome] = useState(true);
  const hasPlayedWhistle = useRef(false);

  useEffect(() => {
    if (isFirstOpen && !hasPlayedWhistle.current) {
      hasPlayedWhistle.current = true;
      setTimeout(() => play("whistle"), 300);
    }
  }, [isFirstOpen, play]);

  useEffect(() => {
    if (chat.messages.length > 0) setShowWelcome(false);
  }, [chat.messages.length]);

  const handleSend = async (content) => {
    play("send");
    setStreamingText("");
    setThinkingText("");

    await chat.sendMessage(
      content,
      (thinkChunk) => {
        play("thinking");
        setThinkingText((prev) => prev + thinkChunk);
      },
      (tokenChunk) => {
        if (tokenChunk === "__clear__") {
          setStreamingText("");
        } else {
          setStreamingText((prev) => prev + tokenChunk);
        }
      },
      () => {
        play("receive");
        setStreamingText("");
        setThinkingText("");
      }
    );
  };

  const handleSuggestion = (text) => {
    play("click");
    handleSend(text);
  };

  const handleUpload = async (file) => {
    try {
      play("click");
      const result = await chat.uploadFile(file);
      if (result) {
        play("upload");
        return result;
      }
    } catch (err) {
      play("error");
      throw err;
    }
  };

  const handleClear = () => {
    play("click");
    chat.clearChat();
    setShowWelcome(true);
  };

  return (
    <motion.div
      className="oe-window"
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 20, scale: 0.95 }}
      transition={{ type: "spring", stiffness: 300, damping: 25 }}
    >
      {/* Header */}
      <div className="oe-header">
        <div className="oe-header-left">
          <div className="oe-avatar">
            <Train size={20} />
          </div>
          <div className="oe-header-info">
            <span className="oe-header-name">Orient Express</span>
            <span className="oe-header-status">
              {chat.isThinking
                ? "Thinking..."
                : chat.activeTool
                ? `Using ${chat.activeTool}...`
                : chat.isLoading
                ? "Composing..."
                : "Online"}
            </span>
          </div>
        </div>
        <div className="oe-header-actions">
          <button
            className="oe-icon-btn"
            onClick={toggleMute}
            title={muted ? "Unmute" : "Mute"}
          >
            {muted ? <VolumeX size={16} /> : <Volume2 size={16} />}
          </button>
          <button className="oe-icon-btn" onClick={handleClear} title="Clear chat">
            <Trash2 size={16} />
          </button>
          <button className="oe-icon-btn" onClick={onClose} title="Minimize">
            <Minimize2 size={16} />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="oe-body">
        {showWelcome && chat.messages.length === 0 ? (
          <div className="oe-welcome">
            <motion.div
              className="oe-welcome-icon"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", delay: 0.2 }}
            >
              <Train size={48} />
            </motion.div>
            <motion.h3
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              All Aboard!
            </motion.h3>
            <motion.p
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              I'm Orient Express, Himanshu's AI assistant. Ask me about his
              experience, upload documents, or analyze data!
            </motion.p>
            <motion.div
              className="oe-suggestions"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.7 }}
            >
              {SUGGESTIONS.map((s, i) => (
                <motion.button
                  key={i}
                  className="oe-suggestion"
                  onClick={() => handleSuggestion(s)}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.8 + i * 0.1 }}
                >
                  {s}
                </motion.button>
              ))}
            </motion.div>
          </div>
        ) : (
          <MessageList
            messages={chat.messages}
            streamingText={streamingText}
            thinkingText={thinkingText}
            isLoading={chat.isLoading}
            isThinking={chat.isThinking}
            activeTool={chat.activeTool}
            metrics={chat.metrics}
            followups={chat.followups}
            onFollowup={handleSuggestion}
          />
        )}
      </div>

      {/* Input */}
      <InputBar
        onSend={handleSend}
        onUpload={handleUpload}
        onStop={chat.stopGeneration}
        isLoading={chat.isLoading}
        sessionId={chat.sessionId}
      />

      {/* Metrics bar */}
      {chat.metrics && chat.metrics.latency > 0 && (
        <div className="oe-metrics">
          <span>{chat.metrics.latency}ms</span>
          {chat.metrics.tokens > 0 && <span>{chat.metrics.tokens} tokens</span>}
        </div>
      )}
    </motion.div>
  );
}

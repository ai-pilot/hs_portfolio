import React, { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  User,
  Train,
  AlertTriangle,
  Brain,
  Wrench,
  ChevronDown,
  ChevronUp,
  ThumbsUp,
  ThumbsDown,
  Copy,
  Check,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

function MarkdownContent({ content }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ inline, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || "");
          if (!inline && match) {
            return (
              <div className="oe-code-block">
                <div className="oe-code-header">
                  <span>{match[1]}</span>
                  <CopyButton text={String(children)} />
                </div>
                <SyntaxHighlighter
                  style={oneDark}
                  language={match[1]}
                  PreTag="div"
                  customStyle={{
                    margin: 0,
                    borderRadius: "0 0 8px 8px",
                    fontSize: "13px",
                  }}
                  {...props}
                >
                  {String(children).replace(/\n$/, "")}
                </SyntaxHighlighter>
              </div>
            );
          }
          return (
            <code className="oe-inline-code" {...props}>
              {children}
            </code>
          );
        },
        table({ children }) {
          return (
            <div className="oe-table-wrap">
              <table>{children}</table>
            </div>
          );
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button className="oe-copy-btn" onClick={handleCopy}>
      {copied ? <Check size={14} /> : <Copy size={14} />}
    </button>
  );
}

function ThinkingIndicator({ text, isActive }) {
  const [expanded, setExpanded] = useState(false);

  if (!text && !isActive) return null;

  return (
    <motion.div
      className="oe-thinking"
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
    >
      <button
        className="oe-thinking-toggle"
        onClick={() => setExpanded(!expanded)}
      >
        <Brain size={14} className={isActive ? "oe-pulse" : ""} />
        <span>{isActive ? "Thinking..." : "Thought process"}</span>
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
      <AnimatePresence>
        {expanded && text && (
          <motion.div
            className="oe-thinking-content"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
          >
            {text}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function ToolIndicator({ toolName }) {
  if (!toolName) return null;

  const toolLabels = {
    search_knowledge: "Searching knowledge base",
    analyze_data: "Analyzing data",
    explain_code: "Analyzing code",
  };

  return (
    <motion.div
      className="oe-tool-indicator"
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -10 }}
    >
      <Wrench size={14} className="oe-spin" />
      <span>{toolLabels[toolName] || toolName}</span>
    </motion.div>
  );
}

function MessageBubble({ message, isStreaming }) {
  const [feedback, setFeedback] = useState(null);

  const isUser = message.role === "user";
  const isSystem = message.role === "system";
  const isError = message.isError;

  return (
    <motion.div
      className={`oe-message ${isUser ? "oe-message-user" : "oe-message-bot"} ${
        isSystem ? "oe-message-system" : ""
      } ${isError ? "oe-message-error" : ""}`}
      initial={{ opacity: 0, y: 15, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
      layout
    >
      {!isUser && !isSystem && (
        <div className="oe-message-avatar">
          <Train size={16} />
        </div>
      )}
      {isSystem && (
        <div className="oe-message-avatar oe-avatar-system">
          <AlertTriangle size={16} />
        </div>
      )}

      <div className="oe-message-content">
        {message.thinking && (
          <ThinkingIndicator text={message.thinking} isActive={false} />
        )}
        <div className="oe-message-text">
          {isUser ? (
            message.content
          ) : (
            <MarkdownContent content={message.content} />
          )}
        </div>

        {/* Feedback buttons for bot messages */}
        {!isUser && !isSystem && !isStreaming && (
          <div className="oe-message-actions">
            <CopyButton text={message.content} />
            <button
              className={`oe-feedback-btn ${feedback === "up" ? "active" : ""}`}
              onClick={() => setFeedback("up")}
            >
              <ThumbsUp size={13} />
            </button>
            <button
              className={`oe-feedback-btn ${feedback === "down" ? "active" : ""}`}
              onClick={() => setFeedback("down")}
            >
              <ThumbsDown size={13} />
            </button>
          </div>
        )}
      </div>

      {isUser && (
        <div className="oe-message-avatar oe-avatar-user">
          <User size={16} />
        </div>
      )}
    </motion.div>
  );
}

function TypingIndicator({ status }) {
  const labels = {
    thinking: "Thinking through this...",
    searching: "Searching knowledge base...",
    analyzing: "Analyzing your data...",
    composing: "Composing response...",
    default: "Getting ready...",
  };

  const label = labels[status] || labels.default;

  return (
    <motion.div
      className="oe-typing"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <div className="oe-message-avatar">
        <Train size={16} />
      </div>
      <div className="oe-typing-bubble">
        <div className="oe-typing-dots">
          <span />
          <span />
          <span />
        </div>
        <span className="oe-typing-label">{label}</span>
      </div>
    </motion.div>
  );
}

export default function MessageList({
  messages,
  streamingText,
  thinkingText,
  isLoading,
  isThinking,
  activeTool,
  metrics,
  followups,
  onFollowup,
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText, thinkingText, isLoading]);

  return (
    <div className="oe-messages">
      <AnimatePresence mode="popLayout">
        {messages.map((msg, i) => (
          <MessageBubble key={`${msg.timestamp}-${i}`} message={msg} />
        ))}
      </AnimatePresence>

      {/* Streaming state */}
      {isLoading && (
        <>
          {isThinking && (
            <ThinkingIndicator text={thinkingText} isActive={true} />
          )}

          <AnimatePresence>
            {activeTool && <ToolIndicator toolName={activeTool} />}
          </AnimatePresence>

          {streamingText ? (
            <motion.div
              className="oe-message oe-message-bot oe-streaming"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div className="oe-message-avatar">
                <Train size={16} />
              </div>
              <div className="oe-message-content">
                <div className="oe-message-text">
                  <MarkdownContent content={streamingText} />
                </div>
              </div>
            </motion.div>
          ) : (
            !isThinking &&
            !activeTool && (
              <TypingIndicator
                status={
                  isThinking
                    ? "thinking"
                    : activeTool === "search_knowledge"
                    ? "searching"
                    : activeTool === "analyze_data"
                    ? "analyzing"
                    : "composing"
                }
              />
            )
          )}
        </>
      )}

      {/* Follow-up suggestion chips */}
      {!isLoading && followups && followups.length > 0 && (
        <motion.div
          className="oe-followups"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          {followups.map((text, i) => (
            <motion.button
              key={i}
              className="oe-followup-chip"
              onClick={() => onFollowup(text)}
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.96 }}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 + i * 0.1 }}
            >
              {text}
            </motion.button>
          ))}
        </motion.div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}

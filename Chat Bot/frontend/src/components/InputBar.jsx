import React, { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Square,
  Paperclip,
  FileText,
  X,
  Upload,
  Loader,
} from "lucide-react";
import { useSound } from "./SoundEngine";

export default function InputBar({ onSend, onUpload, onStop, isLoading, sessionId }) {
  const { play } = useSound();
  const [input, setInput] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null); // null | 'uploading' | {success: true/false, message: ''}
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  const handleSubmit = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [input, isLoading, onSend]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
    if (e.key === "Escape" && isLoading) {
      onStop();
    }
  };

  const handleInput = (e) => {
    setInput(e.target.value);
    // Auto-resize
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  };

  const handleFile = async (file) => {
    if (!file) return;
    if (!sessionId) {
      // Send an initial message first to get a session
      setUploadStatus({ success: false, message: "Send a message first to start a session, then upload your file." });
      setTimeout(() => setUploadStatus(null), 3000);
      return;
    }

    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      play("error");
      setUploadStatus({ success: false, message: "File too large (max 10MB)" });
      setTimeout(() => setUploadStatus(null), 3000);
      return;
    }

    setUploadStatus("uploading");
    try {
      const result = await onUpload(file);
      setUploadStatus({ success: true, message: result.message });
      setTimeout(() => setUploadStatus(null), 4000);
    } catch (err) {
      setUploadStatus({ success: false, message: err.message });
      setTimeout(() => setUploadStatus(null), 3000);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFile(file);
  };

  const handleFileInput = (e) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = "";
  };

  return (
    <div
      className={`oe-input-area ${isDragging ? "oe-dragging" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      {/* Upload status */}
      <AnimatePresence>
        {uploadStatus && (
          <motion.div
            className={`oe-upload-status ${
              uploadStatus === "uploading"
                ? "uploading"
                : uploadStatus.success
                ? "success"
                : "error"
            }`}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
          >
            {uploadStatus === "uploading" ? (
              <>
                <Loader size={14} className="oe-spin" /> Uploading & indexing...
              </>
            ) : (
              <>
                {uploadStatus.success ? (
                  <FileText size={14} />
                ) : (
                  <X size={14} />
                )}
                {uploadStatus.message}
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Drag overlay */}
      <AnimatePresence>
        {isDragging && (
          <motion.div
            className="oe-drag-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <Upload size={32} />
            <span>Drop file here</span>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="oe-input-row">
        <button
          className="oe-icon-btn"
          onClick={() => fileInputRef.current?.click()}
          title="Upload file"
        >
          <Paperclip size={18} />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          className="oe-file-input"
          accept=".pdf,.docx,.doc,.txt,.csv,.xlsx,.xls"
          onChange={handleFileInput}
        />

        <textarea
          ref={textareaRef}
          className="oe-textarea"
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask me anything..."
          rows={1}
          disabled={isLoading}
        />

        {isLoading ? (
          <motion.button
            className="oe-send-btn oe-stop-btn"
            onClick={onStop}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            title="Stop (Esc)"
          >
            <Square size={16} fill="currentColor" />
          </motion.button>
        ) : (
          <motion.button
            className="oe-send-btn"
            onClick={handleSubmit}
            disabled={!input.trim()}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            title="Send (Enter)"
          >
            <Send size={16} />
          </motion.button>
        )}
      </div>

      <div className="oe-input-hint">
        <span>Enter to send · Shift+Enter for new line · Esc to stop</span>
      </div>
    </div>
  );
}

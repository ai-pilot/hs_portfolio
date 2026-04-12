import React, { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Train, X } from "lucide-react";
import { useSound } from "./SoundEngine";

export default function ChatBubble({ isOpen, onClick }) {
  const { play } = useSound();
  const [vibrating, setVibrating] = useState(false);
  const timerRef = useRef(null);

  // Vibrate every 8 seconds when chat is closed to grab attention
  useEffect(() => {
    if (isOpen) {
      clearInterval(timerRef.current);
      setVibrating(false);
      return;
    }

    // Initial vibrate after 3 seconds
    const initialTimer = setTimeout(() => {
      setVibrating(true);
      setTimeout(() => setVibrating(false), 600);
    }, 3000);

    // Then every 8 seconds
    timerRef.current = setInterval(() => {
      setVibrating(true);
      setTimeout(() => setVibrating(false), 600);
    }, 8000);

    return () => {
      clearTimeout(initialTimer);
      clearInterval(timerRef.current);
    };
  }, [isOpen]);

  const handleClick = () => {
    play("click");
    onClick();
  };

  return (
    <motion.button
      className={`oe-bubble ${vibrating ? "oe-bubble-vibrate" : ""}`}
      onClick={handleClick}
      whileHover={{ scale: 1.1 }}
      whileTap={{ scale: 0.9 }}
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: "spring", stiffness: 400, damping: 15 }}
      aria-label={isOpen ? "Close chat" : "Open chat"}
    >
      <motion.div
        className="oe-bubble-icon"
        animate={{ rotate: isOpen ? 90 : 0 }}
        transition={{ duration: 0.3 }}
      >
        {isOpen ? <X size={24} /> : <Train size={24} />}
      </motion.div>
      {!isOpen && <span className="oe-bubble-pulse" />}
    </motion.button>
  );
}

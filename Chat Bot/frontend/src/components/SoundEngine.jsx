import React, { createContext, useContext, useState, useCallback, useRef } from "react";

const SoundContext = createContext(null);

// Generate sounds programmatically using Web Audio API — no external files needed
function createSoundPlayer() {
  let audioCtx = null;

  function getCtx() {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    return audioCtx;
  }

  function playTone(freq, duration, type = "sine", volume = 0.15, ramp = true) {
    try {
      const ctx = getCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      gain.gain.setValueAtTime(volume, ctx.currentTime);
      if (ramp) {
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
      }
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + duration);
    } catch (e) {
      // Silently fail if audio not available
    }
  }

  return {
    send() {
      // Gentle whoosh — rising tones
      playTone(400, 0.15, "sine", 0.08);
      setTimeout(() => playTone(600, 0.1, "sine", 0.06), 50);
    },

    receive() {
      // Soft chime — two pleasant notes
      playTone(800, 0.2, "sine", 0.08);
      setTimeout(() => playTone(1000, 0.25, "sine", 0.06), 120);
    },

    click() {
      // Subtle click
      playTone(1200, 0.05, "square", 0.04);
    },

    whistle() {
      // Train whistle — sliding frequency
      try {
        const ctx = getCtx();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(600, ctx.currentTime);
        osc.frequency.linearRampToValueAtTime(900, ctx.currentTime + 0.3);
        osc.frequency.linearRampToValueAtTime(800, ctx.currentTime + 0.6);
        gain.gain.setValueAtTime(0.1, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.8);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(ctx.currentTime);
        osc.stop(ctx.currentTime + 0.8);
      } catch (e) {}
    },

    error() {
      // Low buzz
      playTone(200, 0.2, "sawtooth", 0.06);
    },

    upload() {
      // Success ding — ascending arpeggio
      playTone(500, 0.15, "sine", 0.07);
      setTimeout(() => playTone(700, 0.15, "sine", 0.07), 100);
      setTimeout(() => playTone(900, 0.2, "sine", 0.07), 200);
    },

    thinking() {
      // Subtle pulse
      playTone(300, 0.3, "sine", 0.03);
    },
  };
}

export function SoundProvider({ children }) {
  const [muted, setMuted] = useState(false);
  const playerRef = useRef(null);

  if (!playerRef.current) {
    playerRef.current = createSoundPlayer();
  }

  const play = useCallback(
    (soundName) => {
      if (muted) return;
      const fn = playerRef.current[soundName];
      if (fn) fn();
    },
    [muted]
  );

  const toggleMute = useCallback(() => setMuted((m) => !m), []);

  return (
    <SoundContext.Provider value={{ play, muted, toggleMute }}>
      {children}
    </SoundContext.Provider>
  );
}

export function useSound() {
  return useContext(SoundContext);
}

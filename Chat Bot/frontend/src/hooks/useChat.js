import { useState, useRef, useCallback } from "react";

export default function useChat(apiBase = "") {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [activeTool, setActiveTool] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [followups, setFollowups] = useState([]);
  const abortRef = useRef(null);

  const sendMessage = useCallback(
    async (content, onThink, onToken, onDone) => {
      const userMsg = { role: "user", content, timestamp: Date.now() };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setIsThinking(false);
      setActiveTool(null);
      setMetrics(null);
      setFollowups([]);

      const allMessages = [...messages, userMsg].map((m) => ({
        role: m.role,
        content: m.content,
      }));

      abortRef.current = new AbortController();
      let botText = "";
      let thinkingText = "";

      try {
        const res = await fetch(`${apiBase}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: allMessages,
            session_id: sessionId,
          }),
          signal: abortRef.current.signal,
        });

        if (!res.ok) {
          throw new Error(`Server error: ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const data = JSON.parse(line.slice(6));

            switch (data.type) {
              case "session":
                setSessionId(data.session_id);
                break;

              case "thinking":
                setIsThinking(true);
                thinkingText += data.content;
                onThink?.(data.content);
                break;

              case "clear":
                // Discard pre-tool-call text — the real answer comes after
                botText = "";
                onToken?.("__clear__");
                break;

              case "tool_start":
                setIsThinking(false);
                setActiveTool(data.name);
                break;

              case "tool_end":
                setActiveTool(null);
                break;

              case "text":
                setIsThinking(false);
                botText += data.content;
                onToken?.(data.content);
                break;

              case "warning":
                setMessages((prev) => [
                  ...prev,
                  {
                    role: "system",
                    content: data.content,
                    timestamp: Date.now(),
                  },
                ]);
                break;

              case "guardrail":
                // Will be followed by text with the guardrail message
                break;

              case "followups":
                setFollowups(data.suggestions || []);
                break;

              case "done":
                setMetrics({
                  tokens: data.tokens_used,
                  latency: data.latency_ms,
                  thinking: data.thinking_summary,
                });
                break;
            }
          }
        }

        if (botText) {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: botText,
              thinking: thinkingText,
              timestamp: Date.now(),
            },
          ]);
        }

        onDone?.();
      } catch (err) {
        if (err.name !== "AbortError") {
          const errorMsg = "Oops, looks like we hit a bump on the tracks! Please try again.";
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: errorMsg,
              isError: true,
              timestamp: Date.now(),
            },
          ]);
          onDone?.();
        }
      } finally {
        setIsLoading(false);
        setIsThinking(false);
        setActiveTool(null);
      }
    },
    [apiBase, messages, sessionId]
  );

  const stopGeneration = useCallback(() => {
    abortRef.current?.abort();
    setIsLoading(false);
    setIsThinking(false);
  }, []);

  const uploadFile = useCallback(
    async (file) => {
      if (!sessionId) return null;

      const formData = new FormData();
      formData.append("file", file);
      formData.append("session_id", sessionId);

      const res = await fetch(`${apiBase}/api/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed");
      }

      const result = await res.json();

      // Auto-show document summary as a bot message
      if (result.summary) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: result.summary,
            timestamp: Date.now(),
          },
        ]);
      }

      // Show upload-specific follow-up suggestions
      if (result.followups) {
        setFollowups(result.followups);
      }

      return result;
    },
    [apiBase, sessionId]
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setMetrics(null);
  }, []);

  return {
    messages,
    isLoading,
    isThinking,
    activeTool,
    sessionId,
    metrics,
    followups,
    sendMessage,
    stopGeneration,
    uploadFile,
    clearChat,
  };
}

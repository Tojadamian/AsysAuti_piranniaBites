import React, { useEffect, useRef, useState } from "react";

const styles = {
  container: {
    width: "100%",
    maxWidth: 720,
    margin: "0 auto",
    padding: 16,
    boxSizing: "border-box",
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  messages: {
    height: "60vh",
    overflowY: "auto",
    display: "flex",
    flexDirection: "column",
    gap: 8,
    padding: 12,
    background: "#fff",
    borderRadius: 8,
    boxShadow: "0 2px 8px rgba(3,3,3,0.06)",
  },
  messageUser: {
    alignSelf: "flex-end",
    background: "#29b433",
    color: "white",
    padding: "8px 12px",
    borderRadius: 12,
    maxWidth: "80%",
  },
  messageAssistant: {
    alignSelf: "flex-start",
    background: "#f1f5f9",
    color: "#111827",
    padding: "8px 12px",
    borderRadius: 12,
    maxWidth: "80%",
  },
  form: {
    display: "flex",
    gap: 8,
  },
  input: {
    flex: 1,
    padding: "10px 12px",
    borderRadius: 8,
    border: "1px solid #e5e7eb",
    fontSize: 14,
  },
  button: {
    padding: "10px 14px",
    background: "#29b433",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    cursor: "pointer",
  },
  info: {
    fontSize: 13,
    color: "#6b7280",
  },
};

const ChatWindow = () => {
  const [messages, setMessages] = useState([
    { role: "assistant", text: "Cześć! Jak mogę pomóc?" },
  ]);
  const [model, setModel] = useState("gpt-3.5-turbo");
  const [temperature, setTemperature] = useState(0.6);
  const [maxTokens, setMaxTokens] = useState(500);
  const [assistantRole, setAssistantRole] = useState("care_assistant");
  const [useCustomSystem, setUseCustomSystem] = useState(false);
  const [customSystem, setCustomSystem] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesRef = useRef(null);

  useEffect(() => {
    // przewiń na dół przy aktualizacji wiadomości
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const sendMessage = async (e) => {
    e && e.preventDefault();
    if (!input.trim()) return;
    const userText = input.trim();
    setInput("");
    setError(null);

    // dopisz wiadomość użytkownika natychmiast
    setMessages((m) => [...m, { role: "user", text: userText }]);
    setLoading(true);

    try {
      const payload = { message: userText };
      // dołącz parametry modelu/roli tylko jeśli Advanced jest widoczne
      if (showAdvanced) {
        if (model) payload.model = model;
        if (typeof temperature !== "undefined")
          payload.temperature = Number(temperature);
        if (typeof maxTokens !== "undefined")
          payload.max_tokens = Number(maxTokens);
        // dołącz role/system prompt
        if (useCustomSystem && customSystem && customSystem.trim()) {
          payload.system = customSystem.trim();
        } else if (assistantRole) {
          payload.assistant_role = assistantRole;
        }
      }

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const t = await res.text();
        throw new Error(`Serwer zwrócił błąd: ${res.status} — ${t}`);
      }

      const data = await res.json();

      // Zakładamy że backend zwraca { reply: "..." }
      const reply = data.reply || data.message || "(Brak odpowiedzi)";

      setMessages((m) => [...m, { role: "assistant", text: reply }]);
    } catch (err) {
      setError(err.message || String(err));
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: "Przepraszam, wystąpił błąd przy wysyłaniu wiadomości.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      {/* Advanced toggle: radio buttons to show/hide extra options */}
      <div
        style={{
          display: "flex",
          gap: 12,
          alignItems: "center",
          marginBottom: 8,
        }}
      >
        <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <input
            type="radio"
            name="advanced"
            checked={!showAdvanced}
            onChange={() => setShowAdvanced(false)}
          />
          <span style={{ fontSize: 13 }}>Ukryj opcje</span>
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <input
            type="radio"
            name="advanced"
            checked={showAdvanced}
            onChange={() => setShowAdvanced(true)}
          />
          <span style={{ fontSize: 13 }}>Pokaż opcje</span>
        </label>
      </div>

      {showAdvanced && (
        <>
          <div
            style={{
              display: "flex",
              gap: 8,
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              style={{ padding: 8, borderRadius: 8 }}
            >
              <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
              <option value="gpt-4">gpt-4</option>
              <option value="gpt-5-pro">gpt-5-pro</option>
            </select>
            <input
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              title="temperature"
              style={{
                width: 80,
                padding: 8,
                borderRadius: 8,
                border: "1px solid #e5e7eb",
              }}
            />
            <input
              type="number"
              min="1"
              max="2000"
              value={maxTokens}
              onChange={(e) => setMaxTokens(parseInt(e.target.value || "0"))}
              title="max tokens"
              style={{
                width: 100,
                padding: 8,
                borderRadius: 8,
                border: "1px solid #e5e7eb",
              }}
            />
            <select
              value={assistantRole}
              onChange={(e) => setAssistantRole(e.target.value)}
              style={{ padding: 8, borderRadius: 8 }}
            >
              <option value="care_assistant">Asystent opieki (autyzm)</option>
              <option value="default">Domyślny pomocnik</option>
            </select>
            <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <input
                type="checkbox"
                checked={useCustomSystem}
                onChange={(e) => setUseCustomSystem(e.target.checked)}
              />
              <span style={{ fontSize: 12 }}>Własny system prompt</span>
            </label>
          </div>
          {useCustomSystem && (
            <textarea
              value={customSystem}
              onChange={(e) => setCustomSystem(e.target.value)}
              placeholder="Wpisz system prompt (np. instrukcję dla asystenta)..."
              style={{
                width: "100%",
                minHeight: 80,
                padding: 8,
                borderRadius: 8,
                border: "1px solid #ebe7e5ff",
              }}
            />
          )}
        </>
      )}
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <div style={{ fontWeight: 700, fontSize: 18 }}>AsysChat</div>
        <div style={styles.info}>
          {/* Wiadomości są lokalne — klucz API używa backendu (opis w README) */}
        </div>
      </div>

      <div style={styles.messages} ref={messagesRef} aria-live="polite">
        {messages.map((m, idx) => (
          <div
            key={idx}
            style={
              m.role === "user" ? styles.messageUser : styles.messageAssistant
            }
          >
            {m.text}
          </div>
        ))}

        {loading && <div style={styles.messageAssistant}>Piszę...</div>}
      </div>

      {error && <div style={{ color: "#d5330bff" }}>Błąd: {error}</div>}

      <form style={styles.form} onSubmit={sendMessage}>
        <input
          style={styles.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Napisz wiadomość..."
          aria-label="Wiadomość"
        />
        <button style={styles.button} type="submit" disabled={loading}>
          Wyślij
        </button>
      </form>
    </div>
  );
};

export default ChatWindow;

import React, { useState } from "react";

function fetchJson(path) {
  return fetch(path).then((r) => r.json());
}

export default function ParticipantViewer() {
  const [subject, setSubject] = useState("2");
  const [data, setData] = useState(null);
  const [params, setParams] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const q = new URLSearchParams();
      q.set("allow_unpickle", "1");
      if (params) q.set("params", params);
      const res = await fetch(`/participant/${subject}?` + q.toString());
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`${res.status} ${txt}`);
      }
      const j = await res.json();
      setData(j);
    } catch (e) {
      setError(e.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <label style={{fontWeight:'600'}}>Subject id:</label>
        <input
          placeholder="np. 2"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          style={{ width: 80 }}
          aria-label="subject-id"
        />
        <label style={{fontWeight:'600'}}>Params (e.g. TEMP:100,EDA):</label>
        <input
          placeholder="TEMP:100,EDA"
          value={params}
          onChange={(e) => setParams(e.target.value)}
          style={{ width: 200 }}
          aria-label="params"
        />
        <button onClick={load}>Load</button>
      </div>
      <div style={{marginTop:8, fontSize:12, color:'#555'}}>
        Jeśli nie widzisz pól powyżej, odśwież stronę (Ctrl+R) lub sprawdź konsolę przeglądarki (F12).
      </div>

      {loading && <p>Loading…</p>}
      {error && <div style={{ color: "red" }}>Error: {error}</div>}

      {data && (
        <div style={{ marginTop: 12 }}>
          <h3>{data.subject}</h3>
          <pre
            style={{
              whiteSpace: "pre-wrap",
              maxHeight: 400,
              overflow: "auto",
              background: "#f6f6f6",
              padding: 8,
            }}
          >
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

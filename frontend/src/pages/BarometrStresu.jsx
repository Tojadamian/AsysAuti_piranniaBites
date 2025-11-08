import React, { useEffect, useState, useRef } from "react";
import Screen from "../components/Screen";
import Header from "../components/Header";
import HeaderActionButton from "../components/HeaderActionButton";
import Footer from "../components/Footer";
import Icon from "../components/Icon";
import MetricCard from "../components/MetricCard";

const BarometrStresu = () => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]); // lokalna historia punktów score
  const pollRef = useRef(null);
  const fullDataRef = useRef(null); // cache for the large full response

  const fetchData = async () => {
    try {
      // guard przeciw nakładaniu się wywołań (chroni przed rekurencją/overlap)
      if (window.__baro_running) {
        console.warn(
          "Barometr: fetchData skipped because previous run still in progress"
        );
        return;
      }
      window.__baro_running = (window.__baro_running || 0) + 1;
      console.debug(
        "Barometr: fetchData start, runCount=",
        window.__baro_running
      );
      setLoading(true);
      // PROTOTYP: pobierz surowe sygnały uczestnika z lokalnego API
      // Używamy bezpośredniego endpointu wskazanego w README:
      // http://127.0.0.1:5000/participant/2?allow_unpickle=1&params=...
      const desiredParams = "EDA:500,HR:500,TEMP:500"; // próbkuj do 500 próbek (jeśli dostępne)
      // Jeśli nie pobraliśmy jeszcze pełnych danych — pobierz z full=1 (duży plik)
      let j = null;
      if (!fullDataRef.current) {
        const participantUrl = `http://127.0.0.1:5000/participant/2?allow_unpickle=1&params=${encodeURIComponent(
          desiredParams
        )}&full=1`;
        const res = await fetch(participantUrl);
        if (!res.ok)
          throw new Error(
            `Błąd HTTP ${res.status} przy pobieraniu ${participantUrl}`
          );
        j = await res.json();
        // cache full response to avoid re-downloading ~50MB files
        fullDataRef.current = j;
      } else {
        // fetch lightweight summary (no full arrays) to update score/state if available
        const participantUrlSmall = `http://127.0.0.1:5000/participant/2?allow_unpickle=1&params=${encodeURIComponent(
          desiredParams
        )}`;
        const res = await fetch(participantUrlSmall);
        if (!res.ok)
          throw new Error(
            `Błąd HTTP ${res.status} przy pobieraniu ${participantUrlSmall}`
          );
        j = await res.json();
      }

      // j is the response (full on first run, summary afterwards)
      // Aby uniknąć przechowywania bardzo dużego (i potencjalnie złożonego)
      // obiektu w stanie komponentu (co może powodować ukryte recursje w devtools),
      // zapisujemy tylko minimalne metadane. Surowe sygnały trzymamy tylko w
      // lokalnej zmiennej i przetwarzamy do historii.
      setData({ state: j.state, trend: j.trend, score: j.score });

      // Parsuj dostępne sygnały i wybierz pierwszy z listy preferowanych
      const signals = j.available_signals || j.available_signals || {};

      // Helper: próbuje wyciągnąć tablicę wartości z różnych struktur odpowiedzi
      const extractArray = (val) => {
        try {
          if (!val && val !== 0) return null;
          // jeśli wrapper full
          if (val && typeof val === "object" && (val.data || val.full)) {
            if (Array.isArray(val.data)) return val.data;
            if (Array.isArray(val.full)) return val.full;
            // jeśli full jest obiektem lokalizacji np. {chest: {TEMP: [...]}}
            if (val.full && typeof val.full === "object") {
              // spróbuj znaleźć najpierw listę w wartościach
              for (const k of Object.keys(val.full)) {
                const v = val.full[k];
                if (Array.isArray(v)) return v;
              }
            }
          }
          if (Array.isArray(val)) return val;
          // jeżeli to obiekt z localisation->channels
          if (typeof val === "object") {
            for (const k of Object.keys(val)) {
              const v = val[k];
              if (Array.isArray(v)) return v;
            }
          }
          return null;
        } catch (e) {
          return null;
        }
      };

      // preferowane kanały (kolejność próbkowania)
      const preferred = ["eda", "hr", "temp", "acc", "acc_x", "acc_y", "acc_z"];
      let chosen = null;

      // przeszukaj hierarchical structure: locations -> channels
      for (const locKey of Object.keys(signals || {})) {
        const locVal = signals[locKey];
        // jeżeli to obiekt zawierający 'full'
        const candidateObj = locVal && locVal.full ? locVal.full : locVal;
        if (candidateObj && typeof candidateObj === "object") {
          for (const chName of Object.keys(candidateObj)) {
            const arr = extractArray(candidateObj[chName]);
            if (!arr) continue;
            const lname = String(chName).toLowerCase();
            // jeśli nazwa kanału w preferred -> wybierz
            for (const p of preferred) {
              if (lname.includes(p)) {
                chosen = { name: chName, values: arr };
                break;
              }
            }
            if (chosen) break;
          }
        }
        if (chosen) break;
      }

      // fallback: jeśli nie znaleziono w strukturze - spróbuj prostą detekcję
      if (!chosen) {
        // flatten and try to find any array
        for (const locKey of Object.keys(signals || {})) {
          const arr = extractArray(signals[locKey]);
          if (arr) {
            chosen = { name: locKey, values: arr };
            break;
          }
        }
      }

      if (!chosen) {
        setError(
          "Nie znaleziono odpowiednich sygnałów w odpowiedzi uczestnika."
        );
        setHistory([]);
        return;
      }

      // Znormalizuj wartości wybranego kanału na 0..100 (min->0, max->100)
      // Najpierw spróbuj spłaszczyć pojedyncze zagnieżdżone tablice jak [[5.25]] -> 5.25
      const unwrap = (v) => {
        try {
          if (v == null) return null;
          if (Array.isArray(v)) {
            if (v.length === 0) return null;
            const first = v[0];
            if (Array.isArray(first)) return first.length ? first[0] : null;
            return first;
          }
          return v;
        } catch (e) {
          return null;
        }
      };

      const vals = chosen.values
        .map((v) => unwrap(v))
        .map((v) => (v == null ? null : Number(v)))
        .filter((v) => !Number.isNaN(v));
      if (!vals.length) {
        setError("Wybrany kanał nie zawiera danych liczbowych.");
        setHistory([]);
        return;
      }
      const min = Math.min(...vals);
      const max = Math.max(...vals);
      const range = max - min || 1;

      // downsample do maksymalnie 100 punktów dla wykresu
      const maxPoints = 100;
      const step = Math.max(1, Math.floor(vals.length / maxPoints));
      const sampled = vals.filter((_, i) => i % step === 0).slice(-maxPoints);
      const mapped = sampled.map((v) => Math.round(((v - min) / range) * 100));

      setHistory(mapped.map((s) => ({ score: s })));
      setError(null);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
      // release guard
      try {
        window.__baro_running = Math.max(0, (window.__baro_running || 1) - 1);
      } catch (e) {}
      console.debug(
        "Barometr: fetchData end, runCount=",
        window.__baro_running
      );
    }
  };

  useEffect(() => {
    // Każda kopia komponentu otrzymuje unikalny id — to pomaga debugować nakładanie się
    const instanceId = `${Date.now()}-${Math.floor(Math.random() * 100000)}`;
    window.__baro_instances = (window.__baro_instances || 0) + 1;
    console.debug(
      `Barometr[${instanceId}]: mount, instances=`,
      window.__baro_instances
    );

    // Jeżeli globalny scheduler już działa pod innym ownerem, nie uruchamiamy kolejnego.
    if (
      window.__baro_global_owner &&
      window.__baro_global_owner !== instanceId
    ) {
      console.debug(
        `Barometr[${instanceId}]: detected existing global owner=`,
        window.__baro_global_owner,
        " — skipping scheduler start"
      );
      return () => {
        window.__baro_instances = Math.max(
          0,
          (window.__baro_instances || 1) - 1
        );
        console.debug(
          `Barometr[${instanceId}]: unmount, instances=`,
          window.__baro_instances
        );
      };
    }

    // ustawiamy właściciela globalnego scheduler'a
    window.__baro_global_owner = instanceId;

    let isMounted = true;
    // zamiast setInterval używamy rekurencyjnego setTimeout — bezpieczniejsze jeśli fetch trwa dłużej
    const run = async () => {
      if (!isMounted) return;
      try {
        await fetchData();
      } catch (err) {
        console.error(`Barometr[${instanceId}] run error:`, err);
      }
      if (!isMounted) return;
      // zaplanuj kolejne uruchomienie tylko jeśli nadal jesteśmy właścicielem
      if (window.__baro_global_owner === instanceId) {
        pollRef.current = setTimeout(run, 5000);
      }
    };
    // start
    run();

    return () => {
      isMounted = false;
      // jeśli jesteśmy właścicielem globalnym, zdejmij ownera i wyczyść timer
      if (window.__baro_global_owner === instanceId) {
        window.__baro_global_owner = null;
      }
      if (pollRef.current) clearTimeout(pollRef.current);
      window.__baro_instances = Math.max(0, (window.__baro_instances || 1) - 1);
      console.debug(
        `Barometr[${instanceId}]: unmount, instances=`,
        window.__baro_instances
      );
    };
  }, []);

  // prosty komponent wskaźnika (gauge) bazujący na score 0-100
  const Gauge = ({ value }) => {
    const v = Math.max(0, Math.min(100, value || 0));
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 8,
        }}
      >
        <div
          style={{
            width: 160,
            height: 160,
            borderRadius: "50%",
            background: "conic-gradient(#e5e7eb 0deg, #e5e7eb 360deg)",
            position: "relative",
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: 0,
              borderRadius: "50%",
              background: `conic-gradient(#29b433 ${v * 3.6}deg, #e5e7eb ${
                v * 3.6
              }deg 360deg)`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
              fontSize: 28,
              color: "#222",
            }}
          >
            {v}%
          </div>
        </div>
        <div style={{ fontSize: 14, color: "#555" }}>Poziom stresu</div>
      </div>
    );
  };

  return (
    <Screen padded={true} maxWidth={420} backgroundColor="#f8fbff">
      <Header>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            width: "100%",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Icon style={{ width: 20, height: 20, fill: "#29b433" }} />
            <div
              style={{
                fontWeight: 700,
                fontSize: 20,
                fontFamily: "Poppins, Arial, sans-serif",
              }}
            >
              AsysAuti
            </div>
          </div>
          <div>
            <HeaderActionButton
              style={{ marginRight: 12 }}
              onClick={() => (window.location.hash = "#/viewer")}
            />
          </div>
        </div>
      </Header>

      <div style={{ paddingTop: 72 }}>
        <div style={{ textAlign: "center", marginTop: 8 }}>
          <div
            style={{
              fontSize: 20,
              fontWeight: 700,
              fontFamily: "Poppins, Arial, sans-serif",
            }}
          >
            {data ? `Stan: ${data.state}` : "Aktualny stan"}
          </div>
          <div style={{ marginTop: 8, color: "#333", fontSize: 14 }}>
            {data && data.trend
              ? `Trend: ${data.trend}`
              : "Przegląd poziomu stresu na podstawie dostępnych sygnałów"}
          </div>
        </div>

        <div style={{ marginTop: 16, display: "grid", gap: 12 }}>
          <div
            style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}
          >
            <MetricCard
              text={
                data && data.score !== null
                  ? `Poziom: ${data.score}%`
                  : loading
                  ? "Ładowanie..."
                  : "Poziom: --"
              }
              onClick={() => fetchData()}
            />
            <MetricCard
              text={data && data.trend ? `Trend: ${data.trend}` : "Trend: --"}
              onClick={() => fetchData()}
            />
          </div>

          <div
            style={{
              marginTop: 8,
              background: "#ffffff",
              borderRadius: 12,
              padding: 12,
              boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 16,
            }}
          >
            <Gauge value={data && data.score !== null ? data.score : 0} />
            <div style={{ fontWeight: 700, marginTop: 4 }}>
              Historia (ostatnie okna)
            </div>
            <div style={{ width: "100%", height: 120 }}>
              {/* Prosty wykres liniowy SVG */}
              {history.length > 1 ? (
                <svg viewBox="0 0 200 100" width="100%" height="100%">
                  <polyline
                    fill="none"
                    stroke="#29b433"
                    strokeWidth="2"
                    points={history
                      .map((h, i) => {
                        const x = (i / (history.length - 1)) * 200;
                        const y = 100 - (h.score / 100) * 90 - 5; // margines 5
                        return `${x},${y}`;
                      })
                      .join(" ")}
                  />
                  {history.map((h, i) => {
                    const x = (i / (history.length - 1)) * 200;
                    const y = 100 - (h.score / 100) * 90 - 5;
                    return (
                      <circle key={i} cx={x} cy={y} r={3} fill="#29b433" />
                    );
                  })}
                </svg>
              ) : (
                <div style={{ color: "#666", fontSize: 12 }}>
                  Brak wystarczających danych do historii.
                </div>
              )}
            </div>
            {error && (
              <div style={{ color: "#b91c1c", fontSize: 12 }}>
                Błąd: {error}
              </div>
            )}
            <div style={{ fontSize: 11, color: "#555" }}>
              Dane odświeżane co 5s • źródło:
              http://127.0.0.1:5000/participant/2
            </div>
          </div>
        </div>
      </div>

      <Footer />
    </Screen>
  );
};

export default BarometrStresu;

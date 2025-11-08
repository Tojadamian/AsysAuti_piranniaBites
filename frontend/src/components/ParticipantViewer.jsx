import React, { useState } from "react";

function fetchJson(path) {
  return fetch(path).then((r) => {
    if (!r.ok) {
      return r.text().then((t) => {
        throw new Error(`${r.status} ${t}`);
      });
    }
    return r.json();
  });
}

function normalizeSubjectToken(token) {
  if (!token && token !== 0) return "";
  const s = String(token).trim();
  if (!s) return "";
  if (s.toUpperCase().startsWith("S") && /^\d+$/.test(s.slice(1)))
    return s.slice(1);
  if (/^\d+$/.test(s)) return s;
  return s; // fallback: return whatever user selected
}

export default function ParticipantViewer() {
  const [subject, setSubject] = useState("2");
  const [selectedLocations, setSelectedLocations] = useState(["chest"]);
  const [data, setData] = useState(null);
  const [indicatorMatches, setIndicatorMatches] = useState({});
  const [params, setParams] = useState("");
  const [rangeSpec, setRangeSpec] = useState("");
  const [dataMode, setDataMode] = useState("sample"); // 'sample' or 'full'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [subjects, setSubjects] = useState([]);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState(null);
  const [subjectSources, setSubjectSources] = useState({}); // subject -> source file
  const [openLocations, setOpenLocations] = useState({});
  const [rangeError, setRangeError] = useState(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      if (!subject) throw new Error("Choose a subject first");
      if (rangeError) throw new Error("Invalid range format");
      const q = new URLSearchParams();
      q.set("allow_unpickle", "1");
      if (rangeSpec) q.set("range", rangeSpec);
      if (params) q.set("params", params);
      if (dataMode === "full") q.set("full", "1");
      const res = await fetch(`/api/participant/${subject}?` + q.toString());
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

  const canonicalIndicators = {
    respiration: ["resp", "breath"],
    acceleration: ["accel", "acceleration", "acc"],
    temperature: ["temp", "temperature", "skin_temp"],
    EMG: ["emg"],
    EDA: ["eda", "galv"],
    ECG: ["ecg"],
    HR: ["hr", "heart", "bvp"],
    BVP: ["bvp", "blood_volume", "bloodvolume"],
  };

  function findIndicatorsInData(useAllLocations = false) {
    if (!data || !data.available_signals) return {};
    // collect channel names across locations (or only selectedLocations)
    const chans = new Set();
    const locs = useAllLocations
      ? Object.keys(data.available_signals)
      : selectedLocations;
    locs.forEach((loc) => {
      const val = data.available_signals[loc];
      if (!val) return;
      if (typeof val === "object") {
        Object.keys(val).forEach((k) => chans.add(k));
      }
    });

    const lower = Array.from(chans).map((c) => ({
      raw: c,
      low: String(c).toLowerCase(),
    }));
    const matches = {};
    Object.entries(canonicalIndicators).forEach(([name, patterns]) => {
      matches[name] = [];
      patterns.forEach((p) => {
        lower.forEach(({ raw, low }) => {
          if (low.includes(p)) {
            if (!matches[name].includes(raw)) matches[name].push(raw);
          }
        });
      });
    });
    return matches;
  }

  const handleFindIndicators = (useAll = false) => {
    const found = findIndicatorsInData(useAll);
    setIndicatorMatches(found);
  };

  const useMatchedAsParams = (indicatorName) => {
    const arr = indicatorMatches[indicatorName] || [];
    if (!arr.length) return;
    // append to params (comma separated)
    const cur = params
      ? params
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
      : [];
    const merged = Array.from(new Set([...cur, ...arr]));
    setParams(merged.join(","));
  };

  const fetchSubjects = async () => {
    setListLoading(true);
    setListError(null);
    try {
      // ask backend to search all candidate dirs
      const j = await fetchJson(
        `/api/participants?allow_unpickle=1&search_all=1`
      );
      const byFile = j.subjects_by_file || {};
      const flat = [];
      const sources = {};
      Object.entries(byFile).forEach(([file, list]) => {
        if (Array.isArray(list)) {
          list.forEach((s) => {
            const ss = String(s);
            flat.push(ss);
            // prefer first seen file as source
            if (!sources[ss]) sources[ss] = file;
          });
        }
      });
      // unique & sort
      const unique = Array.from(new Set(flat)).sort();
      setSubjects(unique);
      setSubjectSources(sources);
      if (unique.length === 1) {
        setSubject(normalizeSubjectToken(unique[0]));
      }
    } catch (e) {
      setListError(e.message);
      setSubjects([]);
    } finally {
      setListLoading(false);
    }
  };

  // validate range on change: allow formats like "start:end" where start/end may be empty or integers
  const onRangeChange = (v) => {
    setRangeSpec(v);
    if (!v) {
      setRangeError(null);
      return;
    }
    const ok = /^\d*:\d*$/.test(v.trim());
    setRangeError(ok ? null : "Use start:end with integers, e.g. 23:500");
  };

  return (
    <div>
      <div
        style={{
          display: "flex",
          gap: 8,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        {/* Subject id input removed — selection via dropdown. */}
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <label style={{ fontWeight: "600" }}>Locations:</label>
          <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <input
              type="checkbox"
              name="location"
              value="chest"
              checked={selectedLocations.includes("chest")}
              onChange={(e) => {
                const checked = e.target.checked;
                setSelectedLocations((prev) => {
                  if (checked) return Array.from(new Set([...prev, "chest"]));
                  return prev.filter((x) => x !== "chest");
                });
              }}
              aria-label="loc-chest"
            />
            chest
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <input
              type="checkbox"
              name="location"
              value="wrist"
              checked={selectedLocations.includes("wrist")}
              onChange={(e) => {
                const checked = e.target.checked;
                setSelectedLocations((prev) => {
                  if (checked) return Array.from(new Set([...prev, "wrist"]));
                  return prev.filter((x) => x !== "wrist");
                });
              }}
              aria-label="loc-wrist"
            />
            wrist
          </label>
        </div>

        <label style={{ fontWeight: "600" }}>Lista subjectów:</label>
        <button onClick={fetchSubjects} aria-label="list-subjects">
          {listLoading ? "Loading…" : "List subjects"}
        </button>

        <select
          aria-label="subjects-select"
          value={subjects.includes("S" + subject) ? "S" + subject : subject}
          onChange={(e) => {
            const raw = e.target.value;
            const normalized = normalizeSubjectToken(raw);
            setSubject(normalized);
          }}
          style={{ minWidth: 160 }}
        >
          <option value="">— select —</option>
          {subjects.map((s) => (
            <option key={s} value={s}>
              {s}
              {subjectSources[s] ? ` — ${subjectSources[s]}` : ""}
            </option>
          ))}
        </select>

        <label style={{ fontWeight: "600" }}>Params (e.g. TEMP:100,EDA):</label>
        <input
          placeholder="TEMP:100,EDA"
          value={params}
          onChange={(e) => setParams(e.target.value)}
          style={{ width: 200 }}
          aria-label="params"
        />
        <label style={{ fontWeight: "600" }}>Range (start:end):</label>
        <input
          placeholder="23:500"
          value={rangeSpec}
          onChange={(e) => onRangeChange(e.target.value)}
          style={{ width: 100 }}
          aria-label="range-spec"
        />
        {rangeError && (
          <div style={{ color: "orange", fontSize: 12, marginLeft: 8 }}>
            {rangeError}
          </div>
        )}
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <label style={{ fontWeight: 600 }}>Mode:</label>
          <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <input
              type="radio"
              name="data-mode"
              value="sample"
              checked={dataMode === "sample"}
              onChange={() => setDataMode("sample")}
              aria-label="mode-sample"
            />
            sample
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <input
              type="radio"
              name="data-mode"
              value="full"
              checked={dataMode === "full"}
              onChange={() => setDataMode("full")}
              aria-label="mode-full"
            />
            full
          </label>
        </div>
        <div style={{ fontSize: 12, color: "#666", marginLeft: 8 }}>
          (server may auto-include full slice if slice ≤{" "}
          {"MAX_FULL_IN_SUMMARY (server-side)"})
        </div>
        <button
          onClick={load}
          disabled={!subject || !!rangeError}
          title={
            !subject
              ? "Select a subject"
              : rangeError
              ? rangeError
              : "Load data"
          }
        >
          Load
        </button>
        <button
          onClick={() => handleFindIndicators(false)}
          title="Search indicators in the selected location"
          style={{ marginLeft: 6 }}
        >
          Find indicators (location)
        </button>
        <button
          onClick={() => handleFindIndicators(true)}
          title="Search indicators across all locations"
          style={{ marginLeft: 6 }}
        >
          Find indicators (all)
        </button>
      </div>

      <div style={{ marginTop: 8, fontSize: 12, color: "#555" }}>
        Jeśli nie widzisz pól powyżej, odśwież stronę (Ctrl+R) lub sprawdź
        konsolę przeglądarki (F12).
      </div>

      {listError && (
        <div style={{ color: "orange" }}>List error: {listError}</div>
      )}
      {loading && <p>Loading…</p>}
      {error && <div style={{ color: "red" }}>Error: {error}</div>}

      {data && (
        <div style={{ marginTop: 12 }}>
          <h3>{data.subject}</h3>
          {/* If available_signals contains any selected location, show those */}
          {data.available_signals &&
          Array.isArray(selectedLocations) &&
          selectedLocations.some((loc) => data.available_signals[loc]) ? (
            <div>
              {selectedLocations.map((loc) =>
                data.available_signals[loc] ? (
                  <div key={loc} style={{ marginBottom: 12 }}>
                    <div
                      style={{ display: "flex", alignItems: "center", gap: 8 }}
                    >
                      <h4 style={{ margin: 0 }}>Location: {loc}</h4>
                      <button
                        onClick={() =>
                          setOpenLocations((p) => ({ ...p, [loc]: !p[loc] }))
                        }
                        style={{ fontSize: 12 }}
                      >
                        {openLocations[loc] ? "Hide" : "Show"}
                      </button>
                    </div>
                    {openLocations[loc] && (
                      <pre
                        style={{
                          whiteSpace: "pre-wrap",
                          maxHeight: 400,
                          overflow: "auto",
                          background: "#f6f6f6",
                          padding: 8,
                        }}
                      >
                        {JSON.stringify(data.available_signals[loc], null, 2)}
                      </pre>
                    )}
                  </div>
                ) : null
              )}
            </div>
          ) : (
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
          )}
        </div>
      )}

      {/* Indicator matches and quick actions */}
      {data && Object.keys(indicatorMatches || {}).length > 0 && (
        <div style={{ marginTop: 12 }}>
          <h4>Indicator matches</h4>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {Object.entries(indicatorMatches).map(([name, arr]) => (
              <div
                key={name}
                style={{ minWidth: 180, border: "1px solid #eee", padding: 8 }}
              >
                <strong>{name}</strong>
                <div style={{ fontSize: 12, color: "#444", marginTop: 6 }}>
                  {arr.length ? (
                    arr.map((c) => (
                      <div
                        key={c}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                        }}
                      >
                        <span>{c}</span>
                      </div>
                    ))
                  ) : (
                    <em style={{ color: "#999" }}>not found</em>
                  )}
                </div>
                <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                  <button
                    onClick={() => useMatchedAsParams(name)}
                    disabled={!arr.length}
                  >
                    Add to params
                  </button>
                  <button
                    onClick={() => {
                      const arr2 = indicatorMatches[name] || [];
                      if (!arr2.length) return;
                      setParams(arr2.join(","));
                      // auto-load
                      setTimeout(() => load(), 50);
                    }}
                    disabled={!arr.length}
                  >
                    Load these
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

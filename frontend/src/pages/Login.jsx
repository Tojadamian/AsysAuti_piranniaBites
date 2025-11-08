import React, { useState } from "react";
import Icon from "../components/Icon";
import Text from "../components/Text";
import Button from "../components/Button";
import LoginInput from "../components/LoginInput";

const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [datasetError, setDatasetError] = useState(null);

  const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:5000";

  const onSubmit = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    setLoading(true);

    const candidate = (email || "").trim().toUpperCase();
    // Jeśli użytkownik wpisze S2 lub S3 w pole email – ustaw katalog danych przez backend
    if (["S2", "S3"].includes(candidate)) {
      try {
        setDatasetError(null);
        const resp = await fetch(`${API_BASE}/data_dir?dir=${candidate}`);
        const data = await resp.json();
        if (resp.ok) {
          setDatasetInfo(`Wybrano katalog danych: ${data.data_dir}`);
          // zapamiętaj wybór lokalnie (opcjonalne wykorzystanie w innych częściach frontendu)
          try {
            localStorage.setItem("datasetDir", candidate);
          } catch {}
        } else {
          setDatasetError(data.error || "Błąd ustawiania katalogu danych");
        }
      } catch (err) {
        setDatasetError("Błąd sieci podczas ustawiania katalogu danych");
      }
    }

    setTimeout(() => {
      setLoading(false);
      window.location.hash = "#/dashboard";
    }, 700);
  };

  return (
    <div
      style={{
        width: "100%",
        maxWidth: 420,
        margin: "0 auto",
        padding: 24,
        boxSizing: "border-box",
      }}
    >
      <div
        style={{ display: "flex", justifyContent: "center", marginBottom: 8 }}
      >
        <div style={{ width: 150 }}>
          <Icon />
        </div>
      </div>

      <div style={{ textAlign: "center", marginBottom: 18 }}>
        <Text text="Logowanie" />
      </div>

      <form onSubmit={onSubmit}>
        <LoginInput
          label="Email"
          placeholder="user@example.com (lub S2 / S3 aby wybrać katalog danych)"
          value={email}
          onChange={setEmail}
        />
        <LoginInput
          label="Hasło"
          type="password"
          placeholder="Wpisz hasło"
          value={password}
          onChange={setPassword}
        />

        <div style={{ marginTop: 12 }}>
          <Button
            type="submit"
            label={loading ? "Logowanie" : "Zaloguj"}
            style={{ maxWidth: "100%" }}
          />
        </div>
        {datasetInfo && (
          <div style={{ marginTop: 12, fontSize: 13, color: "#0a7d28" }}>
            {datasetInfo}
          </div>
        )}
        {datasetError && (
          <div style={{ marginTop: 12, fontSize: 13, color: "#b30000" }}>
            {datasetError}
          </div>
        )}
      </form>

      <div
        style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 18 }}
      >
        <div style={{ flex: 1, height: 1, background: "#e6e6e6" }} />
        <div style={{ color: "#666", fontSize: 14 }}>lub</div>
        <div style={{ flex: 1, height: 1, background: "#e6e6e6" }} />
      </div>

      <div style={{ display: "flex", gap: 12, marginTop: 14 }}>
        <div style={{ flex: "1 1 48%" }}>
          <Button
            label="Google"
            onClick={() => alert("Google login (stub)")}
            style={{ maxWidth: "100%" }}
          />
        </div>
        <div style={{ flex: "1 1 48%" }}>
          <Button
            label="Facebook"
            onClick={() => alert("Facebook login (stub)")}
            style={{ maxWidth: "100%" }}
          />
        </div>
      </div>

      <div style={{ marginTop: 18 }}>
        <Button
          label="Zarejestruj się"
          onClick={() => alert("Register (stub)")}
          style={{ maxWidth: "100%" }}
        />
      </div>
    </div>
  );
};

export default Login;

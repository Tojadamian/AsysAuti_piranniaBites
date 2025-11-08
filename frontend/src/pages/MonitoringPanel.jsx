import React from "react";
import Screen from "../components/Screen";
import Card from "../components/Card";
import Icon from "../components/Icon";
import Header from "../components/Header";
import HeaderActionButton from "../components/HeaderActionButton";
import Footer from "../components/Footer";
import MonitoringItem from "../components/MonitoringItem";

const MonitoringPanel = () => {
  const items = [
    "Barometr stresu",
    "Wewnętrzna równowaga",
    "Poziom napięcia",
    "Ciepło spokoju",
    "Napięcie ciała",
    "Aktywność ruchowa",
    "Siła pulsu",
    "Tempo oddechu",
    "Rytm serca (R-R)",
  ];

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
              onClick={() => (window.location.hash = "/viewer")}
            />
          </div>
        </div>
      </Header>

      {/* zawartość strony przesunięta w dół by nie zasłaniała przez fixed header */}
      <div style={{ paddingTop: 72 }}>
        <div style={{ textAlign: "center", marginTop: 8 }}>
          <div
            style={{
              fontSize: 20,
              fontWeight: 700,
              fontFamily: "Poppins, Arial, sans-serif",
            }}
          >
            Wykresy porównawcze
          </div>
          <div style={{ marginTop: 8, color: "#333", fontSize: 14 }}>
            Sprawdź gotowe wizualizacje lub zapytaj o nowe
          </div>
        </div>

        <div style={{ marginTop: 16, display: "grid", gap: 12 }}>
          {(() => {
            const images = [
              "https://assets.api.uizard.io/api/cdn/stream/c1f793ad-f503-422a-8943-c9a31f16bd62.png",
              "https://assets.api.uizard.io/api/cdn/stream/25824ab5-7ab4-4094-a05d-38852a89653c.png",
              "https://assets.api.uizard.io/api/cdn/stream/97a91a92-aa0e-4db6-88d3-b364d858e6c0.png",
              "https://assets.api.uizard.io/api/cdn/stream/f7279495-0f95-40b7-8299-0f46ad37815e.png",
              "https://assets.api.uizard.io/api/cdn/stream/5f93308b-327b-4561-ac83-5181371129df.png",
              "https://assets.api.uizard.io/api/cdn/stream/0d7d9032-c3e9-421f-a2b3-f51568f08744.png",
              "https://assets.api.uizard.io/api/cdn/stream/8a885dce-4625-499e-af55-4e5b7ec601c2.png",
              "https://assets.api.uizard.io/api/cdn/stream/b77a571d-20e6-42bf-b4dd-01fb10c69639.png",
              "https://assets.api.uizard.io/api/cdn/stream/d277fd9a-ceb2-4b65-a586-6b8c72f92c71.png",
            ];

            return items.map((t, idx) => (
              <MonitoringItem
                key={t}
                title={t}
                img={images[idx] || images[0]}
                onClick={() =>
                  t === "Barometr stresu"
                    ? (window.location.hash = "#/barometr-stresu")
                    : console.log(`Clicked ${t}`)
                }
                isHighlighted={false}
              />
            ));
          })()}
        </div>
      </div>

      {/* stopka na dole ekranu */}
      <Footer />
    </Screen>
  );
};

export default MonitoringPanel;

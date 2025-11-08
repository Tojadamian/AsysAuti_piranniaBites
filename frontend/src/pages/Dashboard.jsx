import React from "react";
import Screen from "../components/Screen";
import Text from "../components/Text";
import Card from "../components/Card";
import Icon from "../components/Icon";
import IconMonitor from "../components/IconMonitor";
import IconUser from "../components/IconUser";
import IconPeople from "../components/IconPeople";
import IconSettings from "../components/IconSettings";
import Header from "../components/Header";

const StatRow = ({ labelLeft, labelRight, percent, color = "#29b433" }) => {
  return (
    <div style={{ marginBottom: 12 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 6,
        }}
      >
        <div style={{ color: "rgba(3,3,3,0.8)", fontSize: 13 }}>
          {labelLeft}
        </div>
        <div style={{ color: "rgba(3,3,3,0.8)", fontSize: 13 }}>
          {labelRight}
        </div>
      </div>
      <div
        style={{
          width: "100%",
          height: 10,
          background: "#fff",
          borderRadius: 999,
        }}
      >
        <div
          style={{
            width: `${percent}%`,
            height: "100%",
            background: color,
            borderRadius: 999,
          }}
        />
      </div>
    </div>
  );
};

const MenuItem = ({
  IconComponent,
  iconProps = {},
  text = "Item",
  onClick,
}) => (
  <button
    type="button"
    className="menu-item"
    onClick={onClick}
    style={{
      display: "flex",
      alignItems: "center",
      gap: 12,
      background: "#dcdcdc",
      padding: 16,
      borderRadius: 12,
      border: "none",
      width: "100%",
      cursor: "pointer",
      textAlign: "left",
    }}
  >
    <div style={{ width: 32, height: 32 }}>
      {IconComponent ? (
        <IconComponent {...iconProps} />
      ) : (
        <Icon style={{ width: 32, height: 32, fill: "#29b433" }} />
      )}
    </div>
    <div
      style={{
        flex: 1,
        fontSize: 18,
        fontFamily: "Poppins, Arial, sans-serif",
      }}
    >
      {text}
    </div>
    <div style={{ color: "#666" }}>›</div>
  </button>
);

const Dashboard = () => {
  return (
    <Screen padded={true} maxWidth={420} backgroundColor="#f8fbff">
      <Header>
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
      </Header>

      {/* zawartość strony przesunięta w dół by nie zasłaniała przez fixed header */}
      <div style={{ paddingTop: 72 }}>
        <div style={{ textAlign: "center", marginTop: 8 }}>
          <div
            style={{
              fontSize: 24,
              fontWeight: 700,
              fontFamily: "Poppins, Arial, sans-serif",
            }}
          >
            Witamy w AsysAuti
          </div>
          <div style={{ marginTop: 8, color: "#333", fontSize: 16 }}>
            Monitoruj poziomy stresu i stany emocjonalne z łatwością
          </div>
        </div>

        <div style={{ marginTop: 20 }}>
          <Card
            style={{
              backgroundColor: "#ffffff",
              boxShadow: "0 8px 20px rgba(0,0,0,0.06)",
            }}
          >
            <div style={{ padding: 20 }}>
              <div
                style={{
                  textAlign: "center",
                  marginBottom: 8,
                  fontWeight: 600,
                }}
              >
                Codzienne spostrzeżenia Asystenta AI
              </div>
              <StatRow
                labelLeft="Poziom stresu"
                labelRight="Umiarkowany stres"
                percent={78}
                color="#29b433"
              />
              <StatRow
                labelLeft="Stan emocjonalny"
                labelRight="Spokój"
                percent={25}
                color="#cfeee0"
              />
              <StatRow
                labelLeft="Niepokój"
                labelRight="Niski"
                percent={45}
                color="#bfead1"
              />
              <StatRow
                labelLeft="Relaksacja"
                labelRight="Wysoki"
                percent={12}
                color="#29b433"
              />
            </div>
          </Card>
        </div>

        <div style={{ marginTop: 18, display: "grid", gap: 12 }}>
          <MenuItem
            IconComponent={IconMonitor}
            text="Panel monitorowania"
            onClick={() => (window.location.hash = "/monitoring")}
            iconProps={{ fill: "#29b433", width: 28, height: 28 }}
          />
          <MenuItem
            IconComponent={IconUser}
            text="Profil"
            iconProps={{ fill: "#29b433", width: 28, height: 28 }}
          />
          <MenuItem
            IconComponent={IconPeople}
            text="Zarządzaj emocjami"
            iconProps={{ fill: "#29b433", width: 28, height: 28 }}
          />
          <MenuItem
            IconComponent={IconSettings}
            text="Ustawienia"
            iconProps={{ fill: "#29b433", width: 28, height: 28 }}
          />
        </div>
      </div>
    </Screen>
  );
};

export default Dashboard;

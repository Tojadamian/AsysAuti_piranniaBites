import React, { useState } from "react"; // ✅ Added useState import
import Screen from "../components/Screen";
import Header from "../components/Header";
import Icon from "../components/Icon";
import Text from "../components/Text";
import Card from "../components/Card";
import Image from "../components/Image";
import IconP from "../components/IconPeople";
import Footer from "../components/Footer";
import InputField from "../components/InputField.jsx";

const StatRow = ({ labelLeft, labelRight, percent, color = "#29b433" }) => {
  return (
    <div style={{ marginBottom: 0 }}>
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

const Profile = () => {
  const [note, setNote] = useState(""); // ✅ React state for input

  return (
    <Screen padded={true} maxWidth={420} backgroundColor="#f8fbff">
      {/* Header */}
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

      {/* Page content */}
      <div
        style={{
          paddingTop: 20,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 20,
        }}
      >
        {/* Avatar + greeting */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 16,
            marginTop: 20,
          }}
        >
          <div style={{ width: 75, height: 75 }}>
            <Image
              src="/avatar.png"
              style={{ width: "100%", height: "100%", borderRadius: "50%" }}
            />
          </div>

          <div>
            <div
              style={{
                fontSize: 24,
                fontWeight: 700,
                fontFamily: "Poppins, Arial, sans-serif",
              }}
            >
              Hello, User!
            </div>
            <div style={{ marginTop: 4, color: "#333", fontSize: 16 }}>
              Welcome back to your profile
            </div>
          </div>
        </div>

        {/* Date cards */}
        <Card
          style={{
            width: "100%",
            backgroundColor: "#ffffff",
            boxShadow: "0 8px 20px rgba(0,0,0,0.06)",
            padding: 16,
            marginTop: 20,
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              gap: 12,
            }}
          >
            {[7, 8, 9, 10, 11].map((day) => (
              <div
                key={day}
                style={{
                  width: 50,
                  height: 50,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: 12,
                  backgroundColor: day === 9 ? "#c0c0c0" : "#ffffff",
                  boxShadow: "0 4px 10px rgba(0,0,0,0.1)",
                  fontWeight: 600,
                  fontSize: 18,
                }}
              >
                {day}
              </div>
            ))}
          </div>
        </Card>

        {/* Two horizontal cards */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 16,
            marginTop: 20,
          }}
        >
          {/* First card: text */}
          <Card
            style={{
              flex: 1,
              minWidth: "45%",
              height: 120,
              backgroundColor: "#ffffff",
              boxShadow: "0 8px 20px rgba(0,0,0,0.06)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 20,
              fontWeight: 600,
            }}
          >
            75 beats/second
          </Card>

          {/* Second card: image */}
          <Card
            style={{
              flex: 1,
              minWidth: "45%",
              height: 120,
              backgroundColor: "#ffffff",
              boxShadow: "0 8px 20px rgba(0,0,0,0.06)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Icon src="/.png" style={{ width: "80%", height: "80%" }} />
          </Card>
        </div>

        {/* Stats card */}
        <Card
          style={{
            backgroundColor: "#ffffff",
            boxShadow: "0 8px 20px rgba(0,0,0,0.06)",
            marginTop: 5,
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

      {/* ✅ Input Field + centered */}
      <div
        style={{
          marginTop: 20,
          width: "100%",
          display: "flex",
          justifyContent: "center",
        }}
      >
        <InputField
          text="Dodaj notatkę..."
          onChange={setNote} // ✅ connects InputField to note state
        />
      </div>

      {/* Optional: show current note below */}
      <div style={{ marginTop: 8, textAlign: "center", color: "#333" }}>
        <strong>Twoja notatka:</strong> {note}
      </div>

      <Footer />
    </Screen>
  );
};

export default Profile;

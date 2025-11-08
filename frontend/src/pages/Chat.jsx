import React from "react";
import Screen from "../components/Screen";
import Header from "../components/Header";
import HeaderActionButton from "../components/HeaderActionButton";
import Footer from "../components/Footer";
import ChatWindow from "../components/ChatWindow";
import Icon from "../components/Icon";

const Chat = () => {
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
        <ChatWindow />
      </div>

      <Footer />
    </Screen>
  );
};

export default Chat;

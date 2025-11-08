import React from "react";
import Image from "../components/Image";
import Text from "../components/Text";
import Button from "../components/Button";

const Home = () => {
  return (
    <div
      style={{
        fontFamily: "Arial, sans-serif",
        width: "100%",
        maxWidth: 720,
        margin: "0 auto",
        padding: 24,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 20,
        minHeight: "60vh",
        boxSizing: "border-box",
      }}
    >
      <div style={{ width: "100%", maxWidth: 360 }}>
        <Image />
      </div>
      <Text text="AsysAuti" />
      <div
        style={{
          width: "100%",
          maxWidth: 360,
          display: "flex",
          justifyContent: "center",
        }}
      >
        <Button
          label="Start"
          onClick={() => (window.location.hash = "#/login")}
        />
      </div>
      <div style={{ marginTop: 8 }}>
        <Button
          label="Przejdź do viewera"
          onClick={() => (window.location.hash = "#/viewer")}
        />
      </div>
    </div>
  );
};

export default Home;

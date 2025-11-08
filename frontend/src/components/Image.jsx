import React from "react";

const defaultProps = {
  image:
    "https://assets.api.uizard.io/api/cdn/stream/cf33fa9c-5027-45be-8558-7a36e4b36cfd.png",
};

const Image = (props) => {
  const src = props.image ?? defaultProps.image;
  return (
    <img
      src={src}
      alt={props.alt || "decorative"}
      style={{
        width: "100%",
        maxWidth: 360,
        height: "auto",
        borderRadius: 12,
        objectFit: "cover",
        display: "block",
      }}
    />
  );
};

export default Image;

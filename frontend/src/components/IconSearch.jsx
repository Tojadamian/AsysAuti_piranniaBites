import React from "react";

const IconSearch = ({ width = 20, height = 20, fill = "#29b433", style = {} }) => (
  <svg
    viewBox="0 0 512 512"
    width={width}
    height={height}
    style={style}
    fill={fill}
    xmlns="http://www.w3.org/2000/svg"
  >
    <path d="M505 442.7L405.3 343c28.4-34.9 45.7-79.3 45.7-127C451 96.5 354.5 0 232.5 0S14 96.5 14 216.1 110.5 432.2 232.5 432.2c47.7 0 92-17.3 127-45.7l99.7 99.7c4.5 4.5 10.6 6.9 16.9 6.9s12.4-2.3 17-6.9c9.3-9.4 9.3-24.6 0-34zM232.5 384c-92.8 0-168-75.2-168-167.9S139.7 48.2 232.5 48.2 400.5 123.4 400.5 216 325.3 384 232.5 384z"/>
  </svg>
);

export default IconSearch;

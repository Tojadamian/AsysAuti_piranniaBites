import React from 'react';

const styles = {
  ImageContainer: {
    top: '558px',
    left: '126px',
    width: '115px',
    height: '122px',
    borderRadius: '8px',
    backgroundImage: 'url(./image.png)',
    backgroundPosition: 'center center',
    backgroundSize: 'cover',
    backgroundRepeat: 'no-repeat',
  },
};

const defaultProps = {
  image: 'https://assets.api.uizard.io/api/cdn/stream/97a91a92-aa0e-4db6-88d3-b364d858e6c0.png',
}

const Image = (props) => {
  return (
    <div style={{
      ...styles.ImageContainer,
      ...(props.style || {}),
      backgroundImage: `url(${props.image ?? defaultProps.image})`,
    }} />
  );
};

export default Image;

import React from 'react';

const styles = {
  ImageContainer: {
    top: '1909px',
    left: '40px',
    width: '295px',
    height: '113px',
    borderRadius: '8px',
    backgroundImage: 'url(./image.png)',
    backgroundPosition: 'center center',
    backgroundSize: 'cover',
    backgroundRepeat: 'no-repeat',
  },
};

const defaultProps = {
  image: 'https://assets.api.uizard.io/api/cdn/stream/c1f793ad-f503-422a-8943-c9a31f16bd62.png',
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

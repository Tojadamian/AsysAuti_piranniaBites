import React from 'react';

const styles = {
  input: {
    width: '100%',
    boxSizing: 'border-box',
    padding: '12px 14px',
    borderRadius: 12,
    border: '1px solid #d3d3d8',
    fontSize: 16,
    outline: 'none',
    background: 'rgba(255,255,255,0.9)',
  },
  label: {
    display: 'block',
    fontSize: 14,
    marginBottom: 8,
    color: '#333',
    fontWeight: 600,
  },
  row: {
    width: '100%',
    marginBottom: 12,
  },
};

const LoginInput = ({ label, type = 'text', value, onChange, placeholder }) => {
  return (
    <div style={styles.row}>
      {label && <label style={styles.label}>{label}</label>}
      <input
        type={type}
        value={value}
        onChange={(e) => onChange && onChange(e.target.value)}
        placeholder={placeholder}
        style={styles.input}
      />
    </div>
  );
};

export default LoginInput;

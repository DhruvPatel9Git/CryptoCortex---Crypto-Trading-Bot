import React from 'react';
import { useNavigate } from 'react-router-dom';
import styles from '../styles/BackButton.module.css';  // We'll add this next

const BackButton = () => {
  const navigate = useNavigate();

  const handleBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate('/', { replace: true });
    }
  };

  return (
    <button className={styles.backButton} type="button" onClick={handleBack}>
      ⬅ Back
    </button>
  );
};

export default BackButton;

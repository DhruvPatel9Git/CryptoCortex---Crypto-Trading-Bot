import React, { useState } from 'react';
import axios from 'axios';
import { jwtDecode } from 'jwt-decode';
import { useLocation, useNavigate } from 'react-router-dom';
import BackButton from '../components/BackButton';
import styles from '../styles/Auth.module.css';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [msg, setMsg] = useState('');
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = location.state?.from || '/';

  const handleLogin = async () => {
    try {
      const res = await axios.post('http://localhost:8000/login', { username, password });
      const { access_token, refresh_token, token_type } = res.data;
      const decoded = jwtDecode(access_token);
      const user_id = decoded.sub;

      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);
      localStorage.setItem('token_type', token_type);
      localStorage.setItem('username', username);
      localStorage.setItem('user_id', user_id);

      setMsg('Logged in!');
      navigate(redirectTo, { replace: true });
    } catch (error) {
      if (error.response?.data?.detail) {
        setMsg(`${error.response.data.detail}`);
      } else {
        setMsg('Error connecting to server');
      }
    }
  };

  return (
    <div className={styles.authPage}>
      <div className={styles.authTop}>
        <BackButton />
      </div>

      <div className={styles.authContainer}>
        <div className={styles.authBox}>
          <h2>Login</h2>
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button className={styles.authButton} onClick={handleLogin}>Login</button>
          {msg && <p className={styles.authMessage}>{msg}</p>}
          <p className={styles.authLink}>Don't have an account? <a href="/register">Register</a></p>
        </div>
      </div>
    </div>
  );
};

export default Login;

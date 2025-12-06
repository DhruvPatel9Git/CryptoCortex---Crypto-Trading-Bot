import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { jwtDecode } from "jwt-decode";
import { useTheme } from "../context/ThemeContext";
import ThemeToggle from "../context/ThemeToggle";
import styles from "../styles/Navbar.module.css";

const isTokenExpired = (token) => {
  try {
    const decoded = jwtDecode(token);
    return decoded.exp * 1000 < Date.now();
  } catch (err) {
    return true;
  }
};

const getValidUsername = () => {
  const token = localStorage.getItem("access_token");
  if (!token || isTokenExpired(token)) return null;
  return localStorage.getItem("username");
};

const Navbar = () => {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const [username, setUsername] = useState(getValidUsername());

  // Listen for storage changes
  useEffect(() => {
    const handleStorageChange = () => {
      setUsername(getValidUsername());
    };
    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, []);

  useEffect(() => {
    setUsername(getValidUsername());
  }, []);

  const handleLogout = async () => {
    const token = localStorage.getItem("access_token");
    try {
      if (token && !isTokenExpired(token)) {
        await fetch(
          `https://cryptocortex-crypto-trading-bot-9.onrender.com/logout`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
          }
        );
      }
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      localStorage.clear();
      setUsername(null);
      navigate("/login");
    }
  };

  return (
    <nav
      className={`${styles.navbar} ${
        theme === "dark" ? styles.navbarDark : styles.navbarLight
      }`}
    >
      <div className={styles.navbarLeft}>
        <Link to="/" className={styles.logoLink}>
          <h2 className={styles.logoText}>CryptoCortex</h2>
        </Link>
        <ul className={styles.navLinks}>
          <li className={styles.navLinkItem}>
            <Link to="/">Home</Link>
          </li>
          <li className={styles.navLinkItem}>
            <Link to="/portfolio">Portfolio</Link>
          </li>
          <li className={styles.navLinkItem}>
            <Link to="/trade">Buy Crypto</Link>
          </li>
          <li className={styles.navLinkItem}>
            <Link to="/details">Market Dashboard</Link>
          </li>
        </ul>
      </div>

      <div className={styles.navbarRight}>
        <ThemeToggle />
        {username ? (
          <>
            <span className={styles.welcome}>
              👋 Welcome, <strong>{username}</strong>
            </span>
            <button className={styles.authButton} onClick={handleLogout}>
              Logout
            </button>
          </>
        ) : (
          <>
            <button
              className={styles.authButton}
              onClick={() => navigate("/login")}
            >
              Login
            </button>
            <button
              className={styles.authButton}
              onClick={() => navigate("/register")}
            >
              Register
            </button>
          </>
        )}
      </div>
    </nav>
  );
};

export default Navbar;

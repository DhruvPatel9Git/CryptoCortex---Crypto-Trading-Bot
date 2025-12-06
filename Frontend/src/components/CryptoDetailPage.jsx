import React, { useEffect, useState } from "react";
import axios from "axios";
import Select from "react-select";
import OrderBook from "../components/OrderBook";
import CryptoCandlesChart from "../components/CryptoCandlesChart";
import { BuySellTransferWidget } from "../components/BuySellTransferWidget";
import { useTheme } from "../context/ThemeContext";
import styles from "../styles/CryptoDetailPage.module.css";

const CryptoDetailPage = () => {
  const [symbols, setSymbols] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [currentPrice, setCurrentPrice] = useState(null);
  const [priceChange, setPriceChange] = useState(null);
  const { theme } = useTheme();

  useEffect(() => {
    const fetchSymbols = async () => {
      try {
        const res = await axios.get(
          "https://cryptocortex-crypto-trading-bot-9.onrender.com/cryptos/all"
        );
        const symbolOptions = res.data.map((s) => ({
          value: s.toLowerCase(),
          label: s.toUpperCase(),
        }));
        setSymbols(symbolOptions);
        setSelectedSymbol({
          value: res.data[0].toLowerCase(),
          label: res.data[0].toUpperCase(),
        });
      } catch (err) {
        console.error("Error fetching symbols:", err);
      }
    };
    fetchSymbols();
  }, []);

  useEffect(() => {
    if (!selectedSymbol) return;

    const ws = new WebSocket(
      `wss://stream.binance.com:9443/ws/${selectedSymbol.value}@ticker`
    );

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setCurrentPrice(parseFloat(data.c));
      setPriceChange(parseFloat(data.P));
    };

    ws.onerror = (err) => console.error("Price WebSocket error:", err);

    return () => ws.close();
  }, [selectedSymbol]);

  const selectStyles = {
    control: (provided, state) => ({
      ...provided,
      backgroundColor: theme === "dark" ? "#1E1E1E" : "#fff",
      borderColor: state.isFocused
        ? "#0ECB81"
        : theme === "dark"
        ? "#555"
        : "#ccc",
      boxShadow: state.isFocused ? "0 0 0 1px #0ECB81" : "none",
      "&:hover": { borderColor: "#0ECB81" },
      color: theme === "dark" ? "#EEE" : "#333",
      borderRadius: "8px",
      minHeight: "40px",
    }),
    singleValue: (provided) => ({
      ...provided,
      color: theme === "dark" ? "#EEE" : "#333",
    }),
    input: (provided) => ({
      ...provided,
      color: theme === "dark" ? "#EEE" : "#333",
    }),
    placeholder: (provided) => ({
      ...provided,
      color: theme === "dark" ? "#888" : "#666",
    }),
    menu: (provided) => ({
      ...provided,
      backgroundColor: theme === "dark" ? "#1E1E1E" : "#fff",
      color: theme === "dark" ? "#EEE" : "#333",
      borderRadius: "8px",
      marginTop: "4px",
      zIndex: 9999,
    }),
    option: (provided, state) => ({
      ...provided,
      backgroundColor: state.isFocused
        ? theme === "dark"
          ? "#333"
          : "#eee"
        : theme === "dark"
        ? "#1E1E1E"
        : "#fff",
      color: theme === "dark" ? "#EEE" : "#333",
      "&:active": {
        backgroundColor: "#0ECB81",
        color: "#000",
      },
    }),
    dropdownIndicator: (provided) => ({
      ...provided,
      color: theme === "dark" ? "#EEE" : "#333",
      "&:hover": { color: "#0ECB81" },
    }),
    indicatorSeparator: (provided) => ({
      ...provided,
      backgroundColor: theme === "dark" ? "#555" : "#ccc",
    }),
    clearIndicator: (provided) => ({
      ...provided,
      color: theme === "dark" ? "#EEE" : "#333",
      "&:hover": { color: "#0ECB81" },
    }),
  };

  if (!selectedSymbol) {
    return <p className={styles.loadingText}>Loading symbols...</p>;
  }

  return (
    <div
      className={`${styles.pageContainer} ${
        theme === "dark" ? styles.pageContainerDark : styles.pageContainerLight
      }`}
    >
      <header
        className={`${styles.header} ${
          theme === "dark" ? styles.headerDark : styles.headerLight
        }`}
      >
        <div className={styles.headerLeft}>
          <h2 className={styles.marketTitle}>Market Dashboard</h2>
          {currentPrice && (
            <div className={styles.priceInfo}>
              <span className={styles.priceValue}>
                ${currentPrice.toLocaleString()}
              </span>
              <span
                className={
                  priceChange >= 0
                    ? styles.priceChangePositive
                    : styles.priceChangeNegative
                }
              >
                {priceChange >= 0 ? "+" : ""}
                {priceChange?.toFixed(2)}%
              </span>
            </div>
          )}
        </div>
        <div className={styles.selectContainer}>
          <Select
            options={symbols}
            value={selectedSymbol}
            onChange={(option) => setSelectedSymbol(option)}
            isSearchable
            placeholder="Search or Select Symbol..."
            styles={selectStyles}
          />
        </div>
      </header>

      <div className={styles.mainContent}>
        <div
          className={`${styles.sidebar} ${
            theme === "dark" ? styles.sidebarDark : styles.sidebarLight
          }`}
        >
          <OrderBook
            symbol={selectedSymbol.value}
            currentPrice={currentPrice}
            theme={theme}
          />
        </div>

        <div className={styles.rightContent}>
          <div
            className={`${styles.chartSection} ${
              theme === "dark"
                ? styles.chartSectionDark
                : styles.chartSectionLight
            }`}
          >
            <CryptoCandlesChart
              key={selectedSymbol.value}
              symbol={selectedSymbol.value}
              currentPrice={currentPrice}
              theme={theme}
            />
          </div>

          <div
            className={`${styles.widgetSection} ${
              theme === "dark"
                ? styles.widgetSectionDark
                : styles.widgetSectionLight
            }`}
          >
            <BuySellTransferWidget
              symbol={selectedSymbol.value}
              currentPrice={currentPrice}
              theme={theme}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default CryptoDetailPage;

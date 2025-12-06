import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import BackButton from "../components/BackButton";
import { useTheme } from "../context/ThemeContext";

const CryptoCandlesTable = () => {
  const [groupedCandles, setGroupedCandles] = useState({});
  const { symbol } = useParams();
  const { theme } = useTheme();

  useEffect(() => {
    const fetchData = async () => {
      const grouped = {};
      try {
        const res = await axios.get(
          `https://cryptocortex-crypto-trading-bot-9.onrender.com/candles/${symbol}`,
          {
            params: { days_back: 30 },
          }
        );
        grouped[symbol] = res.data.sort(
          (a, b) => new Date(b.time) - new Date(a.time)
        );
      } catch (err) {
        console.error(`Error fetching ${symbol}:`, err);
      }
      setGroupedCandles(grouped);
    };

    fetchData();
  }, [symbol]);

  return (
    <div
      style={{
        padding: "20px",
        backgroundColor: theme === "dark" ? "#1a1a1a" : "#ffffff",
        color: theme === "dark" ? "#eee" : "#333",
        minHeight: "100vh",
      }}
    >
      <h1 style={{ color: theme === "dark" ? "#eee" : "#333" }}>
        Crypto Candlestick Prices
      </h1>
      {Object.entries(groupedCandles).length === 0 ? (
        <p>Loading data or no candles found.</p>
      ) : (
        Object.entries(groupedCandles).map(([symbol, data]) => (
          <div key={symbol} style={{ marginBottom: "30px" }}>
            <h2>{symbol}</h2>
            <div style={{ height: "auto", width: "100vw", padding: "20px" }}>
              <table
                border="1"
                cellPadding="6"
                style={{
                  width: "90%",
                  height: "90%",
                  textAlign: "center",
                  borderColor: theme === "dark" ? "#555" : "#ccc",
                  backgroundColor: theme === "dark" ? "#1e1e1e" : "#fff",
                  color: theme === "dark" ? "#eee" : "#333",
                }}
              >
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Interval</th>
                    <th>Open</th>
                    <th>High</th>
                    <th>Low</th>
                    <th>Close</th>
                    <th>Volume</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((candle, index) => (
                    <tr key={index}>
                      <td>{new Date(candle.time).toLocaleString()}</td>
                      <td>{candle.interval}</td>
                      <td>{candle.open}</td>
                      <td>{candle.high}</td>
                      <td>{candle.low}</td>
                      <td>{candle.close}</td>
                      <td>{candle.volume}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))
      )}
      <BackButton />
    </div>
  );
};

export default CryptoCandlesTable;

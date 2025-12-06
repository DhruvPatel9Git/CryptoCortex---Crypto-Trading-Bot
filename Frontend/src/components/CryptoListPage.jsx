import React, { useEffect, useState } from "react";
import styles from "../styles/CryptoListPage.module.css";
import { useTheme } from "../context/ThemeContext";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { isTokenValid } from "../utils/auth";

const CryptoListPage = () => {
  const [cryptos, setCryptos] = useState([]);
  const [livePrices, setLivePrices] = useState({});
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const { theme } = useTheme();
  const navigate = useNavigate();
  const pageSize = 10;
  const [isLoggedIn, setIsLoggedIn] = useState(isTokenValid());

  const popularSymbols = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "SOLUSDT",
  ];
  const [popularCoins, setPopularCoins] = useState([]);

  const fetchCryptos = async (pageNum, searchTerm = "") => {
    setLoading(true);
    try {
      const skip = (pageNum - 1) * pageSize;
      const res = await axios.get(
        "https://cryptocortex-crypto-trading-bot-9.onrender.com/cryptos",
        {
          params: { skip, limit: pageSize, search: searchTerm },
        }
      );
      setCryptos(res.data.items);
      setTotal(res.data.total);
    } catch (err) {
      console.error("Error fetching cryptos:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchPopularCoins = async () => {
    try {
      const res = await axios.get(
        "https://cryptocortex-crypto-trading-bot-9.onrender.com/cryptos",
        {
          params: { skip: 0, limit: 1000 },
        }
      );
      setPopularCoins(
        res.data.items.filter((item) => popularSymbols.includes(item.symbol))
      );
    } catch (err) {
      console.error("Error fetching popular coins:", err);
    }
  };

  useEffect(() => {
    fetchCryptos(page, search);
  }, [page, search]);

  useEffect(() => {
    fetchPopularCoins();
  }, []);

  useEffect(() => {
    const ws = new WebSocket("wss://stream.binance.com:9443/ws/!ticker@arr");

    ws.onmessage = (event) => {
      try {
        const tickers = JSON.parse(event.data); // array of tickers

        setLivePrices((prev) => {
          const updated = { ...prev };
          tickers.forEach((t) => {
            updated[t.s] = t;
          });
          return updated;
        });
      } catch (err) {
        console.error("WS parse error:", err);
      }
    };

    return () => ws.close();
  }, []);

  useEffect(() => {
    const handleStorageChange = () => {
      setIsLoggedIn(isTokenValid());
    };
    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, []);

  const handleSignupRedirect = () => {
    navigate("/register");
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div
      className={`${styles.container} ${
        theme === "dark" ? styles.containerDark : styles.containerLight
      }`}
    >
      {/* LEFT SIDEBAR - static and full height */}
      <aside
        className={`${styles.leftSidebar} ${
          theme === "dark" ? styles.leftSidebarDark : styles.leftSidebarLight
        }`}
      >
        <div className={styles.logoContainer}>
          <div className={styles.logoIcon}>
            <div className={styles.logoSymbol}>₿</div>
            <div className={styles.logoIndicator}>
              <div className={styles.logoIndicatorDot}></div>
            </div>
          </div>
          <div>
            <h1 className={styles.logoTextCrypto}>Crypto</h1>
            <h1 className={styles.logoTextCortex}>Cortex</h1>
          </div>
        </div>

        {!isLoggedIn && (
          <div className={styles.signupSection}>
            <h2 className={styles.signupTitle}>Join the Future</h2>
            <p className={styles.signupDescription}>
              Track, analyze, and trade cryptocurrencies with advanced analytics
            </p>
            <button
              onClick={handleSignupRedirect}
              className={styles.signupButton}
            >
              Sign Up Now
            </button>
          </div>
        )}
      </aside>

      {/* RIGHT SIDE - scrollable */}
      <main className={styles.rightSide}>
        <div className={styles.popularSection}>
          <h2 className={styles.popularTitle}>Popular</h2>
          <div className={styles.popularGrid}>
            {popularSymbols.map((symbol) => {
              const coin = popularCoins.find((c) => c.symbol === symbol);
              const live = livePrices[symbol];
              return coin ? (
                <div
                  key={symbol}
                  className={`${styles.popularCard} ${
                    theme === "dark"
                      ? styles.popularCardDark
                      : styles.popularCardLight
                  }`}
                >
                  <h3 className={styles.popularCardTitle}>{coin.base_asset}</h3>
                  <div className={styles.popularCardPrice}>
                    {live ? `$${parseFloat(live.c).toFixed(2)}` : "Loading..."}
                  </div>
                  <div
                    className={`${styles.popularCardChange} ${
                      live
                        ? live.P >= 0
                          ? styles.popularCardChangePositive
                          : styles.popularCardChangeNegative
                        : styles.popularCardChangeNeutral
                    }`}
                  >
                    {live ? `${live.P}%` : "..."}
                  </div>
                </div>
              ) : null;
            })}
          </div>
        </div>

        <div className={styles.searchSection}>
          <input
            type="text"
            placeholder="Search by symbol or asset..."
            value={search}
            onChange={(e) => {
              setPage(1);
              setSearch(e.target.value);
            }}
            className={`${styles.searchInput} ${
              theme === "dark"
                ? styles.searchInputDark
                : styles.searchInputLight
            }`}
          />
        </div>

        {loading ? (
          <p className={styles.loadingText}>Loading...</p>
        ) : (
          <>
            <table
              className={`${styles.table} ${
                theme === "dark" ? styles.tableDark : styles.tableLight
              }`}
            >
              <thead>
                <tr
                  className={`${styles.tableHead} ${
                    theme === "dark"
                      ? styles.tableHeadDark
                      : styles.tableHeadLight
                  }`}
                >
                  <th className={styles.tableHeader}>#</th>
                  <th className={styles.tableHeader}>Symbol</th>
                  <th className={styles.tableHeader}>Base Asset</th>
                  <th className={styles.tableHeader}>Live Price</th>
                  <th className={styles.tableHeader}>Change (%)</th>
                  <th className={styles.tableHeader}>Candlestick</th>
                </tr>
              </thead>
              <tbody>
                {cryptos.map((crypto, index) => {
                  const live = livePrices[crypto.symbol];
                  return (
                    <tr
                      key={crypto.symbol}
                      className={`${styles.tableRow} ${
                        theme === "dark"
                          ? styles.tableRowDark
                          : styles.tableRowLight
                      }`}
                    >
                      <td className={styles.tableCell}>
                        {(page - 1) * pageSize + index + 1}
                      </td>
                      <td className={styles.tableCell}>{crypto.symbol}</td>
                      <td className={styles.tableCell}>{crypto.base_asset}</td>
                      <td className={styles.tableCell}>
                        {live ? `$${parseFloat(live.c).toFixed(6)}` : "..."}
                      </td>
                      <td
                        className={`${styles.tableCell} ${
                          live?.P >= 0
                            ? styles.tableCellChangePositive
                            : styles.tableCellChangeNegative
                        }`}
                      >
                        {live ? `${live.P}%` : "..."}
                      </td>
                      <td className={styles.tableCell}>
                        <a
                          href={`/candles/${crypto.symbol}`}
                          className={styles.tableCellLink}
                        >
                          View
                        </a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            <div className={styles.pagination}>
              <button
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
                className={`${styles.paginationButton} ${
                  page === 1
                    ? styles.paginationButtonDisabled
                    : styles.paginationButtonEnabled
                }`}
              >
                Previous
              </button>
              <span>
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page === totalPages}
                className={`${styles.paginationButton} ${
                  page === totalPages
                    ? styles.paginationButtonDisabled
                    : styles.paginationButtonEnabled
                }`}
              >
                Next
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  );
};

export default CryptoListPage;

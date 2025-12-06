import React, { useState, useEffect } from "react";
import axios from "axios";
import { useTheme } from "../context/ThemeContext";
import styles from "../styles/BuySellTransfer.module.css";

const BuySellTransferPage = () => {
  const { theme } = useTheme();

  // Existing state
  const [cryptos, setCryptos] = useState([]);
  const [selectedCrypto, setSelectedCrypto] = useState("");
  const [orderType, setOrderType] = useState("MARKET");
  const [tradeAmount, setTradeAmount] = useState("");
  const [price, setPrice] = useState("");
  const [cart, setCart] = useState([]);
  const [activeTab, setActiveTab] = useState("trade");
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("");

  // ✅ New transfer form state
  const [recipientUsername, setRecipientUsername] = useState("");
  const [transferSymbol, setTransferSymbol] = useState("");
  const [transferAmount, setTransferAmount] = useState("");

  const API_URL = "https://cryptocortex-crypto-trading-bot-9.onrender.com";

  useEffect(() => {
    fetchCartFromBackend();
  }, []);

  const handleCryptoSearch = async (value) => {
    setSelectedCrypto(value.toUpperCase());
    if (!value) return setCryptos([]);
    try {
      const res = await axios.get(`${API_URL}/cryptos/search`, {
        params: { query: value },
      });
      setCryptos(res.data);
    } catch (err) {
      console.error("Search error:", err);
    }
  };

  const getUserIdFromToken = () => {
    const token = localStorage.getItem("access_token");
    if (!token) return null;
    try {
      return JSON.parse(atob(token.split(".")[1]))?.sub || null;
    } catch (e) {
      console.error("Invalid token:", e);
      return null;
    }
  };

  const handleAddToCart = async () => {
    const token = localStorage.getItem("access_token");

    if (!selectedCrypto || !tradeAmount || (orderType === "LIMIT" && !price)) {
      setMessage("Please fill all required fields.");
      setMessageType("error");
      return;
    }

    try {
      const payload = {
        symbol: selectedCrypto,
        quantity: parseFloat(tradeAmount),
        order_type: orderType,
        ...(orderType === "LIMIT" && { price: parseFloat(price) }),
      };

      await axios.post(`${API_URL}/cart/add`, payload, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      setSelectedCrypto("");
      setTradeAmount("");
      setPrice("");
      setMessage("Item added to cart!");
      setMessageType("success");
      await fetchCartFromBackend();
    } catch (err) {
      console.error(err);
      setMessage(err?.response?.data?.detail || "Add to cart failed.");
      setMessageType("error");
    }
  };

  const fetchCartFromBackend = async () => {
    const token = localStorage.getItem("access_token");
    try {
      const res = await axios.get(`${API_URL}/cart/view`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setCart(res.data.items);
    } catch (err) {
      console.error("Failed to fetch cart:", err);
    }
  };

  const handleCartCheckout = async () => {
    const token = localStorage.getItem("access_token");
    const user_id = getUserIdFromToken();
    if (!user_id || !token) {
      setMessage("User not authenticated.");
      setMessageType("error");
      return;
    }

    try {
      await axios.post(
        `${API_URL}/cart/checkout`,
        {},
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      setCart([]);
      setMessage("Cart checkout successful!");
      setMessageType("success");
    } catch (err) {
      console.error(err);
      setMessage("Cart checkout failed.");
      setMessageType("error");
    }
  };

  const clearCart = async () => {
    const token = localStorage.getItem("access_token");
    try {
      await axios.delete(`${API_URL}/cart/clear`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setCart([]);
      setMessage("Cart cleared.");
      setMessageType("success");
    } catch (err) {
      console.error(err);
      setMessage("Failed to clear cart.");
      setMessageType("error");
    }
  };

  const removeCartItem = async (symbol) => {
    const token = localStorage.getItem("access_token");
    try {
      await axios.delete(`${API_URL}/cart/remove`, {
        params: { symbol },
        headers: { Authorization: `Bearer ${token}` },
      });
      setMessage(`Item ${symbol} removed from cart.`);
      setMessageType("success");
      await fetchCartFromBackend();
    } catch (err) {
      console.error(err);
      setMessage(err?.response?.data?.detail || `Failed to remove ${symbol}.`);
      setMessageType("error");
    }
  };

  const handleTrade = async (side) => {
    const token = localStorage.getItem("access_token");
    const user_id = getUserIdFromToken();
    if (!user_id || !token) {
      setMessage("User not authenticated.");
      setMessageType("error");
      return;
    }

    if (!selectedCrypto || !tradeAmount || (orderType === "LIMIT" && !price)) {
      setMessage("Please fill all required fields.");
      setMessageType("error");
      return;
    }

    try {
      const payload = {
        user_id,
        symbol: selectedCrypto,
        side: side.toUpperCase(),
        order_type: orderType,
        quantity: parseFloat(tradeAmount),
        ...(orderType === "LIMIT" && { price: parseFloat(price) }),
      };

      await axios.post(`${API_URL}/trade`, payload, {
        headers: { Authorization: `Bearer ${token}` },
      });

      setMessage(`${side.toUpperCase()} order successful!`);
      setMessageType("success");
      setTradeAmount("");
      setPrice("");
    } catch (err) {
      console.error(err);
      setMessage(err?.response?.data?.detail || `${side} order failed.`);
      setMessageType("error");
    }
  };

  // ✅ New Transfer submission function
  const handleTransfer = async () => {
    const token = localStorage.getItem("access_token");

    if (!recipientUsername || !transferSymbol || !transferAmount) {
      setMessage("Please fill all fields.");
      setMessageType("error");
      return;
    }

    try {
      const payload = {
        to_username: recipientUsername,
        symbol: transferSymbol.toUpperCase(),
        amount: parseFloat(transferAmount),
      };

      await axios.post(`${API_URL}/transfer`, payload, {
        headers: { Authorization: `Bearer ${token}` },
      });

      setMessage("✅ Transfer successful!");
      setMessageType("success");

      setRecipientUsername("");
      setTransferSymbol("");
      setTransferAmount("");
    } catch (err) {
      console.error(err);
      setMessage(err?.response?.data?.detail || "❌ Transfer failed.");
      setMessageType("error");
    }
  };

  return (
    <div
      className={`${styles.container} ${
        theme === "dark" ? styles.containerDark : styles.containerLight
      }`}
    >
      <div
        className={`${styles.formBox} ${
          theme === "dark" ? styles.formBoxDark : styles.formBoxLight
        }`}
      >
        <div className={styles.tabSwitcher}>
          <button
            onClick={() => setActiveTab("trade")}
            className={`${styles.tabButton} ${styles.buyTab} ${
              activeTab === "trade" ? styles.buyTabActive : ""
            }`}
          >
            Buy / Sell
          </button>
          <button
            onClick={() => setActiveTab("cart")}
            className={`${styles.tabButton} ${styles.cartTab} ${
              activeTab === "cart" ? styles.cartTabActive : ""
            }`}
          >
            Cart
          </button>
          <button
            onClick={() => setActiveTab("transfer")}
            className={`${styles.tabButton} ${styles.transferTab} ${
              activeTab === "transfer" ? styles.transferTabActive : ""
            }`}
          >
            Transfer
          </button>
        </div>

        {activeTab === "trade" && (
          <>
            <h2>Buy / Sell Cryptocurrency</h2>
            <div className={styles.inputGroup}>
              <label>Search Coin:</label>
              <input
                type="text"
                placeholder="e.g., BTCUSDT"
                value={selectedCrypto}
                onChange={(e) => handleCryptoSearch(e.target.value)}
                className={
                  theme === "dark" ? styles.inputDark : styles.inputLight
                }
              />
              {cryptos.length > 0 && (
                <ul className={styles.searchResults}>
                  {cryptos.slice(0, 10).map((c) => (
                    <li
                      key={c.symbol}
                      onClick={() => handleCryptoSearch(c.symbol)}
                    >
                      {c.symbol} ({c.base_asset})
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className={styles.inputGroup}>
              <label>Order Type:</label>
              <select
                value={orderType}
                onChange={(e) => setOrderType(e.target.value)}
                className={
                  theme === "dark" ? styles.inputDark : styles.inputLight
                }
              >
                <option value="MARKET">Market</option>
                <option value="LIMIT">Limit</option>
              </select>
            </div>

            <div className={styles.inputGroup}>
              <input
                type="number"
                placeholder="Trade Amount"
                value={tradeAmount}
                onChange={(e) => setTradeAmount(e.target.value)}
                className={
                  theme === "dark" ? styles.inputDark : styles.inputLight
                }
              />
            </div>

            {orderType === "LIMIT" && (
              <div className={styles.inputGroup}>
                <input
                  type="number"
                  placeholder="Limit Price"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  className={
                    theme === "dark" ? styles.inputDark : styles.inputLight
                  }
                />
              </div>
            )}

            <div className={styles.actionRow}>
              <button className={styles.actionButton} onClick={handleAddToCart}>
                Add to Cart
              </button>
              <button
                className={styles.actionButton}
                onClick={() => handleTrade("buy")}
                disabled={!tradeAmount}
              >
                Buy
              </button>
              <button
                className={styles.actionButton}
                onClick={() => handleTrade("sell")}
                disabled={!tradeAmount}
              >
                Sell
              </button>
            </div>
          </>
        )}

        {activeTab === "cart" && (
          <>
            <h2> Trade Cart</h2>
            {cart.length === 0 ? (
              <p>Cart is empty.</p>
            ) : (
              <ul>
                {cart.map((item, index) => (
                  <li key={index} className={styles.cartItem}>
                    {item.symbol} - {item.quantity} {item.order_type}
                    {item.price && ` @ $${item.price}`}
                    <button
                      className={styles.removeBtn}
                      onClick={() => removeCartItem(item.symbol)}
                    >
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <div className={styles.actionRow}>
              <button
                className={styles.actionButton}
                onClick={handleCartCheckout}
                disabled={cart.length === 0}
              >
                Checkout
              </button>
              <button
                className={styles.clearBtn}
                onClick={clearCart}
                disabled={cart.length === 0}
              >
                Clear Cart
              </button>
            </div>
          </>
        )}

        {activeTab === "transfer" && (
          <>
            <h2> Transfer Cryptocurrency</h2>

            <div className={styles.inputGroup}>
              <label>Recipient Username:</label>
              <input
                type="text"
                placeholder="Enter recipient's username"
                value={recipientUsername}
                onChange={(e) => setRecipientUsername(e.target.value)}
                className={
                  theme === "dark" ? styles.inputDark : styles.inputLight
                }
              />
            </div>

            <div className={styles.inputGroup}>
              <label>Coin Symbol:</label>
              <input
                type="text"
                placeholder="e.g., BTCUSDT"
                value={transferSymbol}
                onChange={(e) => setTransferSymbol(e.target.value)}
                className={
                  theme === "dark" ? styles.inputDark : styles.inputLight
                }
              />
            </div>

            <div className={styles.inputGroup}>
              <label>Amount:</label>
              <input
                type="number"
                placeholder="Amount to transfer"
                value={transferAmount}
                onChange={(e) => setTransferAmount(e.target.value)}
                className={
                  theme === "dark" ? styles.inputDark : styles.inputLight
                }
              />
            </div>

            <button
              className={styles.transferButton}
              onClick={handleTransfer}
              disabled={
                !recipientUsername || !transferSymbol || !transferAmount
              }
            >
              Send Transfer
            </button>
          </>
        )}

        {message && (
          <div className={`${styles.message} ${styles[messageType]}`}>
            {message}
          </div>
        )}
      </div>
    </div>
  );
};

export default BuySellTransferPage;

import React, { useState } from "react";
import axios from "axios";
import styles from "../styles/BuySellTransferWidget.module.css";

const API_URL = "https://cryptocortex-crypto-trading-bot-9.onrender.com";

export const BuySellTransferWidget = ({ symbol, theme = "dark" }) => {
  const [orderType, setOrderType] = useState("LIMIT");
  const [buyAmount, setBuyAmount] = useState("");
  const [buyPrice, setBuyPrice] = useState("");
  const [sellAmount, setSellAmount] = useState("");
  const [sellPrice, setSellPrice] = useState("");
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("");

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

  const handleTrade = async (side) => {
    const token = localStorage.getItem("access_token");
    const user_id = getUserIdFromToken();
    if (!user_id || !token) {
      setMessage("User not authenticated.");
      setMessageType("error");
      return;
    }

    const amount = side === "buy" ? buyAmount : sellAmount;
    const price = side === "buy" ? buyPrice : sellPrice;

    if (!amount || (orderType === "LIMIT" && !price)) {
      setMessage("Please fill all required fields.");
      setMessageType("error");
      return;
    }

    try {
      const payload = {
        user_id,
        symbol,
        side: side.toUpperCase(),
        order_type: orderType,
        quantity: parseFloat(amount),
        ...(orderType === "LIMIT" && { price: parseFloat(price) }),
      };

      const response = await axios.post(`${API_URL}/trade`, payload, {
        headers: { Authorization: `Bearer ${token}` },
      });

      setMessage(response.data.message);
      setMessageType("success");

      if (side === "buy") {
        setBuyAmount("");
        setBuyPrice("");
      } else {
        setSellAmount("");
        setSellPrice("");
      }
    } catch (err) {
      console.error(err);
      setMessage(err?.response?.data?.detail || `${side} order failed.`);
      setMessageType("error");
    }
  };

  const renderForm = (side) => {
    const amount = side === "buy" ? buyAmount : sellAmount;
    const setAmount = side === "buy" ? setBuyAmount : setSellAmount;
    const price = side === "buy" ? buyPrice : sellPrice;
    const setPrice = side === "buy" ? setBuyPrice : setSellPrice;

    const isMarket = orderType === "MARKET";
    const buttonClass =
      amount && side === "buy"
        ? styles.buyButton
        : amount && side === "sell"
        ? styles.sellButton
        : styles.submitButtonDisabled;

    return (
      <div
        className={`${styles.formContainer} ${
          theme === "dark"
            ? styles.formContainerDark
            : styles.formContainerLight
        }`}
      >
        <div>
          <div className={styles.inputWrapper}>
            <input
              type="number"
              placeholder={isMarket ? "Market Price" : "0.00"}
              value={isMarket ? "" : price}
              onChange={(e) => setPrice(e.target.value)}
              disabled={isMarket}
              className={`${styles.inputField} ${
                isMarket ? styles.inputFieldDisabled : ""
              } ${
                theme === "dark"
                  ? styles.inputFieldDark
                  : styles.inputFieldLight
              }`}
            />
          </div>
          <div className={styles.inputLabel}>Price</div>
        </div>

        <div>
          <div className={styles.inputWrapper}>
            <input
              type="number"
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className={`${styles.inputField} ${
                theme === "dark"
                  ? styles.inputFieldDark
                  : styles.inputFieldLight
              }`}
            />
          </div>
          <div className={styles.inputLabel}>Amount</div>
        </div>

        <button
          onClick={() => handleTrade(side)}
          disabled={!amount}
          className={`${styles.submitButton} ${buttonClass} ${
            theme === "dark"
              ? styles.submitButtonDark
              : styles.submitButtonLight
          }`}
        >
          {side === "buy" ? "Buy" : "Sell"}
        </button>
      </div>
    );
  };

  return (
    <div
      className={`${styles.widgetContainer} ${
        theme === "dark"
          ? styles.widgetContainerDark
          : styles.widgetContainerLight
      }`}
    >
      <div
        className={`${styles.tabs} ${
          theme === "dark" ? styles.tabsDark : styles.tabsLight
        }`}
      >
        <div
          onClick={() => setOrderType("LIMIT")}
          className={`${styles.tab} ${
            theme === "dark" ? styles.tabDark : styles.tabLight
          } ${
            orderType === "LIMIT"
              ? theme === "dark"
                ? styles.tabActiveDark
                : styles.tabActiveLight
              : ""
          }`}
        >
          Limit
        </div>
        <div
          onClick={() => setOrderType("MARKET")}
          className={`${styles.tab} ${
            theme === "dark" ? styles.tabDark : styles.tabLight
          } ${
            orderType === "MARKET"
              ? theme === "dark"
                ? styles.tabActiveDark
                : styles.tabActiveLight
              : ""
          }`}
        >
          Market
        </div>
      </div>

      <div className={styles.mainContent}>
        <div
          className={`${styles.section} ${styles.sectionBorder} ${
            theme === "dark" ? styles.sectionDark : styles.sectionLight
          }`}
        >
          <div
            className={`${
              theme === "dark"
                ? styles.sectionTitleDark
                : styles.sectionTitleLight
            }`}
          >
            Buy {symbol?.split("USDT")[0] || "BTC"}
          </div>
          {renderForm("buy")}
        </div>

        <div
          className={`${styles.section} ${
            theme === "dark" ? styles.sectionDark : styles.sectionLight
          }`}
        >
          <div
            className={`${
              theme === "dark"
                ? styles.sectionTitleDark
                : styles.sectionTitleLight
            }`}
          >
            Sell {symbol?.split("USDT")[0] || "BTC"}
          </div>
          {renderForm("sell")}
        </div>
      </div>

      {message && (
        <div
          className={`${styles.message} ${
            messageType === "success"
              ? styles.messageSuccess
              : styles.messageError
          } ${theme === "dark" ? styles.messageDark : styles.messageLight}`}
        >
          {message}
        </div>
      )}
    </div>
  );
};

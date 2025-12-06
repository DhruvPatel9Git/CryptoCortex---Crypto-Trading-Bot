import React, { useState, useEffect, useRef } from "react";
import styles from "../styles/ChatWidget.module.css";

function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loaded, setLoaded] = useState(false);
  const messagesEndRef = useRef(null);

  // Load chat history from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("chatMessages");
    if (saved && saved !== "[]") {
      setMessages(JSON.parse(saved));
    } else {
      setMessages([
        {
          sender: "bot",
          text: ` Hi, I'm your trading assistant!
 Try typing:
• Buy 0.5 BTCUSDT at market price
• Sell 2 ETHUSDT at limit price 3500
• Show my order history
• Price of BTCUSDT on June 20
How can I help you today?`,
        },
      ]);
    }
    setLoaded(true);
  }, []);

  // Save messages to localStorage on update
  useEffect(() => {
    if (loaded) {
      localStorage.setItem("chatMessages", JSON.stringify(messages));
    }
  }, [messages, loaded]);

  // Auto-scroll to last message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const toggleOpen = () => setIsOpen(!isOpen);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);

    const token = localStorage.getItem("access_token");

    if (!token) {
      localStorage.removeItem("chatMessages");
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: "⚠️ You are not logged in. Please login to chat.",
        },
      ]);
      setInput("");
      return;
    }

    try {
      const res = await fetch(
        "https://cryptocortex-crypto-trading-bot-9.onrender.com/qa",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ question: input }),
        }
      );

      if (res.status === 401) {
        setMessages([
          { sender: "bot", text: "⚠️ Session expired. Please log in again." },
        ]);
        localStorage.removeItem("chatMessages");
        localStorage.removeItem("access_token");
        setInput("");
        return;
      }

      const data = await res.json();

      let botReply = "Sorry, I couldn't understand.";

      if (data.answer) botReply = data.answer;
      else if (data.error) botReply = `⚠️ ${data.error}`;

      setMessages((prev) => [...prev, { sender: "bot", text: botReply }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "⚠️ Error: could not connect to server." },
      ]);
    }

    setInput("");
  };

  return (
    <div className={styles.chatWidget}>
      {!isOpen && (
        <button className={styles.chatToggle} onClick={toggleOpen}>
          💬 Chat
        </button>
      )}

      {isOpen && (
        <div className={styles.chatBox}>
          <div className={styles.chatHeader}>
            <span>CryptoCortex Bot</span>
            <button onClick={toggleOpen}>×</button>
          </div>
          <div className={styles.chatMessages}>
            {messages.map((m, i) => (
              <div
                key={i}
                className={
                  m.sender === "bot" ? styles.botMessage : styles.userMessage
                }
              >
                {m.text}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
          <div className={styles.chatInput}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              placeholder="Type your message..."
            />
            <button onClick={sendMessage}>Send</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default ChatWidget;

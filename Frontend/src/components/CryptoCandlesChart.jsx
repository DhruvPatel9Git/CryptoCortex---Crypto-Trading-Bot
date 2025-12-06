import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import Plot from "react-plotly.js";
import styles from "../styles/CryptoCandlesChart.module.css";

const calculateMA = (data, period) => {
  return data.map((_, i, arr) => {
    if (i < period - 1) return null;
    const slice = arr.slice(i - period + 1, i + 1);
    return slice.reduce((sum, val) => sum + val, 0) / period;
  });
};

const CryptoCandlesChart = ({ symbol, currentPrice, theme = "dark" }) => {
  const [candles, setCandles] = useState([]);
  const [liveCandle, setLiveCandle] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    let isMounted = true;
    setCandles([]);

    const fetchCandles = async () => {
      try {
        const res = await axios.get(
          `https://cryptocortex-crypto-trading-bot-9.onrender.com/candles/${symbol}`,
          {
            params: { days_back: 120 },
          }
        );
        const sorted = res.data.sort(
          (a, b) => new Date(a.time) - new Date(b.time)
        );

        if (isMounted) {
          setCandles(sorted);
        }
      } catch (err) {
        if (isMounted) {
          console.error("Error fetching candlestick data:", err);
          setCandles([]);
        }
      }
    };

    fetchCandles();

    return () => {
      isMounted = false;
    };
  }, [symbol]);

  useEffect(() => {
    if (!symbol) return;

    if (wsRef.current) wsRef.current.close();

    wsRef.current = new WebSocket(
      `wss://stream.binance.com:9443/ws/${symbol}@kline_1m`
    );

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const kline = data.k;

      if (kline) {
        const liveData = {
          time: new Date(kline.t),
          open: parseFloat(kline.o),
          high: parseFloat(kline.h),
          low: parseFloat(kline.l),
          close: parseFloat(kline.c),
          volume: parseFloat(kline.v),
          isComplete: kline.x,
        };

        setLiveCandle(liveData);
      }
    };

    wsRef.current.onerror = (err) => {
      console.error("Kline WebSocket error:", err);
    };

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [symbol]);

  if (candles.length === 0) {
    return (
      <div
        className={`${styles.loadingContainer} ${
          theme === "dark"
            ? styles.loadingContainerDark
            : styles.loadingContainerLight
        }`}
      >
        <div>
          <div>Loading {symbol?.toUpperCase()} chart...</div>
          {currentPrice && (
            <div className={styles.loadingText}>
              Current Price: ${currentPrice.toLocaleString()}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Combine historical and live data
  const allCandles = [...candles];
  if (liveCandle && !liveCandle.isComplete) {
    const lastCandleTime = new Date(allCandles[allCandles.length - 1]?.time);
    const liveTime = new Date(liveCandle.time);

    if (
      lastCandleTime &&
      lastCandleTime.getMinutes() === liveTime.getMinutes() &&
      lastCandleTime.getHours() === liveTime.getHours() &&
      lastCandleTime.getDate() === liveTime.getDate()
    ) {
      allCandles[allCandles.length - 1] = liveCandle;
    } else {
      allCandles.push(liveCandle);
    }
  }

  const times = allCandles.map((c) => new Date(c.time));
  const opens = allCandles.map((c) => c.open);
  const highs = allCandles.map((c) => c.high);
  const lows = allCandles.map((c) => c.low);
  const closes = allCandles.map((c) => c.close);
  const volumes = allCandles.map((c) => c.volume || 0);

  const ma7 = calculateMA(closes, 7);
  const ma25 = calculateMA(closes, 25);
  const ma99 = calculateMA(closes, 99);

  // Determine theme colors
  const isDark = theme === "dark";
  const gridColor = isDark ? "#333" : "#ddd";
  const zeroLineColor = isDark ? "#444" : "#aaa";
  const tickFontColor = isDark ? "#EEE" : "#333";
  const plotBgColor = isDark ? "#121212" : "#ffffff";
  const paperBgColor = isDark ? "#1A1A1A" : "#f5f5f5";
  const fontColor = isDark ? "#EEE" : "#333";
  const hoverBgColor = isDark ? "#333" : "#eee";
  const hoverFontColor = isDark ? "#EEE" : "#333";

  return (
    <div
      className={`${styles.chartContainer} ${
        isDark ? styles.chartContainerDark : styles.chartContainerLight
      }`}
    >
      <div className={styles.chartHeader}>
        <h3
          className={
            theme === "dark" ? styles.chartTitleDark : styles.chartTitleLight
          }
        >
          {symbol?.toUpperCase()} Chart
        </h3>
        {currentPrice && (
          <div className={styles.currentPrice}>
            ${currentPrice.toLocaleString()}
          </div>
        )}
      </div>

      <div className={styles.plotContainer}>
        <Plot
          data={[
            {
              x: times,
              open: opens,
              high: highs,
              low: lows,
              close: closes,
              type: "candlestick",
              name: symbol?.toUpperCase(),
              xaxis: "x",
              yaxis: "y",
              increasing: {
                line: { color: "#0ECB81", width: 1 },
                fillcolor: "#0ECB81",
              },
              decreasing: {
                line: { color: "#F6465D", width: 1 },
                fillcolor: "#F6465D",
              },
            },
            {
              type: "bar",
              x: times,
              y: volumes,
              yaxis: "y2",
              marker: {
                color: closes.map((c, i) =>
                  c > opens[i] ? "#0ECB81" : "#F6465D"
                ),
              },
              name: "Volume",
              opacity: 0.5,
            },
            {
              x: times,
              y: ma7,
              type: "scatter",
              mode: "lines",
              line: { color: "#FFB800", width: 1 },
              name: "MA(7)",
            },
            {
              x: times,
              y: ma25,
              type: "scatter",
              mode: "lines",
              line: { color: "#E91E63", width: 1 },
              name: "MA(25)",
            },
            {
              x: times,
              y: ma99,
              type: "scatter",
              mode: "lines",
              line: { color: "#9C27B0", width: 1 },
              name: "MA(99)",
            },
          ]}
          layout={{
            dragmode: "zoom",
            xaxis: {
              type: "date",
              gridcolor: gridColor,
              zerolinecolor: zeroLineColor,
              tickfont: { color: tickFontColor, size: 10 },
              showgrid: true,
            },
            yaxis: {
              domain: [0.3, 1],
              gridcolor: gridColor,
              zerolinecolor: zeroLineColor,
              tickfont: { color: tickFontColor, size: 10 },
              title: {
                text: "Price ($)",
                font: { color: fontColor, size: 12 },
              },
            },
            yaxis2: {
              domain: [0, 0.25],
              showticklabels: false,
              gridcolor: gridColor,
            },
            autosize: true,
            plot_bgcolor: plotBgColor,
            paper_bgcolor: paperBgColor,
            font: { color: fontColor, size: 11 },
            showlegend: true,
            legend: {
              orientation: "h",
              x: 0,
              y: 1.02,
              bgcolor: "rgba(0,0,0,0)",
              font: { size: 10 },
            },
            margin: { r: 10, t: 10, b: 30, l: 50 },
            hovermode: "x unified",
            hoverlabel: {
              bgcolor: hoverBgColor,
              bordercolor: gridColor,
              font: { color: hoverFontColor },
            },
          }}
          useResizeHandler={true}
          style={{ width: "100%", height: "100%" }}
          config={{
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ["pan2d", "lasso2d", "select2d"],
            responsive: true,
          }}
        />
      </div>
    </div>
  );
};

export default CryptoCandlesChart;

import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useLocation, useNavigate } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import styles from "../styles/Portfolio.module.css";

const COLORS = [
  "#0088FE",
  "#00C49F",
  "#FFBB28",
  "#FF8042",
  "#AF19FF",
  "#FF4560",
];

const Portfolio = () => {
  const [portfolio, setPortfolio] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  const { theme } = useTheme();

  const userId = localStorage.getItem("user_id");
  const token = localStorage.getItem("access_token");

  useEffect(() => {
    if (!userId || !token) {
      navigate("/login", {
        replace: true,
        state: { from: location.pathname || "/" },
      });
      return;
    }

    const fetchPortfolio = async () => {
      try {
        const response = await axios.get(
          `http://localhost:8000/portfolio/${userId}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );
        setPortfolio(response.data);
      } catch (error) {
        console.error("Error fetching portfolio:", error);
        if (error.response?.status === 401 || error.response?.status === 403) {
          navigate("/login", {
            replace: true,
            state: { from: location.pathname || "/" },
          });
        }
      } finally {
        setLoading(false);
      }
    };

    fetchPortfolio();
  }, [userId, token, navigate, location.pathname]);

  const chartData = portfolio.map((item) => ({
    name: item.symbol,
    value: parseFloat(item.quantity) * parseFloat(item.avg_buy_price),
  }));

  const totalValue = chartData
    .reduce((acc, item) => acc + item.value, 0)
    .toFixed(2);

  return (
    <div
      className={`${styles.container} ${
        theme === "dark" ? styles.containerDark : styles.containerLight
      }`}
    >
      <h2 className={styles.title}>My Crypto Portfolio</h2>

      {loading ? (
        <p>Loading...</p>
      ) : portfolio.length === 0 ? (
        <p>No portfolio data available.</p>
      ) : (
        <div className={styles.wrapper}>
          <div className={styles.chartContainer}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  dataKey="value"
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  fill="#8884d8"
                  label={({
                    cx,
                    cy,
                    midAngle,
                    innerRadius,
                    outerRadius,
                    percent,
                    index,
                    value,
                  }) => {
                    const RADIAN = Math.PI / 180;
                    const radius =
                      innerRadius + (outerRadius - innerRadius) * 0.5;
                    const x = cx + radius * Math.cos(-midAngle * RADIAN);
                    const y = cy + radius * Math.sin(-midAngle * RADIAN);

                    const displayPercent = (percent * 100).toFixed(1);
                    const displayValue = `$${value.toFixed(2)}`;

                    return (
                      <text
                        x={x}
                        y={y}
                        fill="white"
                        textAnchor="middle"
                        dominantBaseline="central"
                        fontSize="12"
                      >
                        {`${displayPercent}% (${displayValue})`}
                      </text>
                    );
                  }}
                  labelLine={false}
                >
                  {chartData.map((_, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>

                <Tooltip />
                <Legend verticalAlign="bottom" />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className={styles.portfolioList}>
            {portfolio.map((item, index) => (
              <div className={styles.portfolioItem} key={index}>
                <h3>{item.symbol}</h3>
                <p>
                  <strong>Quantity:</strong> {item.quantity}
                </p>
                <p>
                  <strong>Avg Price:</strong> $
                  {parseFloat(item.avg_buy_price).toFixed(2)}
                </p>
                <p>
                  <strong>Value:</strong> $
                  {(
                    parseFloat(item.quantity) * parseFloat(item.avg_buy_price)
                  ).toFixed(2)}
                </p>
                <p>
                  <strong>Updated:</strong>{" "}
                  {new Date(item.updated_at).toLocaleString()}
                </p>
              </div>
            ))}
            <div className={styles.totalValue}>
              Total Portfolio Value: ${totalValue}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Portfolio;

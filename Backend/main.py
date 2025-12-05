from fastapi import FastAPI
from db import lifespan 

# Import routes using package-relative imports when running as `Backend.main`,
# but fall back to top-level imports when modules are executed directly
try:
    from .routes import cryptoPair, ohlc, websocket_routes, trading, current_balance, portfolio, auth_routes, cart, credits, qa_chatbot
except Exception:
    from routes import cryptoPair, ohlc, websocket_routes, trading, current_balance, portfolio, auth_routes, cart, credits, qa_chatbot
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cryptoPair.router)
app.include_router(ohlc.router)
app.include_router(websocket_routes.router)
app.include_router(trading.router)
app.include_router(current_balance.router)
app.include_router(portfolio.router)
app.include_router(auth_routes.router)
app.include_router(cart.router)
app.include_router(credits.router)
# app.include_router(web3_utils.router)
app.include_router(qa_chatbot.router)

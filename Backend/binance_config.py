from dotenv import load_dotenv
import os
import traceback

# Load environment variables from .env file
load_dotenv()

from dotenv import load_dotenv
import os
import traceback

# Load environment variables from .env file
load_dotenv()

# Get Binance API credentials
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
# Support an env flag to force offline/no-network mode (useful on Render or CI)
BINANCE_OFFLINE = os.getenv("BINANCE_OFFLINE", "0") in ("1", "true", "True")


class _LazyBinanceClient:
	"""Proxy object that constructs the real Binance `Client` lazily on first use.

	If construction fails (e.g., restricted location), the proxy will return safe
	no-op callables for data-fetching methods so background jobs can continue
	without raising exceptions.
	"""

	def __init__(self):
		self._client = None
		self._init_exc = None
		self._logged_init_failure = False

	def _init(self):
		# attempt to construct the real client once
		if self._client is not None or self._init_exc is not None:
			return
		if BINANCE_OFFLINE:
			# explicit offline mode - do not attempt network calls
			self._client = None
			return
		try:
			from binance.client import Client as _Client
			# Create client lazily; note the Client constructor may call ping()
			self._client = _Client(api_key=BINANCE_API_KEY, api_secret=BINANCE_SECRET_KEY, testnet=True)
			try:
				self._client.API_URL = "https://testnet.binance.vision/api"
			except Exception:
				pass
		except Exception as e:
			# remember the exception and print traceback once
			self._init_exc = e
			traceback.print_exc()

	def __getattr__(self, item):
		# Ensure the underlying client is initialized
		self._init()
		if self._client is not None:
			return getattr(self._client, item)

		# If client is unavailable, return a safe no-op function.
		def _safe_noop(*args, **kwargs):
			# Log the failure once to surface the root cause
			if not self._logged_init_failure:
				self._logged_init_failure = True
				if self._init_exc is not None:
					print(f"binance_config: initialization failed: {self._init_exc}")
				else:
					print("binance_config: running in BINANCE_OFFLINE mode or client not initialized")

			# Heuristic: return sensible defaults for common Binance calls
			name = item or ""
			if name == "get_exchange_info":
				return {"symbols": []}
			if name == "get_symbol_ticker":
				return {}
			if name == "get_order":
				return None
			if name.startswith("get_") or name.endswith("klines"):
				return []
			return None

		return _safe_noop

	def is_available(self) -> bool:
		"""Return True if the underlying Binance client was successfully initialized."""
		self._init()
		return self._client is not None


# Export a module-level `client` proxy that other modules can import safely
client = _LazyBinanceClient()



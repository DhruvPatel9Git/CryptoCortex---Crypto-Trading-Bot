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
	If construction fails (e.g., restricted location), behavior depends on BINANCE_OFFLINE:
	- If offline mode, methods that fetch data return safe defaults (e.g., empty lists).
	- Otherwise, attribute access raises a RuntimeError with the original exception attached.
	"""

	def __init__(self):
		self._client = None
		self._init_exc = None

	def _init(self):
		if self._client is not None or self._init_exc is not None:
			return
		if BINANCE_OFFLINE:
			self._client = None
			return
		try:
			from binance.client import Client as _Client
			# Create client lazily; avoid any forced ping at import time
			self._client = _Client(api_key=BINANCE_API_KEY, api_secret=BINANCE_SECRET_KEY, testnet=True)
			# Use testnet API URL if needed
			try:
				self._client.API_URL = "https://testnet.binance.vision/api"
			except Exception:
				pass
		except Exception as e:
			self._init_exc = e
			traceback.print_exc()

	def __getattr__(self, item):
		# Ensure the underlying client is initialized
		self._init()
		if self._client is not None:
			return getattr(self._client, item)

		# If offline, provide safe no-op implementations for common methods
		if BINANCE_OFFLINE:
			def _noop(*args, **kwargs):
				# Return an empty result for data-fetching methods, or None for others
				if item.startswith("get_") or item.endswith("klines"):
					return []
				return None
			return _noop

		# Otherwise, raise informative error
		raise RuntimeError(f"Binance client unavailable: initialization failed: {self._init_exc}")


# Export a module-level `client` proxy that other modules can import safely
client = _LazyBinanceClient()



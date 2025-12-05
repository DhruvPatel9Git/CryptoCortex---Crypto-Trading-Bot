"""
Test runner script for CryptoCortex Backend tests.
Provides convenient commands for running different test suites.
"""
import sys
import subprocess
from pathlib import Path


def run_command(cmd: list[str]) -> int:
    """Run a command and return the exit code."""
    print(f"Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    return result.returncode


def main():
    """Main test runner."""
    if len(sys.argv) < 2:
        print("Usage: python run_tests.py [command]")
        print("\nAvailable commands:")
        print("  all              - Run all tests")
        print("  routes           - Run all route tests")
        print("  auth             - Run authentication tests")
        print("  cart             - Run cart tests")
        print("  credits          - Run credits tests")
        print("  crypto           - Run crypto pair tests")
        print("  balance          - Run balance tests")
        print("  ohlc             - Run OHLC/candles tests")
        print("  portfolio        - Run portfolio tests")
        print("  qa               - Run Q&A chatbot tests")
        print("  trading          - Run trading tests")
        print("  websocket        - Run WebSocket tests")
        print("  coverage         - Run all tests with coverage report")
        print("  coverage-html    - Run tests with HTML coverage report")
        print("  verbose          - Run all tests with verbose output")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    tests_dir = Path(__file__).parent
    
    commands = {
        "all": ["pytest", str(tests_dir)],
        "routes": ["pytest", str(tests_dir / "routes")],
        "auth": ["pytest", str(tests_dir / "routes" / "test_auth_routes.py")],
        "cart": ["pytest", str(tests_dir / "routes" / "test_cart.py")],
        "credits": ["pytest", str(tests_dir / "routes" / "test_credits.py")],
        "crypto": ["pytest", str(tests_dir / "routes" / "test_cryptoPair.py")],
        "balance": ["pytest", str(tests_dir / "routes" / "test_current_balance.py")],
        "ohlc": ["pytest", str(tests_dir / "routes" / "test_ohlc.py")],
        "portfolio": ["pytest", str(tests_dir / "routes" / "test_portfolio.py")],
        "qa": ["pytest", str(tests_dir / "routes" / "test_qa_chatbot.py")],
        "trading": ["pytest", str(tests_dir / "routes" / "test_trading.py")],
        "websocket": ["pytest", str(tests_dir / "routes" / "test_websocket_routes.py")],
        "coverage": ["pytest", str(tests_dir), "--cov=routes", "--cov-report=term-missing"],
        "coverage-html": ["pytest", str(tests_dir), "--cov=routes", "--cov-report=html"],
        "verbose": ["pytest", str(tests_dir), "-v"],
    }
    
    if command not in commands:
        print(f"Unknown command: {command}")
        print("Run without arguments to see available commands.")
        sys.exit(1)
    
    exit_code = run_command(commands[command])
    
    if command == "coverage-html" and exit_code == 0:
        print("\n✅ Coverage report generated in 'htmlcov' directory")
        print("Open htmlcov/index.html in your browser to view the report")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

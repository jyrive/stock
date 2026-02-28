"""Tests for list management (portfolio & watchlist) and new commands."""

import os
import tempfile
import pytest


class TestListManagement:
    """Tests for utils/lists.py — file-based ticker management."""

    def setup_method(self):
        """Create temp files for portfolio and watchlist."""
        self._tmp_dir = tempfile.mkdtemp()
        self._orig_p = None
        self._orig_w = None

    def _patch_paths(self):
        """Monkeypatch PORTFOLIO_PATH and WATCHLIST_PATH to temp dir."""
        import utils.lists as lists_mod

        self._orig_p = lists_mod.PORTFOLIO_PATH
        self._orig_w = lists_mod.WATCHLIST_PATH
        lists_mod.PORTFOLIO_PATH = os.path.join(self._tmp_dir, "portfolio.txt")
        lists_mod.WATCHLIST_PATH = os.path.join(self._tmp_dir, "watchlist.txt")

    def teardown_method(self):
        """Restore original paths."""
        if self._orig_p is not None:
            import utils.lists as lists_mod

            lists_mod.PORTFOLIO_PATH = self._orig_p
            lists_mod.WATCHLIST_PATH = self._orig_w
        # Clean up temp files
        import shutil

        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    # ── Portfolio CRUD ───────────────────────────────────────────

    def test_portfolio_starts_empty(self):
        self._patch_paths()
        from utils.lists import portfolio_list

        assert portfolio_list() == []

    def test_portfolio_add(self):
        self._patch_paths()
        from utils.lists import portfolio_add, portfolio_list

        added = portfolio_add(["AAPL", "MSFT"])
        assert added == ["AAPL", "MSFT"]
        assert portfolio_list() == ["AAPL", "MSFT"]

    def test_portfolio_add_no_duplicates(self):
        self._patch_paths()
        from utils.lists import portfolio_add, portfolio_list

        portfolio_add(["AAPL"])
        added = portfolio_add(["AAPL", "GOOGL"])
        assert added == ["GOOGL"]  # Only GOOGL is new
        assert portfolio_list() == ["AAPL", "GOOGL"]

    def test_portfolio_remove(self):
        self._patch_paths()
        from utils.lists import portfolio_add, portfolio_remove, portfolio_list

        portfolio_add(["AAPL", "MSFT", "GOOGL"])
        removed = portfolio_remove(["MSFT"])
        assert removed == ["MSFT"]
        assert portfolio_list() == ["AAPL", "GOOGL"]

    def test_portfolio_remove_nonexistent(self):
        self._patch_paths()
        from utils.lists import portfolio_add, portfolio_remove

        portfolio_add(["AAPL"])
        removed = portfolio_remove(["XYZ"])
        assert removed == []

    # ── Watchlist CRUD ───────────────────────────────────────────

    def test_watchlist_starts_empty(self):
        self._patch_paths()
        from utils.lists import watchlist_list

        assert watchlist_list() == []

    def test_watchlist_add_remove(self):
        self._patch_paths()
        from utils.lists import watchlist_add, watchlist_remove, watchlist_list

        watchlist_add(["V", "MA", "PYPL"])
        assert watchlist_list() == ["V", "MA", "PYPL"]
        watchlist_remove(["MA"])
        assert watchlist_list() == ["V", "PYPL"]

    # ── Cross-list moves ─────────────────────────────────────────

    def test_move_to_portfolio(self):
        self._patch_paths()
        from utils.lists import watchlist_add, move_to_portfolio
        from utils.lists import portfolio_list, watchlist_list

        watchlist_add(["AAPL", "MSFT"])
        moved = move_to_portfolio(["AAPL"])
        assert moved == ["AAPL"]
        assert "AAPL" in portfolio_list()
        assert "AAPL" not in watchlist_list()
        assert "MSFT" in watchlist_list()

    def test_move_to_watchlist(self):
        self._patch_paths()
        from utils.lists import portfolio_add, move_to_watchlist
        from utils.lists import portfolio_list, watchlist_list

        portfolio_add(["AAPL", "MSFT"])
        moved = move_to_watchlist(["MSFT"])
        assert moved == ["MSFT"]
        assert "MSFT" in watchlist_list()
        assert "MSFT" not in portfolio_list()
        assert "AAPL" in portfolio_list()

    # ── Case insensitivity ───────────────────────────────────────

    def test_case_insensitive_add(self):
        self._patch_paths()
        from utils.lists import portfolio_add, portfolio_list

        portfolio_add(["aapl"])
        assert portfolio_list() == ["AAPL"]
        added = portfolio_add(["AAPL"])  # Already exists (uppercased)
        assert added == []

    # ── File format ──────────────────────────────────────────────

    def test_file_has_header(self):
        self._patch_paths()
        from utils.lists import portfolio_add
        import utils.lists as lists_mod

        portfolio_add(["AAPL"])
        with open(lists_mod.PORTFOLIO_PATH) as f:
            content = f.read()
        assert content.startswith("# Portfolio")
        assert "AAPL" in content

    def test_comma_separated_in_file(self):
        """Tickers can be comma-separated on one line."""
        self._patch_paths()
        import utils.lists as lists_mod
        from utils.lists import _read_tickers

        path = lists_mod.PORTFOLIO_PATH
        with open(path, "w") as f:
            f.write("# test\nAAPL, MSFT, GOOGL\n")
        tickers = _read_tickers(path)
        assert tickers == ["AAPL", "MSFT", "GOOGL"]

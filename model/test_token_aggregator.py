
import time
import pytest
from token_aggregator import TokenAggregator


class TestCountBasedAggregation:

    def test_returns_none_before_threshold(self):
        agg = TokenAggregator(max_tokens=3, max_wait_ms=10_000)
        assert agg.add("a") is None
        assert agg.add("b") is None

    def test_flushes_at_max_tokens(self):
        agg = TokenAggregator(max_tokens=3, max_wait_ms=10_000)
        agg.add("a")
        agg.add("b")
        result = agg.add("c")
        assert result == "abc"

    def test_buffer_cleared_after_count_flush(self):
        agg = TokenAggregator(max_tokens=2, max_wait_ms=10_000)
        agg.add("x")
        agg.add("y")
        assert agg.add("z") is None
        assert agg.flush() == "z"

    def test_multiple_batches(self):
        agg = TokenAggregator(max_tokens=2, max_wait_ms=10_000)
        r1 = None
        r2 = None
        for i, tok in enumerate(["a", "b", "c", "d"]):
            result = agg.add(tok)
            if i == 1:
                r1 = result
            if i == 3:
                r2 = result
        assert r1 == "ab"
        assert r2 == "cd"


class TestTimeBasedAggregation:

    def test_time_triggers_flush_on_next_add(self):
        agg = TokenAggregator(max_tokens=100, max_wait_ms=50)
        agg.add("x")
        time.sleep(0.06)
        result = agg.add("y")
        assert result == "xy"

    def test_no_flush_within_window(self):
        agg = TokenAggregator(max_tokens=100, max_wait_ms=200)
        for tok in ["a", "b", "c"]:
            result = agg.add(tok)
            assert result is None

    def test_buffer_cleared_after_time_flush(self):
        agg = TokenAggregator(max_tokens=100, max_wait_ms=30)
        agg.add("p")
        time.sleep(0.04)
        agg.add("q")
        assert agg.flush() is None


class TestForceFlusBeforeDone:

    def test_flush_returns_buffered_content(self):
        agg = TokenAggregator(max_tokens=100, max_wait_ms=10_000)
        agg.add("p")
        agg.add("q")
        result = agg.flush()
        assert result == "pq"

    def test_flush_clears_buffer(self):
        agg = TokenAggregator(max_tokens=100, max_wait_ms=10_000)
        agg.add("a")
        agg.flush()
        assert agg._buffer == []

    def test_double_flush_returns_none(self):
        agg = TokenAggregator(max_tokens=100, max_wait_ms=10_000)
        agg.add("x")
        agg.flush()
        assert agg.flush() is None

    def test_flush_empty_buffer_returns_none(self):
        agg = TokenAggregator(max_tokens=5, max_wait_ms=10_000)
        assert agg.flush() is None

    def test_add_after_flush_starts_new_batch(self):
        agg = TokenAggregator(max_tokens=2, max_wait_ms=10_000)
        agg.add("a")
        agg.flush()
        assert agg.add("b") is None
        assert agg.add("c") == "bc"

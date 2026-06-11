"""
Load Testing for QPLANT API v4.4.0
Tests concurrent user scenarios and performance under load.

Run:
    locust -f locustfile.py --host=http://localhost:8000

    # Headless mode:
    locust -f locustfile.py --host=http://localhost:8000 \
           --headless --users=100 --spawn-rate=10 --run-time=5m \
           --html=reports/load_test.html
"""

from __future__ import annotations

import os
import random

from locust import HttpUser, task, between, tag


class QPLANTAPIUser(HttpUser):
    """Normal production user — simulates typical API usage patterns."""

    wait_time = between(1, 3)

    def on_start(self) -> None:
        """Setup: read API key from environment."""
        self.api_key = os.environ.get("QPLANT_API_KEY", "qplant_TEST_KEY")
        self.headers = {"X-API-Key": self.api_key}

    # ── Read-heavy endpoints (most common) ───────────────────────────

    @task(10)
    @tag("read", "config")
    def get_health(self) -> None:
        """Health check endpoint."""
        self.client.get("/api/v1/health", headers=self.headers)

    @task(8)
    @tag("read", "config")
    def get_config_summary(self) -> None:
        """Fetch SSOT configuration summary."""
        self.client.get("/api/v1/config", headers=self.headers)

    @task(6)
    @tag("read", "config")
    def get_compressor_specs(self) -> None:
        """Fetch compressor specifications."""
        self.client.get("/api/v1/compressors/specs", headers=self.headers)

    @task(5)
    @tag("read", "config")
    def get_config_section(self) -> None:
        """Fetch a specific config section."""
        sections = [
            "flow_parameters",
            "compressor_specifications",
            "financial",
            "pressure_parameters",
        ]
        section = random.choice(sections)
        self.client.get(f"/api/v1/config/{section}", headers=self.headers)

    # ── Calculation endpoints (moderate load) ────────────────────────

    @task(4)
    @tag("compute", "leak-rate")
    def calculate_leak_rate(self) -> None:
        """Calculate a single leak rate."""
        payload = {
            "leak_rate_mbar_l_s": random.uniform(1e-6, 1e-3),
            "temperature_k": random.uniform(4.2, 300),
            "pressure_bar_abs": random.uniform(1, 15),
        }
        self.client.post("/api/v1/leak-rate", json=payload, headers=self.headers)

    @task(2)
    @tag("compute", "leak-rate")
    def calculate_leak_rate_batch(self) -> None:
        """Batch leak-rate calculation."""
        items = [
            {
                "leak_rate_mbar_l_s": random.uniform(1e-6, 1e-3),
                "temperature_k": random.uniform(4.2, 300),
                "pressure_bar_abs": random.uniform(1, 15),
            }
            for _ in range(random.randint(3, 10))
        ]
        payload = {"items": items, "he_price_eur_kg": 120.0}
        self.client.post("/api/v1/leak-rate/batch", json=payload, headers=self.headers)

    @task(3)
    @tag("compute", "compressor")
    def compressor_reliability(self) -> None:
        """Analyze compressor reliability."""
        payload = {
            "total_units": random.choice([3, 4]),
            "required_units": random.choice([2, 3]),
            "mtbf_hours": 8760,
            "mttr_hours": 8,
            "has_vfd": random.choice([True, False]),
        }
        self.client.post(
            "/api/v1/compressors/reliability", json=payload, headers=self.headers
        )

    # ── Heavy endpoints (less frequent) ──────────────────────────────

    @task(1)
    @tag("compute", "monte-carlo")
    def monte_carlo(self) -> None:
        """Run Monte Carlo simulation."""
        payload = {
            "n_simulations": 1000,
            "he_price_min": 80,
            "he_price_mode": 120,
            "he_price_max": 200,
            "geopolitical_disruption_prob": 0.05,
            "include_histogram": False,
        }
        self.client.post("/api/v1/monte-carlo", json=payload, headers=self.headers)

    @task(1)
    @tag("read")
    def visualization_catalog(self) -> None:
        """Fetch visualization catalog."""
        self.client.get("/api/v1/visualizations/catalog", headers=self.headers)

    @task(1)
    @tag("read")
    def build_status(self) -> None:
        """Fetch build status."""
        self.client.get("/api/v1/build/status", headers=self.headers)


class StressTestUser(HttpUser):
    """
    Stress test user — aggressive request pattern to find breaking point.
    Use with --tags stress or by selecting this user class.
    """

    wait_time = between(0.1, 0.5)

    def on_start(self) -> None:
        self.api_key = os.environ.get("QPLANT_API_KEY", "qplant_TEST_KEY")
        self.headers = {"X-API-Key": self.api_key}

    @task(5)
    @tag("stress")
    def rapid_health(self) -> None:
        self.client.get("/api/v1/health", headers=self.headers)

    @task(3)
    @tag("stress")
    def rapid_config(self) -> None:
        self.client.get("/api/v1/config", headers=self.headers)

    @task(2)
    @tag("stress")
    def rapid_leak_rate(self) -> None:
        payload = {
            "leak_rate_mbar_l_s": 1e-4,
            "temperature_k": 300,
            "pressure_bar_abs": 1.013,
        }
        self.client.post("/api/v1/leak-rate", json=payload, headers=self.headers)

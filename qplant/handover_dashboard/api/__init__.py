"""QPLANT Cryogenic Dashboard — REST API Layer

Exposes the Python physics engine, Monte Carlo simulations,
and configuration management as REST endpoints for the
Next.js HBHS Engineering Portal.

Architecture:
    Next.js Frontend  ──HTTP──►  FastAPI (this layer)  ──►  Python Engine (src/)

Endpoints:
    /api/v1/config        — SSoT configuration management
    /api/v1/leak-rate     — Leak-rate physics calculations
    /api/v1/monte-carlo   — Monte Carlo cost sensitivity analysis
    /api/v1/compressors   — HP compressor reliability analysis
    /api/v1/health        — System health & build status
    /api/v1/visualizations — Chart data for Plotly rendering
"""

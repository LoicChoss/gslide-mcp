# Hosted, multi-user gslides-mcp: streamable HTTP on :8000, sign-in with Google.
# Configuration is read from the environment, see src/gslides_mcp/server.py.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never

COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev

# /data is the volume: sign-in sessions (encrypted), themes, components, caches.
RUN useradd --create-home --uid 1000 app && mkdir -p /data && chown app /data
ENV PATH="/app/.venv/bin:$PATH" \
    HOME=/data \
    FASTMCP_HOME=/data/fastmcp \
    FASTMCP_SHOW_SERVER_BANNER=false \
    GSLIDES_MCP_TRANSPORT=http \
    GSLIDES_MCP_PORT=8000
USER app
VOLUME /data
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

CMD ["gslides-mcp"]

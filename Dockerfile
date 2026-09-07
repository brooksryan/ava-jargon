# syntax=docker/dockerfile:1
# The test image. It installs the package the way the README does, with
# `uv tool install`, then runs pytest inside that tool environment. A test
# failure here is a failure a user sees after the documented install. See ./test.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /bin/

# The tool environment lands at a fixed path so PATH can name its python.
ENV UV_LINK_MODE=copy \
    UV_TOOL_DIR=/opt/uv-tools \
    UV_TOOL_BIN_DIR=/usr/local/bin \
    PATH=/opt/uv-tools/ava-jargon/bin:$PATH

WORKDIR /src

# The package and the maintained fixtures.
COPY pyproject.toml README.md gate-contract.md ./
COPY app ./app
COPY fixtures ./fixtures
COPY agents ./agents
COPY skills ./skills
COPY MANIFEST.in Dockerfile test ./
COPY tests ./tests

# The docs tests read the research directory beside the feature docs.
COPY research ./research

# The dev extra holds the test dependencies. EXTRAS=dev,parser adds the spacy
# tier (~500 MB). The layer keeps no cache mount. A cached build of the local
# source once shipped a stale asset. Every rebuild now starts with an empty
# cache.
ARG EXTRAS=dev
RUN uv build --out-dir /artifacts && \
    set -- /artifacts/*.whl && \
    uv tool install "ava-jargon[${EXTRAS}] @ file://$1"

ENV AVA_DIST_DIR=/artifacts
ENTRYPOINT ["python", "-m", "pytest"]

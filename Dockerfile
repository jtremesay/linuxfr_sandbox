FROM ubuntu:latest
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN useradd -ms /bin/sh linuxfr
USER linuxfr

WORKDIR /linuxfr
COPY .python-version ./
RUN uv python install

COPY pyproject.toml uv.lock ./
ENV UV_FROZEN=1
ENV UV_NO_DEV=1
RUN uv sync --no-install-project

COPY README.md manage.py entrypoint.sh run_worker.sh ./
ENTRYPOINT [ "/linuxfr/entrypoint.sh" ]

COPY --chown=linuxfr:linuxfr src src
RUN uv sync
ENV UV_NO_SYNC=1

CMD [ "manage.py", "runserver", "0.0.0.0:8000" ]
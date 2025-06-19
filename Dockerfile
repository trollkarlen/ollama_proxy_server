FROM python:3.13 AS python-base

# https://python-poetry.org/docs#ci-recommendations
ENV POETRY_VERSION=2.1.3
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv

# Tell Poetry where to place its cache and virtual environment
ENV POETRY_CACHE_DIR=/opt/.cache

# Create stage for Poetry installation
FROM python-base AS poetry-base

# Creating a virtual environment just for poetry and install it with pip
RUN python3 -m venv $POETRY_VENV \
	&& $POETRY_VENV/bin/pip install -U pip setuptools \
	&& $POETRY_VENV/bin/pip install poetry==${POETRY_VERSION}

# Copy Poetry to app image
# COPY --from=poetry-base ${POETRY_VENV} ${POETRY_VENV}

# Add Poetry to PATH
ENV PATH="${PATH}:${POETRY_VENV}/bin"

# temp dir
WORKDIR /app-tmp

# Copy Dependencies
COPY --chown=worker:worker poetry.lock pyproject.toml ./

# [OPTIONAL] Validate the project is properly configured
RUN poetry check

# Copy Application
COPY --chown=worker:worker . ./

# build and install the app
RUN poetry build

# Create a new stage from the base python image
FROM python-base AS ollama-proxy-server

RUN adduser worker
WORKDIR /home/worker

# copy wheel and tgz
COPY --from=poetry-base /app-tmp/dist ./dist

RUN pip install dist/*.whl

RUN rm -fr ./dist

# copy entry point
COPY --from=poetry-base /app-tmp/entry-point.sh /

USER worker

# Copy config.ini and authorized_users.txt into project working directory
COPY --chown=worker:worker config.ini .
COPY --chown=worker:worker authorized_users.txt .

# Do not buffer output, e.g. logs to stdout
ENV PYTHONUNBUFFERED=1

# Run Application
EXPOSE 8080
ENTRYPOINT ["/entry-point.sh"]

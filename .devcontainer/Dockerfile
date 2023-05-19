FROM debian:testing

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 python3-dev python-is-python3 python3-venv build-essential libcairo2-dev libgirepository1.0-dev \
    gir1.2-ostree-1.0 gir1.2-appstream-1.0 flatpak

RUN python -m venv /venv && \
    /venv/bin/python -m pip install -U pip 'micropipenv[toml]' && \
    ln -s /venv/bin/pip /usr/local/bin/pip

# COPY pyproject.toml poetry.lock /
# RUN /venv/bin/micropipenv install


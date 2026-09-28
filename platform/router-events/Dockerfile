# python3 + a postgres driver that speaks LISTEN + a socket. That is the whole requirement, and it
# is here because no image in the estate carries all three (see publisher.yaml for the three that
# were tried and how each failed).
FROM docker.io/library/python:3.13-alpine
RUN pip install --no-cache-dir "psycopg[binary]==3.2.3"
COPY publisher.py /app/publisher.py
USER 999
ENTRYPOINT []

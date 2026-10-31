# The known-bad service in its second shape: no .py in the image, but the base image is a
# Python runtime. The gate must refuse this too -- a python base image is python reaching the
# spine even when no python file is copied.
FROM python:3.11-slim-bookworm
WORKDIR /app
COPY broker /app/broker
ENTRYPOINT ["python3", "-m", "broker.serve"]

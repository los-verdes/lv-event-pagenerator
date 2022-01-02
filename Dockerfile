FROM python:3.8

WORKDIR /app

COPY requirements.txt .
RUN pip install \
    --trusted-host pypi.python.org \
    --requirement requirements.txt

COPY ./pagenerator/ ./pagenerator

ENTRYPOINT ["gunicorn", "-b", "0.0.0.0:8080", "pagenerator.app:create_app()", "--log-file", "-"]

FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install \
    --trusted-host pypi.python.org \
    --requirement requirements.txt

COPY ./events_page/ ./events_page

ENTRYPOINT ["gunicorn", "-b", "0.0.0.0:8080", "events_page.app:create_app()", "--log-file", "-"]

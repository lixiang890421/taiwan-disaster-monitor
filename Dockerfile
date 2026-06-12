FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --root-user-action=ignore --disable-pip-version-check -r /tmp/requirements.txt

COPY app /app

ENV TZ=Asia/Taipei
EXPOSE 8080

CMD ["python", "app.py"]

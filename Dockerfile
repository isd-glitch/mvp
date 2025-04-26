FROM mcr.microsoft.com/playwright/python:v1.43.1

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt
RUN playwright install

CMD ["python", "app.py"]

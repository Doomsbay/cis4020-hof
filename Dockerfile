# Reproducible environment for the CIS4020 project (same pins as requirements.txt)
FROM python:3.12-slim

WORKDIR /project
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The project folder (code + data) is mounted at /project at run time, not copied in
EXPOSE 8888
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--ServerApp.token=cis4020"]

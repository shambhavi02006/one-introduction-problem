# Offline CPU-only policy image. No network, GPU or trained assets are needed at inference.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONHASHSEED=0
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY policy.py /app/policy.py
COPY smp /app/smp
COPY LICENSE-networkx.txt /app/LICENSE-networkx.txt
# Pre-compile bytecode: the evaluation container is read-only, so it cannot be written at run time.
RUN python -m compileall -q /app
USER 65534:65534
ENTRYPOINT ["python", "/app/policy.py"]

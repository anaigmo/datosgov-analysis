FROM python:3.11-slim


RUN pip install --no-cache-dir pyshacl

RUN pip install --no-cache-dir rdflib

RUN pip install --no-cache-dir requests

RUN pip install --no-cache-dir DateTime

COPY . .

CMD ["python", "analysis.py"]

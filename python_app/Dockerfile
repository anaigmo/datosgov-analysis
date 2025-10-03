FROM python:3.11-slim


RUN pip install --no-cache-dirpy shacl==0.30.1
RUN pip install --no-cache-dir rdflib==7.2.1
RUN pip install --no-cache-dir requests==2.32.5
RUN pip install --no-cache-dir DateTime==5.5

COPY . .

CMD ["python", "analysis.py"]
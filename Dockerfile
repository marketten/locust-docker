FROM locustio/locust
ENV PORT=8080
COPY locustfile.py .
COPY start.sh .
ENTRYPOINT ["sh","start.sh"]
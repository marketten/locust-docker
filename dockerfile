FROM locustio/locust
COPY locustfile.py .
ENV PORT=8080
EXPOSE $PORT
ENTRYPOINT ["sh","-c","locust --web-port=$PORT"]
FROM python:3.10
ADD . /code
WORKDIR /code
RUN \
    pip install poetry && \
    poetry install
ENV FLASK_APP=notifico:create_app
CMD poetry run notifico run --host 0.0.0.0
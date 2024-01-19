FROM python:3.7

# install gcloud
RUN curl -sSL https://sdk.cloud.google.com | bash
ENV PATH $PATH:/root/google-cloud-sdk/bin
RUN /bin/bash -c "source /root/google-cloud-sdk/completion.bash.inc"

# copy only the requirements to prevent rebuild for any changes
# need to have in subdir of app
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY . /app

WORKDIR /app
RUN pip install -e .

ARG SERVICE_ACCOUNT_KEY
ARG PROJECT_ID


RUN echo "Building backend for $PROJECT_ID"
RUN echo "Using Service Account $SERVICE_ACCOUNT_KEY"


RUN gcloud auth activate-service-account --key-file $SERVICE_ACCOUNT_KEY
RUN gcloud config set project $PROJECT_ID



EXPOSE 5000
ENTRYPOINT ["honcho", "start", "dev", "--no-prefix"]

FROM ubuntu:16.04

ARG TEST_POOL_IP
ARG INDY_POOL_NAME
ARG TAILS_SERVER_SEED

ENV TEST_POOL_IP=${TEST_POOL_IP}
ENV INDY_POOL_NAME=${INDY_POOL_NAME}
ENV TAILS_SERVER_SEED=${TAILS_SERVER_SEED}
ENV BUILD=/root/app-root HOME=/root

WORKDIR ${BUILD}

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    PIPENV_MAX_DEPTH=16 \
    RUST_LOG=error \
    TEST_POOL_IP=${TEST_POOL_IP:-10.0.0.2} \
    HOST_IP=0.0.0.0
RUN  apt-get update \
    && apt-get install -y software-properties-common python-software-properties \
    && add-apt-repository -y ppa:ondrej/php \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
        build-essential \
        pkg-config \
        cmake \
        libssl-dev \
        libsqlite3-dev \
        libsodium-dev \
        libzmq3-dev \
        python3.6 \
        python3.6-dev \
        python3-pip \
        python3-nacl \
        apt-transport-https \
        ca-certificates \
        libtool \
        autoconf \
        automake \
        uuid-dev \
        telnet \
        vim

ADD docker/libindy.so.tgz /usr/lib
RUN chown root:root /usr/lib/libindy.so
COPY src/app/requirements.txt ${HOME}/
COPY docker/docker-entrypoint.sh ${BUILD}/
RUN chmod a+x ${BUILD}/docker-entrypoint.sh

WORKDIR ${HOME}
RUN pip3 install --trusted-host pypi.python.org --upgrade pip==9.0.3
RUN pip3 install --trusted-host pypi.python.org pipenv
RUN pipenv --three --python 3.6
RUN pipenv install --python 3.6 -r ${HOME}/requirements.txt
WORKDIR ${BUILD}

WORKDIR ${HOME}/src
COPY src/app app
RUN sed -i "s/\${TEST_POOL_IP}/${TEST_POOL_IP}/g" app/config/bootstrap/genesis.txn
RUN sed -i "s/\${INDY_POOL_NAME}/${INDY_POOL_NAME}/g" app/config/config.ini
RUN sed -i "s/\${TAILS_SERVER_SEED}/${TAILS_SERVER_SEED}/g" app/config/config.ini

ENTRYPOINT ["pipenv", "run", "/root/app-root/docker-entrypoint.sh"]

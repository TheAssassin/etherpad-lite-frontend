FROM phusion/baseimage:0.9.19

ENV EPF_ROOT "/srv/eplitefrontend"

RUN adduser --system --group --home $EPF_ROOT --disabled-login --disabled-password eplitefrontend

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python2.7-minimal python-virtualenv python2.7-dev python-pip \
    python-setuptools python-wheel libpq-dev abiword build-essential \
    libpcre3-dev nodejs npm nodejs-legacy postgresql-client sudo

ADD ./lib/nginx $EPF_ROOT/lib/nginx
RUN cd $EPF_ROOT/lib/nginx/ && \
    cpucount=$(expr 1 + $(cat /proc/cpuinfo | awk '/^processor/{print $3}' | tail -1)) \
    auto/configure --prefix="$(readlink -f $PWD/../..)" && make -j$cpucount

ADD ./lib/etherpad-lite $EPF_ROOT/lib/etherpad-lite
ADD ./docker/conf/settings.json $EPF_ROOT/lib/etherpad-lite/settings.json
RUN cd $EPF_ROOT/lib/etherpad-lite/ && \
    bin/installDeps.sh && \
    npm install postgresql ep_font_family ep_font_size ep_headings2 ep_author_hover

ADD ./requirements.txt $EPF_ROOT/requirements.txt
RUN pip install -r $EPF_ROOT/requirements.txt psycopg2

ADD ./docker/conf/eplitefrontend.py $EPF_ROOT/conf/eplitefrontend.py

ADD ./docker/runit/supervisord/run /etc/service/supervisord/run
RUN chmod +x /etc/service/*/run

RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

VOLUME ["$EPF_ROOT/var", "$EPF_ROOT/secret_key"]
EXPOSE 18000
WORKDIR $EPF_ROOT

ADD . $EPF_ROOT

RUN sed -i 's/127.0.0.1:18000/0.0.0.0:18000/g' $EPF_ROOT/conf/nginx/nginx.conf

CMD "/sbin/my_init"

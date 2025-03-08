# syntax=docker/dockerfile:1

FROM debian:latest

RUN dpkg --add-architecture i386 && \
 apt-get update && \
 apt-get install -y --no-install-recommends \
 wine \
 wine32 \
 cmake \
 make \
 xvfb \
 ca-certificates \
 cmake \
 git \
 nano \
 wget \
 unzip \
 python3 \
 python-is-python3 \
 python3-pip \
 && \
 rm -rf /var/lib/apt/lists/*

ENV DISPLAY=:0.0
ENV WINEDEBUG=-all
ENV WINEARCH=win32




COPY vc6-toolchain.cmake /opt/work/vc6-toolchain.cmake

COPY tools /opt/work/tools
RUN chmod +x /opt/work/tools/*.py

RUN cd /tmp
RUN wget https://archive.org/download/visual-cpp-60-sp-6/VisualCpp60SP6.zip -O /tmp/VisualCpp60SP6.zip
RUN unzip /tmp/VisualCpp60SP6.zip -d /opt/work/tools

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY build.sh /opt/work/build.sh
RUN chmod +x /opt/work/build.sh

RUN Xvfb :0 -screen 0 1x1x8 &
RUN sleep 2
RUN wine /opt/work/tools/init.bat

WORKDIR /opt/work

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash", "/opt/work/build.sh"]

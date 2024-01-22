FROM harbor.jlgltech.com/qa/python3.8:latest
ENV prod true
EXPOSE 8000
WORKDIR /home/deploy/zero
COPY . .
RUN pip3 install -r requirements.txt -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com &&\
    rm -rf /var/lib/apt/lists/* &&\
    cd .. && mkdir -vp log/zero && mkdir -vp /data/jacoco/report

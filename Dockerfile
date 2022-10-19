FROM osgeo/gdal:latest

WORKDIR  /usr/src/app

RUN apt-get update \
    && apt-get -y install python3 \
    && apt-get -y install python3-pip \
    && apt-get -y install libgeos-dev \
    && apt-get -y install gdal-bin python3-gdal

RUN apt -y install libexpat1

ENV LANG=C.UTF-8

COPY requirements.txt ./

RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "./run.py"]
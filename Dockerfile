FROM    osgeo/gdal:latest

WORKDIR  /usr/src/app

COPY requirements.txt ./

RUN apt update \
    && apt -y install python3 \
    && apt -y install python3-pip \
    && apt -y install libgeos-dev \
    && apt -y install gdal-bin python3-gdal

RUN apt -y install libexpat1

ENV LANG=C.UTF-8

RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "./run.py"]
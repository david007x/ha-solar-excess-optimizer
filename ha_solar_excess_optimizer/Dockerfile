ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache python3 py3-pip

WORKDIR /app
COPY app/ /app/

RUN pip3 install --break-system-packages \
    aiohttp \
    aiofiles \
    pyyaml

# Panel HTML in eigenen Ordner kopieren (run.sh kopiert es nach /config/www)
COPY panel/ /panel/

COPY run.sh /run.sh
RUN chmod +x /run.sh

EXPOSE 8099
CMD ["/run.sh"]

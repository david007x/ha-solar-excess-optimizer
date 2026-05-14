ARG BUILD_FROM
FROM $BUILD_FROM

WORKDIR /app
COPY app/ /app/
COPY panel/ /panel/

RUN pip3 install --break-system-packages \
    aiohttp \
    aiofiles \
    pyyaml

COPY run.sh /run.sh
RUN chmod +x /run.sh

EXPOSE 8099
CMD ["/run.sh"]

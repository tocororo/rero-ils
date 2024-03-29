
FROM docker.uclv.cu/elasticsearch:7.17.1
COPY analysis-icu-7.17.1.zip /opt/analysis-icu-7.17.1.zip
RUN bin/elasticsearch-plugin install file:///opt/analysis-icu-7.17.1.zip

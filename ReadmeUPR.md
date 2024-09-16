


Preguntas para resolver:
1- como meter la data inicial
2- si el host cambia, cual es el estandar para hacerlo.

comparar, si existe, el codigo de  production instances:

[RERO+ network](https://bib.rero.ch/)

[UCLouvain network](https://ils.bib.uclouvain.be/)



Make sure you have enough virtual memory for Elasticsearch in Docker:

# Linux
$ sysctl -w vm.max_map_count=262144


propiedades del host de docker, si es un linux container.
security.nesting: "true"
limits.kernel.memlock unlimited


en docker-services.yml
image: mher/flower:0.9.7


podman build --no-cache --rm -t crai/rero-ils-base:0.1.0 -f Dockerfile.base .


```commandline
(rero-ils-py3.9) malayo@rafael-sceiba-dsti:~/dev/rero/rero-ils/data/upr$ invenio reroils utils marc21tojson -t rero data/upr/db/BECSH/marc21.fix.mrcxml data/upr/db/BECSH/marc21.fix.json data/upr/db/BECSH/marc21.fix.error.mrcxml -v -d

```

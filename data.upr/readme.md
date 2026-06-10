# Proyecto biblioteca de vueltabajo. 

El sistema, ademas de las bibliotecas de la universidad de pinar del rio, funcionara como una nube para las bibliotecas de la Universidad de Pinar del Rio (UPR). 

no se utilizara por el momento ninguna instancia de rero-mef.

El servicio se desplegará en bib.upr.edu.cu

## Configuracion inicial 

- En la carpeta data.upr se colocaran los datos iniciales del sistema en general y los de la universidad de pinar del rio en particular. Se necesitan definir los ficheros json que se crearan en data.upr para inicializar la informacion de la upr

Bibliotecas de la  Universidad de Pinar del Rio (UPR). 
Biblioteca de Ciencias Técnicas BCT
Economía, Ciencias Sociales y Humanísticas - BECSH
Facultad de Cultura Fisica - FCF
Facultad de Ciecias Politicas - FCP

Además incluiremos la Biblioteca Provincial "Ramon Gonzales Coro" perteneciente al Ministerio de Cultura y la Bibliotea Escolar de San Luis, perteneciente al Ministerio de Educacion 


- Es necesario un proceso de importacion de los datos que vienen de la exportacion del sistema antiguo de la UPR, que estan exportados en marc 21 XML. 
El script legacy_import.py intenta importar los datos exportados del sistema anterior a rero. Los datos exportados tienen algun error o el script no funciona totalmente bien. 


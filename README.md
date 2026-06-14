<div id="top"></div>

<!-- PROJECT SHIELDS -->
[![Github actions
status](https://github.com/rero/rero-ils/workflows/CI/badge.svg)](https://github.com/rero/rero-ils/actions?query=workflow%3ACI)
[![image](https://img.shields.io/coveralls/rero/rero-ils.svg)](https://coveralls.io/r/rero/rero-ils)
[![Release
Number](https://img.shields.io/github/tag/rero/rero-ils.svg)](https://github.com/rero/rero-ils/releases/latest)
[![License](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](http://www.gnu.org/licenses/agpl-3.0.html)
[![Gitter
room](https://img.shields.io/gitter/room/rero/reroils.svg)](https://gitter.im/rero/reroils)
[![Translation
status](https://hosted.weblate.org/widgets/rero_plus/-/rero-ils/svg-badge.svg)](https://hosted.weblate.org/engage/rero_plus/?utm_source=widget)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/rero/rero-ils">
    <img src=".github/images/logo-global.svg" alt="RERO ILS" width="80" height="80">
  </a>

<h2 align="center">Biblioteca de Vueltabajo</h2>

  <p align="center">
    Biblioteca virtual pública que integra la información de todos los fondos físicos y digitales de las bibliotecas y centros de documentación de la provincia de Pinar del Río, Cuba.
    <br />
    <strong>Basado en <a href="https://github.com/rero/rero-ils">RERO-ILS</a></strong>
    ·
    <a href="https://ils.test.rero.ch/"><strong>Live Demo »</strong></a>
    ·
    <a href="https://bib.rero.ch/help/home/"><strong>User docs »</strong></a>
    ·
    <a href="https://github.com/rero/developer-resources"><strong>Developer docs »</strong></a>
    <br />
    <br />
    <a href="https://www.rero.ch/produits/ils">Website</a>
    ·
    <a href="https://github.com/rero/rero-ils/issues">Report Bug</a>
    ·
    <a href="https://github.com/rero/rero-ils/issues">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#biblioteca-de-vueltabajo">Biblioteca de Vueltabajo</a></li>
        <li><a href="#built-with">Built with</a></li>
      </ul>
    </li>
    <li>
      <a href="#usage">Usage</a>
      <ul>
        <li><a href="#demo">Demo</a></li>
        <li><a href="#features">Features</a></li>
        <li><a href="#use-rero-ils">Use RERO ILS</a></li>
      </ul>
    </li>
    <li><a href="#getting-started">Getting started</a></li>
      <ul>
        <li><a href="#install">Install</a></li>
        <li><a href="#the-ecosystem">The ecosystem</a></li>
      </ul>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>
<br />

# About the project

<div align="center">
  <a href="https://ils.test.rero.ch/">
    <img src=".github/images/screenshot.png" alt="RERO ILS" style="width:720px">
  </a>
</div>
<br />

## Biblioteca de Vueltabajo

La **Biblioteca de Vueltabajo** es una biblioteca virtual pública desarrollada por la Universidad de Pinar del Río "Hermanos Saíz Montes de Oca" (UPR) en Cuba. Este proyecto integra los recursos bibliográficos físicos y digitales de todas las bibliotecas y centros de documentación de la provincia de Pinar del Río, creando un ecosistema digital unificado y multisectorial.

**Esta implementación está basada en [RERO-ILS](https://github.com/rero/rero-ils)**, un sistema de gestión bibliotecaria de código abierto desarrollado por RERO+ en Suiza, adaptado y configurado para las necesidades específicas del territorio cubano.

### Contexto

Vueltabajo, región ubicada en la provincia de Pinar del Río, Cuba, se distingue por su diversidad geográfica y riqueza histórica. Esta riqueza natural, histórica y productiva demanda un acceso ágil y centralizado al conocimiento generado en y sobre la región. Sin embargo, la fragmentación de la información bibliográfica y la ausencia de plataformas digitales adaptadas impedían que este legado se tradujera en herramientas prácticas para el desarrollo local.

### Solución

La Biblioteca de Vueltabajo surge como respuesta a esta necesidad, aprovechando capacidades técnicas existentes de la UPR y aprendiendo de errores pasados. Su enfoque es integrador y multisectorial, articulando recursos bibliográficos para el desarrollo local, con potencial aplicable a nivel nacional.

### Beneficiarios

* **Red de bibliotecas públicas** (Ministerio de Cultura)
* **Bibliotecas escolares** (Ministerio de Educación)
* **Gobierno Provincial**
* **Asociaciones civiles** (ASCUBI, SOCICT, UIC)
* **Archivo Provincial**
* **Universidad de Pinar del Río**

### Objetivos

* Unificar recursos dispersos bajo una plataforma única con interoperabilidad técnica y gobernanza colaborativa
* Escalar capacidades técnicas hacia un modelo multisectorial usando herramientas de código abierto
* Implementar un modelo de gestión participativa con comité técnico multisectorial
* Convertir la biblioteca en puente entre conocimiento y acción para sectores productivos

## Built with

[![Invenio](https://img.shields.io/badge/Invenio-00b0f0?style=for-the-badge&logo=academia&logoColor=white)](https://github.com/inveniosoftware/invenio)
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://github.com/pallets/flask)
[![Angular](https://img.shields.io/badge/Angular-DD0031?style=for-the-badge&logo=angular&logoColor=white)](https://github.com/angular/angular)
[![ElasticSearch](https://img.shields.io/badge/Elasticsearch-005571?style=for-the-badge&logo=elasticsearch&logoColor=white)](https://github.com/elastic/elasticsearch)
[![Ngx-Formly](https://img.shields.io/badge/Ngx--Formly-1976d2?style=for-the-badge&logo=angular&logoColor=white)](https://github.com/ngx-formly/ngx-formly)

<p align="right">(<a href="#top">back to top</a>)</p>

# Usage

## Demo

Para explorar el sistema, puede visitar la [instancia de prueba](https://ils.test.rero.ch/) o revisar las instancias en producción: [red RERO+](https://bib.rero.ch/) (activa desde verano 2021) y [red UCLouvain](https://ils.bib.uclouvain.be/) (activa desde principios de 2022).

## Features

* :globe_with_meridians: **Modelo consortial:** construido principalmente para redes de bibliotecas, grandes o pequeñas, con varios niveles de configuración (organización, biblioteca).
* :books: **Catálogo y gestión de publicaciones seriadas:** editor de catalogación moderno conforme a estándares actuales (RDA, BibFrame); gestión profunda de periódicos, suscripciones y predicción de números.
* :computer: **Catálogo en línea:** catálogo público en línea con funciones de búsqueda y filtrado simples pero potentes; vistas personalizables por organización y biblioteca; integración perfecta de recursos de plataformas externas (libros electrónicos, bases de datos, etc.).
* :book: **Módulo de circulación:** realiza todas las operaciones requeridas por las bibliotecas: préstamo, devolución, reservas de ítems, gestión de usuarios, préstamos interbibliotecarios, en una interfaz web moderna, rápida y ergonómica.
* :arrows_clockwise: **Interacción de datos y apertura:** datos bibliográficos en formato JSON [modelo Bibframe](https://www.loc.gov/bibframe/) con una API potente para interactuar con la base de datos.

## Use RERO ILS

La Biblioteca de Vueltabajo está basada en **RERO ILS**, un sistema de código abierto que puede ser desplegado y alojado por cualquier persona, siempre que pueda asumir el esfuerzo de configuración o desarrollo requerido. RERO ILS también puede ser alojado [*como servicio*](https://www.rero.ch/en/products/ils#discover) por RERO+ para cualquier biblioteca u organización interesada.

La [documentación de usuario](https://bib.rero.ch/help/home/) para RERO ILS está alojada en [flask-wiki](https://github.com/rero/flask-wiki/).

<p align="right">(<a href="#top">back to top</a>)</p>

# Getting started

## Install

* El proceso de instalación se describe en un [archivo específico](INSTALL.md).
* Para ejecutar un entorno de desarrollo, puede consultar esta [documentación](https://github.com/rero/developer-resources/blob/master/rero-instances/rero-ils/dev_installation.md).

## The ecosystem

### Three GitHub repositories for RERO ILS

El [proyecto rero-ils en GitHub](https://github.com/rero/rero-ils) contiene el proyecto principal para RERO ILS, proporcionando básicamente el backend `invenio`. Para trabajar en el frontend del proyecto, también necesita [rero-ils-ui](https://github.com/rero/rero-ils-ui), que está basado en [ng-core](https://github.com/rero/ng-core).

### MEF

El [MEF](https://github.com/rero/rero-mef) (*Multilingual Entity File*), proporciona autoridades (o entidades) a RERO ILS, en dos idiomas: francés y alemán (por ahora). Esto se utiliza para vincular documentos a descripciones controladas de autores y materias. MEF puede agregar múltiples archivos de autoridad, como [IdRef](https://www.idref.fr/) y [GND](https://www.dnb.de/DE/Professionell/Standardisierung/GND/gnd_node.html). Estos archivos de autoridad se alinean a través de [VIAF](https://viaf.org), proporcionando así autoridades multilingües.

Como resultado, para ejecutar RERO ILS, necesita usar nuestro [servidor MEF público](https://mef.test.rero.ch), o ejecutar el suyo propio.

<p align="right">(<a href="#top">back to top</a>)</p>

# Contact

* Si tiene preguntas, puede preguntar al equipo de desarrollo en [Gitter](https://gitter.im/rero/reroils).
* En caso de un problema de seguridad, por favor contacte a <security@rero.ch>.

<p align="right">(<a href="#top">back to top</a>)</p>

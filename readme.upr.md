# run dev

## add angular projects in dev mode

nvm use v22

uv run scripts/russian_dolls -c ../ng-core/ -u ../rero-ils-ui/

uv run scripts/bootstrap -t ../rero-ils-ui/build/rero-rero-ils-ui-21.0.0.tgz 



## 1- en ng-core

Esta es la libreria base de angular. 

npm install 
npm pack
npm run build-lib

## 2- rero-ils-ui

npm run start-admin-proxy
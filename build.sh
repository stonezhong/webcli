#!/bin/bash

rm -rf dist
pushd src/webcli2/web
rm -rf node_modules
npm install
npm run build-dev

popd
python -m build

#!/bin/bash

python_packages=/usr/local/lib/python3.12/site-packages

export cbr_website_beta=$python_packages/cbr_website_beta/
export cbr_static=$python_packages/cbr_static/

cp -R ./custom/* $python_packages

cd $cbr_website_beta

uvicorn fast_api_main:app --reload --host 0.0.0.0 --port $PORT \
                          --reload-dir $cbr_static             \
                          --reload-dir $cbr_website_beta       \
                          --reload-include '*.html'


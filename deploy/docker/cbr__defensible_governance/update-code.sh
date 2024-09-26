#!/bin/bash

python_packages=/usr/local/lib/python3.12/site-packages


echo "... copying code from custom folder into python site-packages"

#docker exec cbr_custom echo cp -Rv "/app/custom/*" "$python_packages"
docker exec cbr__defensible_governance bash -c "cp -Rv /app/custom/* $python_packages"
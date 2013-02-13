#!/usr/bin/env sh
wget -O- --header 'Content-Type: application/json' --post-file $1 $2

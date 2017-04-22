#!/bin/bash
# restart service
# 2017 03 10 SeJ init

sudo systemctl daemon-reload
sudo service rc.local restart


!#/bin/bash
# stopremove.sh
# 2017-12-16 init SeJ

sudo systemctl status infinitude0.service
sudo systemctl stop infinitude0.service
sudo systemctl disable infinitude0.service

sudo systemctl status infinitude1.service
sudo systemctl stop infinitude1.service
sudo systemctl disable infinitude1.service

sudo systemctl status furnace0.service
sudo systemctl stop furnace0.service
sudo systemctl disable furnace0.service

sudo systemctl status furnace1.service
sudo systemctl stop furnace1.service
sudo systemctl disable furnace1.service

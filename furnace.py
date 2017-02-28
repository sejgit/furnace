#!/usr/bin/env python3
# furnace.py
# communications between Infinity Thermostate, Infinitude Server, & ISY994i controller

# 2017 02 27 SeJ init


###
### imports and parse args
###

### imports
import datetime as dt
import schedule
import time
import logging
import logging.handlers
import os
import sys
import glob
import paul
import argparse
from Adafruit_IO import Client
import json
from pprint import pprint

# parsing
parser = argparse.ArgumentParser(description='Furnace control & data acquisition')
parser.add_argument('-t', '--test', action='store_true',
                    help='offline testing')
parser.add_argument('-d', '--dir', help='home directory')
parser.add_argument('-n', '--name', default='Furnace',
                    help='name label for output like prowl')
parser.add_argument('-s', '--stream', default='furnacemode',
                    help='stream name for AIO')
args = parser.parse_args()

if args.dir:
        dir = os.path.join(args.dir, '')
else:
        dir = '/home/pi/furnace/'

if os.path.isdir(dir):
        print("\n" + dir + "   ***using directory***\n")
else:
        print("\n" + dir + "   ***not a dir***\n")
userdir = os.path.expanduser("~")



###
### get logging going
###

# set up a specific logger with desired output level
LOG_FILENAME = dir + 'furnace.log'

logger = logging.getLogger('FurnaceLogger')

# add the rotating log message handler
fh = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=100000, backupCount=5)
if args.test:
        logger.setLevel(logging.DEBUG)
        fh.setLevel(logging.DEBUG)
else:
        logger.setLevel(logging.INFO)
        fh.setLevel(logging.INFO)

# create formatter and add it to the handlers
formatter = logging.Formatter(fmt='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
fh.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(fh)


logger.info('***start program')
logger.info('using directory  ' + dir)
logger.info('testing = ' + str(args.test))



###
### variables
###

# prowl vars
try:
    p = paul.Paul()

    apikey1 = ""
    with open(os.path.join(userdir, ".ssh/.paul1"), "r") as f:
            apikey1 = f.read()
            apikey1 = apikey1.strip()
except IOError:
    logger.error("Could not read prowl api file")

# AIO vars
try:
    ADAFRUIT_IO_USERNAME = ""
    ADAFRUIT_IO_KEY = ''
    with open(os.path.join(userdir, ".ssh/aio.key"), "r") as f:
            ADAFRUIT_IO_USERNAME = f.readline()
            ADAFRUIT_IO_USERNAME = ADAFRUIT_IO_USERNAME.rstrip()
            ADAFRUIT_IO_KEY = f.readline()
            ADAFRUIT_IO_KEY = ADAFRUIT_IO_KEY.rstrip()
            print("'" + ADAFRUIT_IO_USERNAME + "'")
            print("'" + ADAFRUIT_IO_KEY + "'")
            print("'" + args.stream + "'")
except IOError:
    logger.error("Could not read AIO key file")
aio = Client(ADAFRUIT_IO_KEY)



###
### defined functions
###

# paul prowl push def
def prowl(event, description, pri=None):
        try:
            p = paul.Paul()

            """
            p.push(apikey,
                   args.name,
                   args.event,
                   args.description,
                   url=args.url,
                   priority=args.priority)
            """

            # prowl push to sej
            p.push(apikey1,
                   fishlabel,
                   event,
                   description,
                   url=None,
                   priority=pri)

        except IOError:
            logger.error('prowl error')
        return

# load JSON file
# process JSON file
# get temp
# get activity
# update ISY vars

def load_status():
        with open('status.json') as data_file:
                data = json.load(data_file)
        return data



def read_temp():

        if temp_f > temp_f_hi:
            status = 'hi'
        elif temp_f < temp_f_lo:
            status = 'lo'
        else:
            status = 'ok'
        return temp_f, status

# push temp status to prowl
def pushtempstatus():
    if "status_old" not in pushtempstatus.__dict__: pushtempstatus.status_old = 'first run'
    deg_f, status = read_temp()
    if status != pushtempstatus.status_old:
        prowl('temperature ', (" *** " + status + " " + str(deg_f) + ' ***'), ((status == 'ok') * -2))
        pushtempstatus.status_old = status
    return

# writing of temps
def templog():
    deg_f, status = read_temp()
    templogger.info('{1}, {0:f}'.format(deg_f, status))
    aio.send(args.stream, deg_f)
    return

def dailylog():
    deg_c, deg_f, status = read_temp()
    logger.info('celcius {0:.2f}  fahrenheit {1:.2f}  {2}'.format(deg_c, deg_f, status))
    templogger.info('{2}, {0:.2f}, {1:.2f}'.format(deg_c, deg_f, status))
    aio.send(args.stream, deg_f)
    return


# heartbeat function
def heartbeat(ast):
    if ast==" ":
        ast = "*"
    else:
        ast = " "
    return ast


###
### first run items
###

def scheduling():
    # set scheduled events
    # schedule.every().day.at(start_str).do(relay1_on)  # light/bubbler ON in morning
    # schedule.every().day.at(end_str).do(relay1_off)   # light/bubler OFF at night
    # schedule.every(10).minutes.do(templog)    # log temp to templogger
    # schedule.every().day.do(dailylog)    # daily log temp to logger & temp logger
    # schedule.every(15).minutes.do(pushtempstatus) # push temperature status to prowl
    logger.info('scheduling set')
    return


###
### main loop
###

def main():
    scheduling()
    timestamp = dt.datetime.now().time()
    logger.info('nowtime ='+ str(timestamp)[:5])

    # log & push status on first run
    #dailylog()

    data=load_status()
    hb = "*"
    if args.test:
        pprint()
        return

    while True:
        schedule.run_pending()
        try:
            time.sleep(60) # wait one minute
            hb = heartbeat(hb)
            deg_f, status = read_temp()

            # overlay text onto camera
            with open(dir + 'user_annotate.txt', 'w') as f:
                f.write('celcius {0:.2f}  fahrenheit {1:.2f}  {2}'.format(deg_c, deg_f, status+hb))
                f.closed

        except KeyboardInterrupt:
            print('\n\nKeyboard exception. Exiting.\n')
            logger.info('keyboard exception')
            exit()

        except:
            logger.info('program end:', sys.exc_info()[0])
            exit()
    return


if __name__== '__main__':
    main()
    exit()


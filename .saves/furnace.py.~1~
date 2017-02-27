#!/usr/bin/env python3
# fish tank scheduler & data collector
# thomas & dad
# 2016 06 20
# 2016 06 21 update for logging
# 2016 07 05 added temp prob & overlay to camera
# 2016 07 06 changed logging to complex form
# 2016 07 07 add temperature logging
# 2016 07 17 incorporate temp analysis & plot & external web
# 2016 07 18 change y axis & command line parse
# 2016 07 18 add args for -test -dir -plotonly
# 2016 07 19 prowl warnings & status
# 2016 07 20 fix plots
# 2016 07 21 clean-up .paul files to .ssh
# 2016 09 12 moved to agg away from X
# 2016 09 15 move temp parameters to work with new heater
# 2016 10 19 add relay logic to main loop to fix relay dropping
# 2016 10 31 changed temp raw reading to attempt to fix memory error
# 2016 11 09 if temp ok then send prowl at -2 priority
# 2016 12 22 switch to wiring pi, one relay
# 2016 12 23 add label switch for house with more than one fishtank
# 2016 12 24 add third prowl/paul output
# 2017 02 17 changed from rpi-cam to motioneye, finally round temp to 2 digits
# 2017 02 17 changed temperature annotation file location for above
# 2017 02 23 create adafruit io version -- remove matlib & panda


# todo: add annotation to motioneye camera & perhaps buttons for lights
# todo: make temperature ranges a parameter instead of hard variable

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

# parsing
parser = argparse.ArgumentParser(description='Fishtank control & data aquisition')
parser.add_argument('-t', '--test', action='store_true',
                    help='turn off I/O for offline testing')
parser.add_argument('-d', '--dir', help='home directory')
parser.add_argument('-n', '--name',
                    help='name label for output like prowl')
parser.add_argument('-u', '--upper', default='79.5',
                    help='upper control limit for temperature warnings')
parser.add_argument('-l', '--lower', default='75.5',
                    help='lower control limit for temperature warnings')
parser.add_argument('-s', '--stream', default='fishtemp',
                    help='stream name for AIO')
args = parser.parse_args()

if args.dir:
        dir = os.path.join(args.dir, '')
else:
        dir = '/home/pi/fishtank/'

if os.path.isdir(dir):
        print("\n" + dir + "   ***using directory***\n")
else:
        print("\n" + dir + "   ***not a dir***\n")
userdir = os.path.expanduser("~")

if not args.test:
        import RPi.GPIO as GPIO
if args.name:
        fishlabel=args.name
else:
        fishlabel='Fishtank'

temp_f_hi = float(args.upper)
temp_f_lo = float(args.lower)
temp_c_test = 26


###
### get logging going
###

# set up a specific logger with desired output level
LOG_FILENAME = dir + 'fishtank.log'

logger = logging.getLogger('FishTankLogger')

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


###
### get temperature logging going
###

# set up temp logger with desired output level
TEMP_LOG_FILENAME = dir + 'fishtemp.log'

templogger = logging.getLogger('FishTempLogger')
templogger.setLevel(logging.DEBUG)

# add the rotating log message handler
tfh = logging.handlers.RotatingFileHandler(TEMP_LOG_FILENAME, maxBytes=0, backupCount=5)
tfh.setLevel(logging.DEBUG)

# create formatter and add it to the handlers
tempformatter = logging.Formatter(fmt='%(asctime)s, %(levelname)s, %(message)s', datefmt='%Y-%m-%dT%H:%M:%S')
tfh.setFormatter(tempformatter)

# add the handlers to the logger
templogger.addHandler(tfh)

logger.info('***start program')
logger.info('using directory  ' + dir)
logger.info('testing = ' + str(args.test))
templogger.info('***start program')
templogger.info('testing = ' + str(args.test))


###
### variables
###

# relay variables
if not args.test:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(17, GPIO.OUT)
start = dt.time(5, 30)
start_str = str(start)[:5]
end = dt.time(20, 45)
end_str = str(end)[:5]


# temp prob set-up and vars
if not args.test:
        os.system('modprobe w1-gpio')
        os.system('modprobe w1-therm')

        base_dir = '/sys/bus/w1/devices/'
        device_folder = glob.glob(base_dir + '28*')[0]
        device_file = device_folder + '/w1_slave'

# prowl vars
try:
    p = paul.Paul()

    apikey1 = ""
    with open(os.path.join(userdir, ".ssh/.paul1"), "r") as f:
            apikey1 = f.read()
            apikey1 = apikey1.strip()

    apikey2 = ""
    with open(os.path.join(userdir, ".ssh/.paul2"), "r") as f:
            apikey2 = f.read()
            apikey2 = apikey2.strip()

    apikey3 = ""
    with open(os.path.join(userdir, ".ssh/.paul3"), "r") as f:
            apikey3 = f.read()
            apikey3 = apikey3.strip()

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

            # prowl push to tej
            p.push(apikey2,
                   fishlabel,
                   event,
                   description,
                   url=None,
                   priority=pri)

            # prowl push to csj
            p.push(apikey3,
                   fishlabel,
                   event,
                   description,
                   url=None,
                   priority=pri)

        except IOError:
            logger.error('prowl error')
        return

# temp prob def
def read_temp_raw():
        if not args.test:
                f = open(device_file, 'r')
                lines = f.readlines()
                f.close()
        else:
                lines = ''
        return lines

def read_temp():
        if not args.test:
            lines = read_temp_raw()
            while lines[0].strip()[-3:] != 'YES':
                time.sleep(0.2)
                lines = read_temp_raw()
            equals_pos = lines[1].find('t=')
            if equals_pos != -1:
                temp_string = lines[1][equals_pos+2:]
                temp_c = float(temp_string) / 1000.0
                temp_f = temp_c * 9.0 / 5.0 + 32.0
        else:
            temp_c = temp_c_test
            temp_f = temp_c * 9.0 / 5.0 + 32.0

        if temp_f > temp_f_hi:
            status = 'hi'
        elif temp_f < temp_f_lo:
            status = 'lo'
        else:
            status = 'ok'
        return round(temp_c,2), round(temp_f,2), status

# push temp status to prowl
def pushtempstatus():
    if "status_old" not in pushtempstatus.__dict__: pushtempstatus.status_old = 'first run'
    deg_c, deg_f, status = read_temp()
    if status != pushtempstatus.status_old:
        prowl('temperature ', (" *** " + status + " " + str(deg_f) + ' ***'), ((status == 'ok') * -2))
        pushtempstatus.status_old = status
    return

# relay def
def relay1_on():
    if not args.test:
        GPIO.output(17, GPIO.LOW)
    logger.info('relay1_on')
    return

def relay1_off():
    if not args.test:
        GPIO.output(17, GPIO.HIGH)
    logger.info('relay1_off')
    return


# writing of temps
def templog():
    deg_c, deg_f, status = read_temp()
    templogger.info('{2}, {0:.2f}, {1:.2f}'.format(deg_c, deg_f, status))
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
    schedule.every().day.at(start_str).do(relay1_on)  # light/bubbler ON in morning
    schedule.every().day.at(end_str).do(relay1_off)   # light/bubler OFF at night
    schedule.every(10).minutes.do(templog)    # log temp to templogger
    schedule.every().day.do(dailylog)    # daily log temp to logger & temp logger
    schedule.every(15).minutes.do(pushtempstatus) # push temperature status to prowl
    logger.info('start light on='+ start_str)
    logger.info('end light off='+ end_str)
    return


###
### main loop
###

def main():
    scheduling()
    timestamp = dt.datetime.now().time()
    logger.info('nowtime ='+ str(timestamp)[:5])

    # start or stop light/bubbles
    if start <= timestamp <= end:
        relay1_on()
    else:
        relay1_off()

    # log & push temp on first run
    dailylog()
    pushtempstatus()
    hb = "*"

    while True:
        schedule.run_pending()
        try:
            time.sleep(60) # wait one minute
            hb = heartbeat(hb)
            deg_c, deg_f, status = read_temp()

            # overlay text onto camera
            if not args.test:
                with open(dir + 'user_annotate.txt', 'w') as f:
                    f.write('celcius {0:.2f}  fahrenheit {1:.2f}  {2}'.format(deg_c, deg_f, status+hb))
                f.closed

            # start or stop light/bubbles
            timestamp = dt.datetime.now().time()
            if start <= timestamp <= end:
                relay1_on()
            else:
                relay1_off()

        except KeyboardInterrupt:
            print('\n\nKeyboard exception. Exiting.\n')
            logger.info('keyboard exception')
            GPIO.cleanup()
            exit()

        except:
            logger.info('program end:', sys.exc_info()[0])
            GPIO.cleanup()
            exit()
    return


if __name__== '__main__':
    main()
    exit()


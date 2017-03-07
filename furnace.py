#!/usr/bin/env python3
# furnace.py
# communications between Infinity Thermostate, Infinitude Server, & ISY994i controller

# 2017 02 27 SeJ init
# 2017 03 07 add updateFurnace flog for powl prioritization

###
### imports and parse args
###

### imports
import datetime as dt
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
import requests
import xmltodict

# parsing
parser = argparse.ArgumentParser(description='Furnace control & data acquisition')
parser.add_argument('-t', '--test', action='store_true',
                    help='offline testing')
parser.add_argument('-d', '--dir', help='home directory')
parser.add_argument('-n', '--name', default='Furnace',
                    help='name label for output like prowl')
parser.add_argument('-s', '--stream', default='furnace',
                    help='stream name for AIO')
parser.add_argument('-i', '--index', default=0, type=int,
                    help='furnace index number for ISY vars')
parser.add_argument('-l', '--lower', default=50, type=int,
                    help='lower temperature alarm')
parser.add_argument('-u', '--upper', default=90, type=int,
                    help='upper temperature alarm')

args = parser.parse_args()

args.index = int(args.index) #strange issue when running from crontab vs command


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
            logger.info("AIO stream = '" + args.stream + "'")
except IOError:
    logger.error("Could not read AIO key file")
aio = Client(ADAFRUIT_IO_KEY)

# ISY vars
try:
    isyip = "" # use http://10.0.1.x format
    isylogin = ""
    isypass = ""
    with open(os.path.join(userdir, ".ssh/isy.auth"), "r") as f:
            isyip  = f.readline()
            isyip = isyip.rstrip()
            isylogin  = f.readline()
            isylogin = isylogin.rstrip()
            isypass  = f.readline()
            isypass = isypass.rstrip()
            logger.info("ISY IP = '" + isyip + "'")

except IOError:
    logger.error("Could not read ISY auth file")

transOnOff = {
        'on': 1,
        'off': 0
}
transActivity = {
        'none': 0,
        'wake': 1,
        'away': 2,
        'home': 3,
        'sleep': 4
}

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
                   args.name,
                   event,
                   description,
                   url=None,
                   priority=pri)

        except IOError:
            logger.error('prowl error')
        return


def load_status():
        try:
            with open(os.path.join(dir, 'state/status.json'), "r") as data_file:
                data = json.load(data_file)
        except Exception as error:
                logger.error('load data error ='+str(error))
                return 'fail'
        return data

def load_isy_vars():
        try:
                # get integer variables
                r=requests.get(isyip + '/rest/vars/get/1', auth=(isylogin, isypass))
                if r.status_code != requests.codes.ok:
                        logger.error('isy integer request error ='+str(r.status_code))
                        raise
                isy = xmltodict.parse(r.text)

                # get state value of updateFurnace (means change was ISY pushed)
                r=requests.get(isyip + '/rest/vars/get/1/27'
                               ,auth=(isylogin, isypass))
                if r.status_code != requests.codes.ok:
                        logger.error('isy state request error ='+str(r.status_code))
                        raise
                update = int(xmltodict.parse(r.text))
                logger.info('updateFurnace '+ str(update == 1))
        except:
                logger.error('isy request exception')
                return 'fail'
        return isy, update

def change(data, isy):
        """ # ISY key for vars:
        fnorth, fsouth  index = id - 1
        index=0,1 id=1,2  vacatrunning
        index=2,3 id=3,4  hold
        index=4,5 id=5,6  currentActivity
        index=6,7 id=7,8  rt=temp
        index=8,9 id=9,10 rh=relHumidity """

        f=['vacatrunning','hold','currentActivity','rt', 'rh']
        f[0]=data['status'][0]['vacatrunning'][0]
        f[1]=data['status'][0]['zones'][0]['zone'][0]['hold'][0]
        f[2]=data['status'][0]['zones'][0]['zone'][0]['currentActivity'][0]
        f[3]=data['status'][0]['zones'][0]['zone'][0]['rt'][0]
        f[4]=data['status'][0]['zones'][0]['zone'][0]['rh'][0]

        #i=['vacatrunning','hold','currentActivity','rt', 'rh']
        i=[0,0,0,0,0]
        i[0]=int(isy['vars']['var'][args.index+0]['val'])
        i[1]=int(isy['vars']['var'][args.index+2]['val'])
        i[2]=int(isy['vars']['var'][args.index+4]['val'])
        i[3]=int(isy['vars']['var'][args.index+6]['val'])
        i[4]=int(isy['vars']['var'][args.index+8]['val'])

        c=[True, True, True, True, True]
        c[0] = not (transOnOff[f[0]] == i[0])
        c[1] = not (transOnOff[f[1]] == i[1])
        c[2] = not (transActivity[f[2]] == i[2])
        c[3] = not (float(f[3]) == i[3])
        c[4] = not (float(f[4]) == i[4])

        changemode = True
        changeany = True
        if (not (c[0] or c[1] or c[2])):
                changemode = False
                logger.info('changemode=False')
        else:
                logger.info('changemode=True')
        if (not (c[0] or c[1] or c[2] or c[3] or c[4])):
                changeany = False # no change has happened
                logger.info('changeany=False')
        else:
                logger.info('changeany=True')
        logger.info(f + i + c)
        return changeany, changemode, f, i, c


def update_isy(f, i, c):
        if args.test:
            print('test mode no isy update')
        else:
            x=0
            if c[x]:
                try: # vacatrunning
                    s=isyip+'/rest/vars/set/1/'+str((x*2)+args.index+1)+'/'+str(transOnOff[f[x]])
                    r=requests.get(s, auth=(isylogin, isypass))
                    if r.status_code != requests.codes.ok:
                            logger.error('isy update vac error ='+str(r.status_code))
                except:
                    logger.error('isy update vacatrunning exception')
            x=1
            if c[x]:
                try: # hold
                    r=requests.get(isyip + '/rest/vars/set/1/'
                                  +str((x*2)+args.index+1)+'/'+str(transOnOff[f[x]]),
                                       auth=(isylogin, isypass))
                    if r.status_code != requests.codes.ok:
                            logger.error('isy update hold error ='+str(r.status_code))
                except:
                    logger.error('isy update hold exception')
            x=2
            if c[x]:
                try: # currentActivity
                    r=requests.get(isyip + '/rest/vars/set/1/'
                                  +str((x*2)+args.index+1)+'/'+str(transActivity[f[x]]),
                                       auth=(isylogin, isypass))
                    if r.status_code != requests.codes.ok:
                            logger.error('isy update activity error ='
                                         +str(r.status_code))
                except:
                    logger.error('isy update activity exception')
            x=3
            if c[x]:
                try: # temp
                    s=isyip+'/rest/vars/set/1/'+str((x*2)+args.index+1)+'/'+str(int(float(f[x])))
                    r=requests.get(s, auth=(isylogin, isypass))
                    if r.status_code != requests.codes.ok:
                            logger.error('isy update temp error ='
                                         +str(r.status_code))
                except:
                    logger.error('isy update temperature exception')
            x=4
            if c[x]:
                try: # rh
                    r=requests.get(isyip + '/rest/vars/set/1/'
                                  +str((x*2)+args.index+1)+'/'+str(int(float(f[x]))),
                                       auth=(isylogin, isypass))
                    if r.status_code != requests.codes.ok:
                            logger.error('isy update rh error ='
                                         +str(r.status_code))
                except:
                    logger.error('isy update rh exception')
            try: # furnaceUpdate reset
                r=requests.get(isyip + '/rest/vars/set/2/27/0'
                               ,auth=(isylogin, isypass))
                if r.status_code != requests.codes.ok:
                        logger.error('isy update furnaceUpdate error ='
                                     + str(r.status_code))
            except:
                    logger.error('isy update furnaceUpdate exception')
        return


def update_prowl_mode(f, i, c, update):
        if "status_old" not in update_prowl_mode.__dict__:
                update_prowl_mode.status_old = 'first run'
        else:
                update_prowl_mode.status_old = 'mode change'
        description = 'currAct:'+ f[2] + ' hold:' + f[1] + ' vac:' +f[0]
        logger.info(update_prowl_mode.status_old + ": " + description)
        if args.test:
                print('update_prowl')
        else:
                prowl(update_prowl_mode.status_old, description
                      ,((update == 1) * -2))
        return


def check_temp(temp):
        if temp > args.upper:
            status = 'hi'
        elif temp < args.lower:
            status = 'lo'
        else:
            status = 'ok'
        return status


def prowl_temp(f, i, c, force):
    if "status_old" not in prowl_temp.__dict__:
            prowl_temp.status_old = 'first run'
    status = check_temp(float(f[3]))

    if (status != prowl_temp.status_old or force) and (not args.test):
        prowl('temp ', (" *** " + status + " " + str(f[3]) + ' ***  rh ' + str(f[4])),
              ((status == 'ok') * -2))
        prowl_temp.status_old = status
    return

def aioUpdate(f):
        try:
                activity = args.stream+str(args.index)+'activity'
                temp = args.stream+str(args.index)+'temp'
                rh = args.stream+str(args.index)+'rh'
                aio.send(activity, transActivity[f[2]])
                aio.send(temp, float(f[3]))
                aio.send(rh, float(f[4]))
        except:
                logger.error('AIO request error')
                logger.error(activity)
                logger.error(temp)
                logger.error(rh)

        return


# heartbeat function
def heartbeat(ast):
    if ast==" ":
        ast = "*"
    else:
        ast = " "
    return ast


###
### main loop
###

def main():
    timestamp = dt.datetime.now().time()
    logger.info('nowtime ='+ str(timestamp)[:5])

    # log & push status on first run
    hb = "*"
    while True:
            data=load_status()
            isy, update=load_isy_vars()
            if data =='fail' or isy == 'fail':
                    logger.error('repeat failure: load data or isy')
                    time.sleep(30)
            else:
                    break
    changeany, changemode, f, i, c = change(data, isy)
    if changeany:
            update_isy(f, i, c)
    aioUpdate(f)
    update_prowl_mode(f, i, c, update)
    prowl_temp(f, i, c, True)

    if args.test:
        return

    while True:
        try:
            time.sleep(60) # wait one minute
            hb = heartbeat(hb)
            while True:
                    data=load_status()
                    isy, update=load_isy_vars()
                    if data == 'fail' or isy == 'fail':
                            logger.error('repeat failure: load data or isy')
                            time.sleep(30)
                    else:
                            break
            changeany, changemode, f, i, c = change(data, isy)
            if changeany:
                    update_isy(f, i, c)
                    aioUpdate(f)
            if changemode:
                    update_prowl_mode(f, i, c, update)
            prowl_temp(f, i, c, False)


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


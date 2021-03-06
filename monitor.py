#!/usr/bin/env python
import sys
import os
import datetime
import time
import urllib
import urllib2
import base64
import json
import traceback
import RPi.GPIO as GPIO

#General Options
Green = 8
Yellow = 9
Red = 10
Strobe = 7

# Can't figure out why something isn't working? Turn this on.
DEBUG = False

LoopSleep = 5
# Reverse logic here because a ground for the relay activates it
On = False
Off = True

#Internet monitor options
TestURLList = ["http://www.google.com","http://www.yahoo.com","http://www.twitter.com"]
TestURLTimeout = 5
MonitorSiteURLs = ["[UrlToTest]","[AnotherURLToTest]"]
MonitorSiteTimeout = 6

#Team city monitor options
TeamCityURL = "[TeamcityUrl]/httpAuth/app/rest/builds?locator=running:any"
TeamCityRunningURL = "[TeamcityUrl]/httpAuth/app/rest/builds?locator=running:true"
TeamCityUsername = ""
TeamCityPassword = ""
BuildIdExclusions = ["bt86"] # Ignore builds that always fail for that team that can't get it together
BuildIdStartsWithExclusion = "InDevelopment" # Way to prevent new builds from triggering alarm while being created


def main():
	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(Green,GPIO.OUT)
	GPIO.setup(Yellow,GPIO.OUT)
	GPIO.setup(Red,GPIO.OUT)
	GPIO.setup(Strobe,GPIO.OUT)

	Light(Green,On)
	time.sleep(1)
	Light(Green,Off)
	Light(Yellow,On)
	time.sleep(1)
	Light(Yellow,Off)
	Light(Red,On)
	time.sleep(1)
	Light(Red,Off)
	Light(Strobe,On)
	time.sleep(1)
	Light(Strobe,Off)

	greenState = Off
	yellowState = Off
	redState = Off
	strobeState = Off
	
	while True:
		if hasFailingBuilds():
			console("Build Failure")
			if redState == Off: #wasn't already off, checking to see if this is the loop that turns it on
				os.system('mpg321 SadTrombone.mp3 &')
			redState = On
			greenState = Off
			Light(Red,On)
			Light(Green,Off)
		else:
			debug("Build OK")
			redState = Off
			greenState = On
			Light(Green,On)
			Light(Red,Off)

		if hasRunningBuilds():
			debug("Build Running")
			yellowState = On
			Light(Yellow,On)
		else:
			debug("No Build Running")
			yellowState = Off
			Light(Yellow,Off)
		
		if connectionWorks() and applicationWorks():
			debug("Connection OK")
			strobeState = Off
			Light(Strobe,Off)
		else:
			debug("Connection Failure")
			if strobeState == Off: #wasn't already off, checking to see if this is the loop that turns it on
				os.system('mpg321 SystemIsDown.mp3 &')
			strobeState = On
			Light(Strobe,On)
	
		time.sleep(LoopSleep)

def debug(message):
	if(DEBUG):
		print("%s : %s" % (datetime.datetime.now(), message))

def console(message):
	print("%s : %s" % (datetime.datetime.now(), message))
		
def applicationWorks():
	for i in MonitorSiteURLs:
		try:
			debug(i)
			urllib2.urlopen(i,timeout=MonitorSiteTimeout).close()
		except:
			console(i)
			console(sys.exc_info()[1])
			return False
			#pass

	return True
	


def connectionWorks():
	#rotate the array so we aren't always trying the same outside site
	global TestURLList
	TestURLList = rotate(TestURLList)
	
	for i in TestURLList:
		try:
			debug(i)
			urllib2.urlopen(i,timeout=TestURLTimeout).close()
			return True
		except:
			console(i)
			console(sys.exc_info()[1])
			pass
			
	return False
	
	
def hasFailingBuilds():
	buildData = get_builds(TeamCityURL)
	latestBuilds = get_latest_builds(buildData)
	failures = searchForStatus(latestBuilds, "FAILURE")

	if len(failures) > 0:
		console(failures)
		return True
	else:
		return False

def hasRunningBuilds():
	buildData = get_builds(TeamCityRunningURL)
	latestBuilds = get_latest_builds(buildData)

	if len(latestBuilds) > 0:
		return True
	else:
		return False

def searchForStatus(lastBuildStatus, status):
	matchingBuildTypes = []
	for i in lastBuildStatus:
		if lastBuildStatus[i] == status:
			matchingBuildTypes.append(i)

	return matchingBuildTypes

def get_latest_builds(jsonBuildData):
	lastBuilds = {}
	lastBuildStatus = {}

	if int(jsonBuildData["count"]) > 0:
		for i in jsonBuildData["build"]:
			if i["buildTypeId"].startswith(BuildIdStartsWithExclusion):
				pass
			elif i["buildTypeId"] not in lastBuilds:
				lastBuilds[i["buildTypeId"]] = i.get("number", -1)
				lastBuildStatus[i["buildTypeId"]] = i.get("status","SUCCESS")
			elif int(lastBuilds[i["buildTypeId"]]) < int(i.get("number", -1)):
				lastBuilds[i["buildTypeId"]] = i.get("number", -1)
				lastBuildStatus[i["buildTypeId"]] = i.get("status","SUCCESS")
	
		for i in BuildIdExclusions:
			if i in lastBuilds:
				del lastBuilds[i]
				del lastBuildStatus[i]
				
	return lastBuildStatus
	
def get_builds(url):
	username = TeamCityUsername
	password = TeamCityPassword

	userpass = '%s:%s' % (username, password)	
	
	request = urllib2.Request(url)

	authInfo = base64.encodestring("%s:%s" % (username,password)).replace('\n', '')
	request.add_header("Authorization", "Basic %s" % authInfo)
	request.add_header('Accept', 'application/json')
	response = urllib2.urlopen(request)

	data = json.loads(response.read())
	return data

def Light(pin, status):
	GPIO.output(pin,status)

def rotate(l, y=1):
   if len(l) == 0:
      return l
   y = y % len(l)    # Why? this works for negative y

   return l[y:] + l[:y]


if __name__=="__main__":
	main()

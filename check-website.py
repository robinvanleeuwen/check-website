#!/usr/bin/python3
import socket
from time import sleep
from time import strftime
from docopt import docopt

import urllib3
import requests
import configparser
import sys

DEFAULT_INTERVAL=10
TIMEOUT=5

ARGUMENTS = """Usage: check-website.py [-c <configfile>] | -u <url> [ -i <interval>] | [-h] [-v]

Options:
    -h --help       Show this
    -v --version    Show version
    -c <configfile> Use this as configuration file
    -u <url>        Use this url to check
    -i <interval>   Check interval in seconds, default {0} seconds

""".format(DEFAULT_INTERVAL)

_VERSION_ = "1.1"


class WebsiteChecker():

    doc = None
    websites = dict()
    tcphosts = dict()
    interval = 0
    slack_url = None
    identifier = ""

    def __init__(self):
        self.doc = docopt(ARGUMENTS)

    def run(self):
        self.parse_arguments()
        self.check_websites()

    def parse_arguments(self):

        # Ok you wanted to see the version.
        # Do it and exit.
        if self.doc["--version"]:
            print(_VERSION_)
            sys.exit()

        # Then either a config file is given:
        if self.doc["-c"]:
            self.read_config()

        # Or a single site is given.
        if self.doc["-u"]:
            self.websites[self.doc["-u"]] = "UP"

        self.interval = self.doc["-i"] or DEFAULT_INTERVAL


    def check_websites(self):

        # We do not want to preoccupy us with SSL shit.
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # No need to check NULL websites, we are done.
        print("Cheking {0} sites and {1} TCP hosts".format(len(self.websites), len(self.tcphosts)))

        if len(self.websites) == 0 and len(self.tcphosts) == 0:
            print("Nothing to check...\n")
            sys.exit()

        print("Checking sites:\n")

        for site in self.websites:
            print(site)

        print("\nAnd TCP hosts:\n")

        for host in self.tcphosts:
            print(host)

        print("\nWith an interval of {0} seconds.".format(self.interval))

        while True:

            for site in self.websites:

                if site == "":
                    continue

                print(".", end="")
                sys.stdout.flush()

                timestamp = strftime("%Y-%m-%d %H:%M:%S")

                try:
                    requests.head(site, timeout=10, verify=False)

                    if self.websites[site] == "DOWN":
                        print("Yey! {0} is up again! {1}".format(site, timestamp), end="")
                        sys.stdout.flush()
                        self.sendslack(site, state="up", timestamp=timestamp)
                        self.websites[site] = "UP"
                        continue

                except Exception as e:

                    print("X", end="")
                    sys.stdout.flush()

                    if self.websites[site] == "UP":
                        self.websites[site] = "DOWN"
                        print("{0} IS DOWN! {1}".format(site, timestamp), end="")
                        sys.stdout.flush()
                        self.sendslack(site, state="down", timestamp=timestamp)
                        continue

            for host in self.tcphosts:

                if host == "":
                    continue

                print("t", end="")
                sys.stdout.flush()

                try:
                    self.connect_tcp(host.split(":")[0], host.split(":")[1])

                    if self.tcphosts[host] == "DOWN":
                        print("Yey! {0} is up again! {1}".format(host, timestamp), end="")
                        sys.stdout.flush()
                        self.sendslack(host, state="up", timestamp=timestamp)
                        self.tcphosts[host] = "UP"
                        continue

                except OSError as e:
                    if self.tcphosts[host] == "UP":
                        self.tcphosts[host] = "DOWN"
                        print("{0} IS DOWN! {1}".format(host, timestamp), end="")
                        sys.stdout.flush()
                        self.sendslack(host, state="down", timestamp=timestamp)
                        continue

            sleep(int(self.interval))

    def read_config(self):

        # Read the config file given.
        config = configparser.ConfigParser()
        config.read(self.doc["-c"])

        # Get the settings
        self.interval = config.get("settings", "interval")
        self.identifier = config.get("settings", "identifier")
        self.slack_url = config.get("settings", "slack_url")

        # Declare each site as initiallly UP
        for site in config.get("settings", "sites").split(" "):
            # Scheme must be provided eg: "http://www.google.com" , and not "google.com"
            if site.find("http") == 0:
                self.websites[site] = "UP"

        for host in config.get("settings", "tcp").split(" "):
            if host != "":
                self.tcphosts[host] = "UP"


    def sendslack(self, site, state, timestamp=None):

        # No Slack thus quit.
        if not self.slack_url:
            return
        
        print(self.slack_url)

        if state == "up":

            payload = {
                "text": "{0}: Yey! :+1: :+1: :+1: *{1}* is up again! ({2})".format(self.identifier, site, timestamp)
            }

        elif state == "down":

            payload = {
                "text": "{0}: *{1}* is DOWN :sob: ({2})".format(self.identifier, site, timestamp)
            }

        headers = {'Content-Type': 'application/json'}

        try:
            response = requests.post(self.slack_url, json=payload, headers=headers)
        except Exception as e:
            print(e)


    def connect_tcp(self, address, port):
        address = address.lstrip("\"")
        port = port.rstrip("\"")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((address, int(port)))
        s.close()


if __name__ == "__main__":

    c = WebsiteChecker()
    c.run()

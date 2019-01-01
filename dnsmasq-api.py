#!/usr/bin/env python3

from datetime import tzinfo, timedelta, datetime
import datetime
import subprocess, os, sys, time, uuid, time
import json
import falcon
from wsgiref import simple_server
import threading
sem = threading.Semaphore()


DNSMASQ_LEASES_FILE = '/var/cache/dnsmasq/dnsmasq-dhcp.leasefile'

class LeaseEntry:
    def __init__(self, leasetime, macAddress, ipAddress, name, clientid):
        if (leasetime == '0'):
            self.staticIP = True
        else:
            self.staticIP = False
        self.leasetime_epoch = leasetime
        self.leasetime = datetime.datetime.fromtimestamp(
            int(leasetime)
            ).strftime('%Y-%m-%d %H:%M:%S')
        self.macAddress = macAddress
        self.ipAddress = ipAddress
        self.name = name
        self.clientid = clientid

    def serialize(self):
        return {
            'staticIP': self.staticIP,
            'leasetime': self.leasetime,
            'macAddress': self.macAddress,
            'ipAddress': self.ipAddress,
            'name': self.name,
            'clientid': self.clientid
        }

def leaseSort(arg):
    # Fixed IPs first
    if arg.staticIP == True:
        return 0
    else:
        return arg.name.lower()

def writeLeases(filename, leases):
    # 1546379507 00:e1:8c:94:9d:b9 192.168.1.75 Sandra_Lenovo_wifi 01:00:e1:8c:94:9d:b9

    f = open(filename, "w")
    for l in leases:
        f.write(" ".join([l.leasetime_epoch, l.macAddress, l.ipAddress, l.name, l.clientid]))
        f.write("\n")
    f.flush()
    f.close()


def getLeases():
    leases = list()
    with open(DNSMASQ_LEASES_FILE) as f:
        for line in f:
            elements = line.split()
            if len(elements) == 5:
                entry = LeaseEntry(elements[0],
                           elements[1],
                           elements[2],
                           elements[3],
                           elements[4])
                leases.append(entry)

    # leases.sort(key = leaseSort)
    return leases

def getLeasesJson():
    leases = getLeases()
    s = [lease.serialize() for lease in leases]
    return json.dumps(s)


def get_chunked_input(req):
    CHUNK_SIZE_BYTES = 4096

    big_chunk = bytes()
    while True:
        chunk = req.stream.read(CHUNK_SIZE_BYTES)
        if not chunk:
            break

        big_chunk = big_chunk + chunk

    return big_chunk

def convert_raw_as_json_to_obj(b):
    # Decode UTF-8 bytes to Unicode, and convert single quotes
    # to double quotes to make it valid JSON

    my_json = b.decode('utf8').replace("'", '"')
    return json.loads(my_json)



class DNSMasqAPI:
    def on_get(self, req, res):
        try:
            res.body = getLeasesJson()
            res.status = falcon.HTTP_200
        except:
            res.status = falcon.HTTP_500

    def on_delete(self, req, res):
        body = req.stream.read()
        try:
            j = convert_raw_as_json_to_obj(body)
        except:
            print("Syntax error in the JSON")
            res.status = falcon.HTTP_400
            return

        try:
            leases = getLeases()
        except:
            print("Can't retrieve lease file")
            res.status = falcon.HTTP_500
            return

        # When an logical-and is given
        if 'and' in j:
            print("Got AND clause")
            if 'ip' in j['and'] and 'macaddr' in j['and']:
                print("You have ip and macaddr")
                for l in leases:
                    if l.ipAddress == j['and']['ip'] and l.macAddress == j['and']['macaddr']:
                        print("Found IP and Mac combo")
                        leases.remove(l)
                        writeLeases(DNSMASQ_LEASES_FILE, leases)
                        res.status = falcon.HTTP_204
                        return

            elif 'ip' in j['and'] and 'name' in j['and']:
                print("You have ip and name")
                for l in leases:
                    if l.ipAddress == j['and']['ip'] and l.name == j['and']['name']:
                        print("Found IP and Mac combo")
                        leases.remove(l)
                        writeLeases(DNSMASQ_LEASES_FILE, leases)
                        res.status = falcon.HTTP_204
                        return
            else:
                print("The AND-clause not supported")
                res.status = falcon.HTTP_400
                return

        # When a bare lookup is requested
        else:
            if 'ip' in j:
                for l in leases:
                    if l.ipAddress == j['ip']:
                        print("Found it")
                        leases.remove(l)
                        writeLeases(DNSMASQ_LEASES_FILE, leases)
                        res.status = falcon.HTTP_204
                        return
            if 'macaddr' in j:
                for l in leases:
                    if l.macAddress == j['macaddr']:
                        print("Found it")
                        leases.remove(l)
                        writeLeases(DNSMASQ_LEASES_FILE, leases)
                        res.status = falcon.HTTP_204
                        return
            else:
                print("Unfulfilled search criteria")
                res.status = falcon.HTTP_400
                return

        # Nothing found to do
        res.status = falcon.HTTP_404

    def on_head(self, req,res):
        leases = getLeases()
        writeLeases("/tmp/test.leases", leases)
        res.status = falcon.HTTP_204

    def on_patch(self, req, res):
        try:
            b = get_chunked_input(req)
            j = convert_raw_as_json_to_obj(b)
        except:
            res.status = falcon.HTTP_400
            return

        print(json.dumps(j))

        res.status = falcon.HTTP_200

    def on_post(self, req, res):
        try:
            b = get_chunked_input(req)
            j = convert_raw_as_json_to_obj(b)
        except:
            res.status = falcon.HTTP_400
            return

        res.status = falcon.HTTP_200


### Main
if __name__ == "__main__":
    import argparse

    # Init
    PATH = os.path.dirname(os.path.realpath(__file__)) + '/'

    # Parser
    parser = argparse.ArgumentParser(os.path.basename(__file__))
    parser.add_argument("--port",
                        help="Listening port number (default is 5000, can also listen to a range, like 5000-5010).",
                        type=str)
    parser.add_argument("--host",
                        default='127.0.0.1',
                        help="Listening on IP-address (default is 127.0.0.1).",
                        type=str)
    args = parser.parse_args()
    host = args.host

    # Start
    api = falcon.API()
    route_dnsmasq = '/dnsmasq/leases'
    api.add_route(route_dnsmasq, DNSMasqAPI())
    print("Loaded route: " + route_dnsmasq)

    port      = 0
    from_port = 0
    to_port   = 0
    bind_complete = False

    if args.port:
        try:
            port = int(args.port)
        except:
            try:
                from_port = int(args.port.split('-')[0])
                to_port   = int(args.port.split('-')[1])
            except:
                print("Error: parse error in port assignment:", args.port, "Format example is: 5000 or 5000-5010")
                sys.exit(1)

            if not from_port <= to_port:
                print("Error: port range must start with a smaller port number and range to an upper port number")
                sys.exit(1)
    else:
        port = 5000

    # Bind to a port or free port
    if port != 0:
        try:
            httpd = simple_server.make_server(host, port, api)
            bind_complete = True
        except:
            print("Can't bind interface to", host, port, "possibly already in use")
            sys.exit(1)
    else:
        for port in range(from_port, to_port + 1):
            try:
                httpd = simple_server.make_server(host, port, api)
                bind_complete = True
                break
            except:
                pass
                continue

    if not bind_complete:
        if from_port != 0:
            print("Could not bind to port range", from_port, "to", to_port, "on interface", host)
        else:
            print("Could not bind to port", port, "on interface", host)
        sys.exit(1)

    print("Operating on", host, "port", port, "from current working dir", PATH)
    httpd.daemon_threads = True
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Service stopped by user.")
        pass

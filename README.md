# rest-2-dnsmasq
REST api to DNSMasq

Author: Oscar Koeroo
E-mail: okoeroo@gmail.com


## Command line paramters

Status code | Meaning
----------- | -------
`--port <port>` | Listening port number. Default: 5000. Alternative: 5000-5010, to look for a free port number to bind on in this range.
`--host <ip address>` | Listening IP address. Default: 127.0.0.1. To listen on all interfaces uses 0.0.0.0


## API - /dnsmasq/leases

### GET
Returns a dump of the lease file.

Input: none
Output: leases file encoded in JSON

Status code | Meaning
----------- | -------
200 | Returning leases information in JSON
500 | Could not retrieve leases file.

### DELETE
Removes one lease from the leases file based on search criteria.

Input header: Content-Type: application/json
Input data: search criteria.
Output: none.

Status code | Meaning
----------- | -------
200 | Returning leases information in JSON
500 | Could not retrieve leases file.

#### Search by MAC Address:
`{ "macaddr": "52:54:00:91:57:1f" }`

#### Search by IP Address:
`{ "ip": "192.168.1.107" }`

#### Search by IP address and Mac address:
`{ "and": { "ip": "192.168.1.107", "macaddr": "52:54:00:91:57:1F" } }`

#### Search by IP address and Name:
`{ "and": { "ip": "192.168.1.107", "name": "localhost" } }`

### HEAD
Dumps the leases file through the parses and writes it to /tmp/test.leases for evaluation.



import urllib.parse
import geoip2.database
import socket
import json
import subprocess
from subprocess import PIPE
from decimal import Decimal
from geoip2.errors import AddressNotFoundError

# MaxMind databases
GEOIP_CITY = geoip2.database.Reader("geoip/GeoLite2-City.mmdb")
GEOIP_COUNTRY = geoip2.database.Reader("geoip/GeoLite2-Country.mmdb")
ASN = geoip2.database.Reader("geoip/GeoLite2-ASN.mmdb")

def parse_hostport(hp):
    # urlparse() and urlsplit() insists on absolute URLs starting with "//"
    result = urllib.parse.urlsplit('//' + hp)
    return result.hostname, result.port

def raw_hostname(address):
    """
    Resolves hostname for the specified address using reverse DNS resolution.
    """
    hostname = address
    try:
        hostname = socket.gethostbyaddr(address)[0]
    except (socket.gaierror, socket.herror) as err:
        print(err)
    return hostname

def raw_geoip(address):
    """
    Resolves GeoIP data for the specified address using MaxMind databases.
    """
    country = None
    city = None
    lat = 0.0
    lng = 0.0
    timezone = None
    asn = None
    org = None

    prec = Decimal('.000001')

    if not address.endswith(".onion"):
        try:
            gcountry = GEOIP_COUNTRY.country(address)
        except AddressNotFoundError:
            pass
        else:
            country = gcountry.country.iso_code

        try:
            gcity = GEOIP_CITY.city(address)
        except AddressNotFoundError:
            pass
        else:
            city = gcity.city.name
            if gcity.location.latitude is not None and \
                    gcity.location.longitude is not None:
                lat = float(Decimal(gcity.location.latitude).quantize(prec))
                lng = float(Decimal(gcity.location.longitude).quantize(prec))
            timezone = gcity.location.time_zone

    if address.endswith(".onion"):
        asn = "TOR"
        org = "Tor network"
    else:
        try:
            asn_record = ASN.asn(address)
        except AddressNotFoundError:
            pass
        else:
            asn = 'AS{}'.format(asn_record.autonomous_system_number)
            org = asn_record.autonomous_system_organization

    return (city, country, lat, lng, timezone, asn, org)


proc = subprocess.run("curl -s https://seeds.tamami-foundation.org/seeds.txt | grep '    1 '", shell=True, text=True)

seeds_list = []
with open('seeds.txt', mode='rt', encoding='utf-8') as f:
	for line in f:
		l = line.split()
		del l[1]
		del l[2:7]
		l2 = parse_hostport(l[0])
		hn = raw_hostname(l2[0])
		info = raw_geoip(l2[0])

		l3 = [l2[0],l2[1],int(l[4]),l[5].strip('"'),int(l[1]),int("0x"+ l[3], 0),int(l[2]),hn,info[0],info[1],info[2],info[3],info[4],info[5],info[6]]
		seeds_list.append(l3)

with open('../dnsseeddata/map_plot.json', 'w') as f:
	f.write(json.dumps(seeds_list))

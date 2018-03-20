import logging
import os
from dns.resolver import Timeout
import arrow

from csirtg_indicator import resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
from cif.utils import resolve_ns
from csirtg_indicator import Indicator
from .constants import ENABLED


def process(i):
    if not ENABLED:
        return

    if i.itype != 'fqdn':
        return

    if 'search' in i.tags:
        return

    try:
        r = resolve_ns(i.indicator)
    except Timeout:
        return

    rv = []

    for rr in r:
        if str(rr).rstrip('.') in ["", 'localhost']:
            continue

        ip = Indicator(**i.__dict__())
        ip.indicator = str(rr)
        ip.lasttime = arrow.utcnow()

        try:
            resolve_itype(ip.indicator)
        except InvalidIndicator:
            continue

        ip.itype = 'ipv4'
        ip.rdata = i.indicator
        ip.confidence = (ip.confidence - 4) if ip.confidence >= 4 else 0
        rv.append(ip)

    return rv
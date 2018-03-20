from csirtg_indicator import Indicator, resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
import arrow


def process(i):
    if i.itype != 'fqdn':
        return

    if 'search' in i.tags:
        return

    if not i.is_subdomain():
        return

    fqdn = Indicator(**i.__dict__())
    fqdn.indicator = i.is_subdomain()
    fqdn.lasttime = arrow.utcnow()

    try:
        resolve_itype(fqdn.indicator)
    except InvalidIndicator as e:
        return

    fqdn.confidence = (fqdn.confidence - 3) if fqdn.confidence >= 3 else 0
    return fqdn
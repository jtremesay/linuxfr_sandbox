from datetime import datetime

from ninja import Schema

from linuxfr.models import ChangeFrequency, Kind


class SitemapEntry(Schema):
    location: str
    kind: Kind
    last_modified: datetime
    change_frequency: ChangeFrequency
    priority: float

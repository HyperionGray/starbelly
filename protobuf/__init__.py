from uuid import UUID

import dateutil.parser
from datetime import timezone


def pb_date(pb, date_attr):
    if pb.HasField(date_attr):
        dt = dateutil.parser.parse(getattr(pb, date_attr))
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = None
    return dt

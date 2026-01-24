# Python imports
from datetime import date, datetime

# Third-party imports
import pytz


async def user_timezone_converter(user, input_date=None):
    if user is None or input_date is None:
        return None

    user_timezone = user.user_timezone or None
    if not user_timezone:
        return input_date

    try:
        tz = pytz.timezone(user_timezone)
    except pytz.UnknownTimeZoneError:
        return input_date

    # Ensure input_date is datetime or date
    if isinstance(input_date, datetime):
        converted_date = input_date.astimezone(tz)
    elif isinstance(input_date, date):
        converted_date = datetime.combine(input_date, datetime.min.time()).astimezone(tz)
    else:
        return input_date

    return converted_date

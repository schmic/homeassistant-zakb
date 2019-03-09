"""
A component/platform which allows you to get garbage collection dates from ZAKB
https://www.zakb.de/

For more details about this component, please refer to the documentation at
https://github.com/schmic/homeassistant-zakb
"""

import logging

import homeassistant.util.dt as dt_util
from homeassistant.util import Throttle

from homeassistant.components.calendar import (CalendarEventDevice)

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['MechanicalSoup==0.11.0', 'asgiref==2.3.2']

MIN_TIME_BETWEEN_UPDATES = dt_util.dt.timedelta(hours=3)

CONF_DEVICE_ID = 'device_id'

COLLECTIONS = ['R', 'B', 'P', 'G']

CONF_HOURS = "hours"
CONF_TOWN = "town"
CONF_STREET = "street"
CONF_STREET_NR = "street_nr"


def setup_platform(hass, config, add_devices, discovery_info=None):
    _LOGGER.info("ZAKB setup_platform")

    calendar_devices = []
    for collection in COLLECTIONS:
        device_data = {
            CONF_DEVICE_ID: "zakb_" + collection
        }

        device = ZakbCalendarEventDevice(hass, device_data, collection, config)
        calendar_devices.append(device)

    add_devices(calendar_devices)


class ZakbCalendarEventDevice(CalendarEventDevice):
    def __init__(self, hass, device_data, collection, config):
        self.data = ZakbCalendarData(collection, config)
        super().__init__(hass, device_data)

    async def async_update(self):
        from asgiref.sync import sync_to_async
        self.data.event = await sync_to_async(self.data.get_event)()
        _LOGGER.debug(
            "Data AsyncUpdate() event: ({}) {}".format(
                self.data.collection, self.data.event))
        super().update()


class ZakbCalendarData(object):
    def __init__(self, collection, config):
        self.collection = collection
        self.config = config
        self.event = None

    def update(self):
        return True

    def parse_d_str(self, date_string):
        from datetime import datetime as dt
        date_string = self.replace_month(date_string).split(", ", 1)[1]
        parsed_dt = dt.strptime(date_string, "%B %d, %Y")
        return parsed_dt

    def replace_month(self, date_string):
        import re

        d = {
            'Januar': 'January',
            'Februar': 'February',
            'März': 'March',
            'April': 'April',
            'Mai': 'May',
            'Juni': 'June',
            'Juli': 'July',
            'August': 'August',
            'September': 'September',
            'Oktober': 'October',
            'November': 'November',
            'Dezember': 'December'
        }

        pattern = re.compile(r'\b(' + '|'.join(d.keys()) + r')\b')
        return pattern.sub(lambda x: d[x.group()], date_string)

    def get_event(self):
        import mechanicalsoup
        try:
            browser = mechanicalsoup.StatefulBrowser()
            browser.open(
                'https://www.zakb.de/online-service/online-service/abfallkalender/'
            )
            browser.set_verbose = 1

            form = browser.select_form('#athos-os-form')
            form.set_select({
                "aos[Ort]": self.config[CONF_TOWN]
            })
            browser.submit_selected()

            form = browser.select_form('#athos-os-form')
            form.set_select({
                "aos[Strasse]": self.config[CONF_STREET]
            })
            form.set("aos[Hausnummer]", self.config[CONF_STREET_NR])
            form.set("aos[Hausnummerzusatz]", "")
            form.set("aos[Zeitraum]", "Die Leerungen der nächsten 4 Wochen")
            form.set("submitAction", "nextPage")
            form.set("pageName", "Lageadresse")
            browser.submit_selected()
        except mechanicalsoup.LinkNotFoundError:
            _LOGGER.warn("Could not setup ZAKB:{}, website unavailable".format(
                self.collection))
            return None

        for td in browser.get_current_page().select('td.highlighted'):
            for event in td.select('div.cal-event'):
                collection_type = event.text
                if self.collection == collection_type:
                    collection_title = event.attrs['title']
                    collection_date = self.parse_d_str(td.attrs['title'])

                    start_time = collection_date - \
                        dt_util.dt.timedelta(hours=self.config[CONF_HOURS])
                    end_time = collection_date + \
                        dt_util.dt.timedelta(hours=self.config[CONF_HOURS])

                    return {
                        'start': {
                            'dateTime': start_time.isoformat()
                        },
                        'end': {
                            'dateTime': end_time.isoformat()
                        },
                        'description': collection_title
                    }

        return None

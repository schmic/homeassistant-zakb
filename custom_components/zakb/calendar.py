"""
A component/platform which allows you to get garbage collection dates from ZAKB
https://www.zakb.de/

For more details about this component, please refer to the documentation at
https://github.com/schmic/homeassistant-zakb
"""

import logging
import voluptuous as vol
from datetime import timedelta

import homeassistant.helpers.config_validation as cv

from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.helpers.template import DATE_STR_FORMAT
from homeassistant.components.calendar import (CalendarEventDevice)

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['MechanicalSoup==0.11.0']

CONF_NAME = 'name'
CONF_DEVICE_ID = 'device_id'

ZAKB_URL = 'https://www.zakb.de/online-service/online-service/abfallkalender/'
COLLECTIONS = {
    'R': 'Restabfallbehälter',
    'B': 'Bioabfallbehälter',
    'P': 'Papierbehälter',
    'G': 'Gelber Sack'
}

CONF_OFFSET = "offset"
CONF_TOWN = "town"
CONF_STREET = "street"
CONF_STREET_NR = "street_nr"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_TOWN): cv.string,
    vol.Required(CONF_STREET): cv.string,
    vol.Required(CONF_STREET_NR): cv.string,
    vol.Optional(CONF_OFFSET, default=timedelta(hours=6)): cv.time_period,
    vol.Optional(CONF_SCAN_INTERVAL, default=timedelta(hours=3)): cv.time_period
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    scan_interval = config.get(CONF_SCAN_INTERVAL)

    calendar_devices = []
    for collection in COLLECTIONS:
        device_data = {
            CONF_NAME: "{} - ZAKB".format(COLLECTIONS[collection]),
            CONF_DEVICE_ID: "zakb_{}".format(collection)
        }
        calendar_data = ZakbCalendarData(
            collection, config, hass.config.time_zone)
        device = ZakbCalendarEventDevice(hass, device_data, calendar_data)
        calendar_devices.append(device)

    add_devices(calendar_devices)


class ZakbCalendarEventDevice(CalendarEventDevice):
    def __init__(self, hass, device_data, calendar_data):
        self.hass = hass
        self.data = calendar_data
        super().__init__(hass, device_data)

    async def async_update(self):
        self.data.event = await self.hass.async_add_job(self.data.get_event)
        _LOGGER.info(
            "Device AsyncUpdate() event: ({}) {}".format(
                self.data.collection, self.data.event))
        super().update()


class ZakbCalendarData(object):
    def __init__(self, collection, config, tz):
        self.collection = collection
        self.config = config
        self.tz = tz
        self.event = None

    def update(self):
        return True

    def get_event(self):
        td_highlights = self.get_data()

        if td_highlights is None:
            return None

        for td in td_highlights:
            for event in td.select('div.cal-event'):
                collection_type = event.text
                if self.collection == collection_type:
                    collection_title = event.attrs['title']
                    collection_date = self.parse_d_str(td.attrs['title'])

                    start_time = collection_date - self.config.get(CONF_OFFSET)
                    end_time = collection_date + self.config.get(CONF_OFFSET)

                    _LOGGER.info("date: {} {} {}".format(
                        collection_title, start_time, end_time))

                    return {
                        'start': {
                            'dateTime': start_time.strftime(DATE_STR_FORMAT)
                        },
                        'end': {
                            'dateTime': end_time.strftime(DATE_STR_FORMAT)
                        },
                        'description': collection_title
                    }

        return None

    def get_data(self):
        import mechanicalsoup
        try:
            browser = mechanicalsoup.StatefulBrowser()
            browser.open(ZAKB_URL)

            form = browser.select_form('#athos-os-form')
            form.set_select({
                "aos[Ort]": self.config.get(CONF_TOWN)
            })
            browser.submit_selected()

            form = browser.select_form('#athos-os-form')
            form.set_select({
                "aos[Strasse]": self.config.get(CONF_STREET)
            })
            form.set("aos[Hausnummer]", self.config.get(CONF_STREET_NR))
            form.set("aos[Hausnummerzusatz]", "")
            form.set("aos[Zeitraum]", "Die Leerungen der nächsten 4 Wochen")
            form.set("submitAction", "nextPage")
            form.set("pageName", "Lageadresse")
            browser.submit_selected()
            return browser.get_current_page().select('td.highlighted')
        except mechanicalsoup.LinkNotFoundError:
            _LOGGER.warn("Could not setup ZAKB:{}, website unavailable".format(
                self.collection))
            return None

    def parse_d_str(self, date_str):
        from datetime import datetime as dt
        from pytz import utc, timezone

        date_str = self.replace_month(date_str).split(", ", 1)[1]
        date_tz = self.tz.localize(
            dt.strptime(date_str, "%B %d, %Y"))

        return date_tz.astimezone(utc)

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

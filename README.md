# Home-Assistant ZAKB Component

**Zweckverband Abfallwirtschaft Kreis Bergstraße** ([ZAKB](https://www.zakb.de)) is reponsible for the garbage collection at Kreis Bergstraße in Germany.

The component lets you configure your address and gets the next upcoming date for the clearances of your garbage.

The component currently gets dates for:
- Restmüll
- Biomüll
- Gelber Sack
- Papiermüll

## Installation
Copy the content of the repository into your `/config` folder, so you end with `/config/custom_components/zakb/calendar.py`


## Configuration
Put your address in `town`, `street` and `street_nr`.

The `hours` option defines from what time +/- around midnight the event is active (`state: on`)

    calendar:
        - platform: zakb
          hours: 5
          town: !secret zakb_town
          street: !secret zakb_street
          street_nr: !secret zakb_street_nr

With that example the `state: on` is from 7pm to 5am.

More information about Home-Assistant [secrets](https://www.home-assistant.io/docs/configuration/secrets/).

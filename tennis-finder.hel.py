# import argparse   # TODO XXX
import logging

# import os     # TODO XXX
from datetime import date, datetime, timedelta
from pprint import pp
from sys import exit
from urllib.parse import parse_qs, urlparse
import requests
from bs4 import BeautifulSoup
from requests.exceptions import ConnectionError

# XXX to be removed/ changed logging level in PROD
logging.basicConfig(
    level=logging.ERROR, format="%(levelname)s - %(asctime)s: %(message)s"
)

# PARAMETERS
WORKDAYS = (1, 2, 3, 4, 5)
WEEKENDS = (6, 7)
START_HOUR = 16
END_HOUR = 21
MAX_COURT_NO = 30  # maximum number of valid court; the rest are ball cannons
# websites return _currently_ maximum of +4 weeks (28 days) forward
PLUS_DAYS_MAX = 6  # 4*7      # XXX return to 4*7 value!

CENTERS = {
    # XXX uncomment!
    "smash": {"url": "https://smashcenter.slsystems.fi", "name_nice": "Smash"},
    # Tali moved to new system at https://talitaivallahti.feel.cintoia.com/
    "tali": {"url": "https://varaukset.talintenniskeskus.fi", "name_nice": "Tali"},
    "mandatumcenter": {
        "url": "https://play.fi/mandatumcenter",
        "name_nice": "Puhos/MandatumCenter",
    },
    "mailapelikeskus": {
        "url": "https://play.fi/mailapelikeskus",
        "name_nice": "Helsingin Mailapelikeskus",
    },
}

# Data structure to store results from all tennis centers:
# {center:
#       [
#        { date: thedate,
#          availabilities: [{'time':xx, 'duration': yy, 'court': zz}, ..]  # = parse_results()
#        },
#        ..
#       ],
# }
all_results = {cname: [] for cname in CENTERS}


def fetch_raw_data(
    baseurl: str, the_date: str, book_path: str = "/booking/booking-calendar"
) -> str:
    """Fetches web-page
       See https://www.scrapehero.com/how-to-fake-and-rotate-user-agents-using-python-3/

    Args:
        baseurl (str): base url
        the_date (str): date parameter in 'YYYY-MM-DD' format
        book_path (str, optional): booking path of the url. Defaults to '/booking/booking-calendar'.

    Returns:
        str | None: returns web-page source, may be None
    """

    # TODO: try asyncio XXX

    url = baseurl + book_path

    headers = {
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Sec-GPC": "1",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Accept-Language": "en-GB,en;q=0.9",
    }

    params = (
        ("BookingCalForm[p_laji]", "1"),  # tennis = 1
        ("BookingCalForm[p_pvm]", the_date),
    )

    response = None
    with requests.Session() as session:
        try:
            response = session.get(url, headers=headers, params=params)
        except ConnectionError as ce:
            logging.exception(f"Connection error for {baseurl}.\n{ce}")
    return response.text if response else None


def parse_results(data: str, center: str) -> list:
    """Parse results from HTML for a single center and date

    Args:
        data (str): raw HTML data
        center (str): center shrt name

    Returns:
        list: list of availabilities for the center and date; each availability is a dic()
    """
    results = []  # list of dictionaries
    if data is None:
        return results
    soup = BeautifulSoup(data, "html.parser")
    # avail_list = soup.find_all("td", class_=["s-avail", "s-avail-short"])
    # avail_list = soup.select('a[href^="/booking/create-booking"]')
    links = [
        link.get("href") for link in soup.select('a[href*="/booking/create-booking"]')
    ]
    # use urlparse to split links' parameters

    for link in links:
        urlstring = urlparse(link, allow_fragments=False).query
        urldic = parse_qs(urlstring)
        court_no = int(urldic.get("resid")[0])
        duration = urldic.get("kesto")[0]
        start_time = datetime.strptime(urldic.get("alkuaika")[0], "%Y-%m-%d %H:%M:%S")
        start_hour = start_time.hour

        is_suitable_time = start_hour in range(START_HOUR, END_HOUR + 1)

        if court_no < MAX_COURT_NO and is_suitable_time:
            results.append(
                {
                    "time": start_time.strftime("%H:%M"),
                    "duration": duration,
                    "court": court_no,
                }
            )
            # logging.debug(results)
            # 'link': CENTERS.get(center).get('url')})
    return results


def display_results(results) -> None:
    print("\nAvailability details:\n")
    pp(results)


def tennis_finder_hel() -> None:
    """main function"""
    # read_parameters()
    print(
        f"Reading availability of {len(CENTERS)} centers for {PLUS_DAYS_MAX} days with starting time between {START_HOUR} and {END_HOUR}...\n"
    )
    today = date.today()
    # check all days from today up to +PLUS_DAYS_MAX
    for days_plus in range(PLUS_DAYS_MAX + 1):
        date_ = today + timedelta(days=days_plus)
        # date_nice is used in URL and in presenting the data
        date_for_url = date_.strftime("%Y-%m-%d")  # for forming URL
        date_nice = date_.strftime("%a %d %b")  # for printout
        # skip weekends
        if date_.isoweekday() in WEEKENDS:
            # logging.debug(f'Date {date_} (day = {date_.isoweekday()}) --> Weekend detected, skipping')
            continue
        # check all tennis centers
        for center, cdata in CENTERS.items():
            url = cdata.get("url", "")
            # logging.debug(f'fetching: {date_}: {url}')
            data = fetch_raw_data(url, date_for_url)
            parsed_data = parse_results(data, center)
            print(
                f'Availability for {center.title()} center ({CENTERS.get(center).get("url")}) on {date_} between {START_HOUR} and {END_HOUR}: {len(parsed_data)} slots.'
            )
            if parsed_data:
                all_results[center].append(
                    {"date": date_nice, "availabilities": parsed_data}
                )
    display_results(all_results)


if __name__ == "__main__":
    print(
        "This program finds tennis centers availability for the upcoming days in Helsinki.\n"
    )
    tennis_finder_hel()

# metascraper.py - Call the other scrapers to grab OpenAI URLs
# This script puts it all together- takes the universal interface of OpenAI URLS, calls OpenAI
# And generates JSONS of them
import requests
import config
from pick import pick
import scraperutils
from scrapers.allgptsscraper import AllGPTSScraper
from scrapers.botsbarnscraper import BotsBarnScraper
from scrapers.pluginsurfscraper import PluginSurfScraper
from scrapers.tinytopgpts import TinyTopGPTS
from scrapers.topgptsscraper import TopGPTsScraper
import json


def fetch_openai_gizmo(openai_url):
    # Start by sanitizing the url, it should start with https://chat.openai.com/g/g-
    if not openai_url.startswith("https://chat.openai.com/g/g-"):
        # raise ValueError("Unknown OpenAI URL")
        return (None, False, "failed_valid_url")

    # the next sequence of characters up until the next hyphen is the gizmo id
    gizmo_id = openai_url[27:openai_url.find("-", 28)]

    # Once this is done, we can plug this into a request to the OpenAI API
    # This can be at https://chat.openai.com/backend-api/gizmos/<gizmo_id>

    headers = {
        "accept": "*/*",
        "accept-language": "en-US",
        "sec-ch-ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"",
        "sec-ch-ua-mobile": "?0",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
        "authorization": config.OPENAI_BEARER_TOKEN,
        "sec-ch-ua-platform": "\"macOS\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin"
    }

    full_request_url = "https://chat.openai.com/backend-api/gizmos/g" + gizmo_id

    gizmo_request = requests.get(full_request_url, headers=headers)

    successful_request = True
    if gizmo_request.status_code != 200:
        # raise ValueError("Error Fetching Gizmo JSON @ URL " + full_request_url +  " Status Code: " + str(gizmo_request.status_code) + " " + gizmo_request.text)
        return None, False, "http_code " + str(gizmo_request.status_code)

    gizmo_json = None
    try:
        gizmo_json = gizmo_request.json()
    except:
        print("Error Fetching Gizmo JSON @ URL " + full_request_url + " Status Code: " + str(gizmo_request.status_code))
        return (gizmo_json, False, "invalid_json")

    return (gizmo_json, successful_request, "none")

def decode_scrapers(name):
    match name:
        case "topgpts.ai":
            return TopGPTsScraper()
        case "plugin.surf":
            return PluginSurfScraper()
        case "topgpts.ai-tiny":
            return TinyTopGPTS()
        case "allgpts.co":
            return AllGPTSScraper()
        case "botsbarn.com":
            return BotsBarnScraper()
        case _:
            raise ValueError(f"Unknown scraper name/Not implemented: {name}")
def main():
    title = 'Select scrapers to run: '
    options = ['topgpts.ai', 'plugin.surf', 'topgpts.ai-tiny', "allgpts.co", "botsbarn.com", 'Twitter']
    selected = pick(options, title, multiselect=True, min_selection_count=1)
    failure_tracker = {}

    selected_strings = "Running with "
    for i in selected:
        selected_strings = selected_strings +  i[0] + ", "

    print(f"{scraperutils.bcolors.OKCYAN}{selected_strings}{scraperutils.bcolors.ENDC}")

    scrapers = []
    for selection in selected:
        scrapers.append(decode_scrapers(selection[0]))

    scraper_data = []
    for scraper in scrapers:
        # TODO: check if a .bak.json of the output exists and ask if you want to ignore scraping

        openai_urls = scraper.scrape()

        scraper_data.append({
            "id": scraper.ID,
            "scraper": scraper,
            "openai_urls": openai_urls,
            "openai_gpts": []
        })
        # log entry into the failure tracker
        failure_tracker[scraper.ID] = {}

    # compose the urls into referral banks
    referrer_lookup_table = {}

    gizmo_list = []
    for scraper in scraper_data:
        source = scraper["id"]
        for openai_url in scraper["openai_urls"]:
            # Take the gizmo and fetch OpenAI data
            gizmo, status, reason = fetch_openai_gizmo(openai_url)

            if status == False:
                if reason not in failure_tracker[source].keys():
                    failure_tracker[source][reason] = 1
                else:
                    failure_tracker[source][reason] += 1
                continue

            # Case for if the gizmo appears in another scrape, we will not append it, but we will keep a log of it
            if openai_url in referrer_lookup_table.keys():
                print(f"{scraperutils.bcolors.OKCYAN}Duplicate OpenAI URL: {openai_url}")
                referrer_lookup_table[openai_url].append(source)
            else:
                referrer_lookup_table[openai_url] = [source]
                gizmo_list.append(gizmo)



    # At the end of it all, log the failures and which domains caused them
    print(f"{scraperutils.bcolors.WARNING}Failures = ", failure_tracker)

    print(referrer_lookup_table)

    with open("gizmos_noref.json", "w") as outfile:
        json.dump(gizmo_list, outfile)

    # Let's tag all the gizmos with a referrer array
    for gizmo_index in range(len(gizmo_list)):
        gizmo_id = gizmo_list[gizmo_index]["gizmo"]["id"]
        shortcode = scraperutils.convert_short_code_to_openai_url(gizmo_id)

        if shortcode in referrer_lookup_table.keys():
            gizmo_list[gizmo_index]["source"] = referrer_lookup_table[shortcode]
        else:
            gizmo_list[gizmo_index]["source"] = ["unknown"]

    with open("gizmos_ref.json", "w") as outfile:
        json.dump(gizmo_list, outfile)


def exit():
    pass


if __name__ == "__main__":
    main()


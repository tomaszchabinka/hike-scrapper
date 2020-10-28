from bs4 import BeautifulSoup
import requests
import json
import argparse

LINK_PREFIX = "https://www.wandelnetwerknoordholland.nl"

def get_coordinates(starting_point_id):
    coordinates_response = requests.get(f"{LINK_PREFIX}/content/get_geo_json.php?function=3&n_codes={starting_point_id}")

    if coordinates_response.status_code != 200:
        raise Exception("connection to wandelnetwerknoordholland.nl failed")

    return coordinates_response.json()['features'][0]['geometry']['coordinates']


def check_if_trail_dog_friendly(link):
    trail_response = requests.get(f"{LINK_PREFIX}{link}")
    if trail_response.status_code != 200:
        raise Exception("connection to wandelnetwerknoordholland.nl failed")

    trail_details = trail_response.content
    trail_details_parsed = BeautifulSoup(trail_details, 'html.parser')
    return not ( "Verboden voor honden" in str(trail_details_parsed) )

def get_color(trail_name):
    trail_name_lowercase = trail_name.lower()
    if "blauw" in trail_name_lowercase:
        return "blue"

    if "geel" in trail_name_lowercase or "gele" in trail_name_lowercase:
        return "yellow"

    if "oranje" in trail_name_lowercase:
        return "orange"

    if "paars" in trail_name_lowercase:
        return "purple"

    if "rode" in trail_name_lowercase or "rood" in trail_name_lowercase:
        return "red"

    if "groen" in trail_name_lowercase:
        return "green"

    return None
    

def scrap_trails(link):
    trails = []

    starting_point_details_response = requests.get(f"{LINK_PREFIX}{link}")
    if starting_point_details_response.status_code != 200:
        raise Exception("connection to wandelnetwerknoordholland.nl failed")

    starting_point_details = starting_point_details_response.content
    starting_point_details_parsed = BeautifulSoup(starting_point_details, 'html.parser')

    for trails_block in starting_point_details_parsed.select(".info-container > .info-block")[0].find_all("dl"):
        found_trails = trails_block.find_all("dt")
        for trail in found_trails:
            name = trail.find("a").string
            link = trail.find("a")["href"]
            length = float(trail.find("dd").string.split(" ")[0])
            trails.append({"name": name, "link": f"{LINK_PREFIX}{link}", "length": length, "dogFriendly": check_if_trail_dog_friendly(link), "color": get_color(name)})

    return trails

def scrap_starting_points():
    next_page_link = "/startpunten/"
    starting_points = []

    while next_page_link != None:
        starting_points_list = None
        print( f"New page will be processed: {LINK_PREFIX}{next_page_link}" )
        starting_points_list_response = requests.get(f"{LINK_PREFIX}{next_page_link}")

        if starting_points_list_response.status_code == 200:
            starting_points_list = starting_points_list_response.content
        else:
            raise Exception("connection to wandelnetwerknoordholland.nl failed")

        starting_points_list_parsed = BeautifulSoup(starting_points_list, 'html.parser')

        next_page_link = None
        starting_point_divs = starting_points_list_parsed.find_all("div", class_="box-route clearfix")

        for starting_point_div in starting_point_divs:
            name = starting_point_div.find("a").string
            link = starting_point_div.find("a")['href']
            starting_point_id = link.split("/")[-2]

            trails = scrap_trails(link)
            starting_points.append({"name": name, "link": f"{LINK_PREFIX}{link}", "trails": trails, "coordinates": get_coordinates(starting_point_id)})
            print(f"Starting Point added to the list: {name}")

        next_page_link = starting_points_list_parsed.find("a", string="Volgende")['href'] if starting_points_list_parsed.find("a", string="Volgende") else None

    return starting_points

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_path")
    args = parser.parse_args()

    starting_points_data = {"startingPoints": scrap_starting_points()}

    with open(args.output_path, mode="w+") as jsonfile:
        jsonfile.write(json.dumps(starting_points_data))

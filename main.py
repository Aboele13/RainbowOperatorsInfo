import pandas as pd
import requests
from bs4 import BeautifulSoup
from unidecode import unidecode


def scrape_from_int():

    def proper_case(s):
        words = s.split()
        for i in range(len(words)):
            words[i] = words[i][0].upper() + words[i][1:].lower()
        return " ".join(words)

    base_url = "https://www.ubisoft.com"
    operators_url = base_url + "/en-us/game/rainbow-six/siege/game-info/operators"

    # Step 1: Get the main page content
    response = requests.get(operators_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Step 2: Find all operator links and names
    operator_links = []
    for card in soup.select('div.oplist__cards__wrapper a.oplist__card'):
        operator_name = card.find('span').text.strip()
        operator_url = base_url + card['href']
        operator_links.append((operator_name, operator_url))

    # Step 3: Visit each operator page and scrape loadout information
    data = []

    for name, link in operator_links:
        print(f"Acquiring data on {name} from {link}")
        operator_response = requests.get(link)
        operator_soup = BeautifulSoup(operator_response.text, 'html.parser')

        # Extract side (Attacker or Defender)
        side_text = "Unknown"
        side_div = operator_soup.select_one('div.operator__header__side__detail')
        if side_div:
            side_span = side_div.find('span')
            if side_span:
                side_text = side_span.get_text(strip=True)
                if side_text.lower() == "attacker":
                    side_text = "Attacker"
                elif side_text.lower() == "defender":
                    side_text = "Defender"
                    
        # Extract Speed
        speed_div = operator_soup.select_one('div.operator__header__stat')
        speed = 0
        if speed_div:
            stars = speed_div.select('div.react-rater-star.is-active')
            speed = 4 - len(stars)

        # Extract primary weapons
        primaries = []
        for weapon_div in operator_soup.select('div.operator__loadout__category'):
            title = weapon_div.find('h2', class_='operator__loadout__category__title').get_text(strip=True)
            if "Primary Weapon" in title:
                for weapon in weapon_div.select('div.operator__loadout__weapon'):
                    weapon_name = weapon.find('p').text.strip()
                    if weapon_name == "9X19SVN" or weapon_name == "UZK50Gi":
                        weapon_type = "SUBMACHINE GUN"
                    elif weapon_name == "CCE Shield" or weapon_name == "LE ROC SHIELD" or weapon_name == "G52-Tactical Shield" or weapon_name == "Ballistic Shield":
                        weapon_type = "Shield"
                    else:
                        weapon_type = weapon.find_all('p')[1].text.strip()
                    primaries.append(f"{weapon_name} ({proper_case(weapon_type)})")

        # Extract secondary weapons
        secondaries = []
        for weapon_div in operator_soup.select('div.operator__loadout__category'):
            title = weapon_div.find('h2', class_='operator__loadout__category__title').get_text(strip=True)
            if "Secondary Weapon" in title:
                for weapon in weapon_div.select('div.operator__loadout__weapon'):
                    weapon_name = weapon.find('p').text.strip()
                    if weapon_name == "Bailiff 410":
                        weapon_type = "SHOTGUN"
                    elif weapon_name == "Luison":
                        weapon_type = "HANDGUN"
                    else:
                        weapon_type = weapon.find_all('p')[1].text.strip()
                    secondaries.append(f"{weapon_name} ({proper_case(weapon_type)})")

        # Extract gadgets
        gadgets = []
        for weapon_div in operator_soup.select('div.operator__loadout__category'):
            title = weapon_div.find('h2', class_='operator__loadout__category__title').get_text(strip=True)
            if "Gadget" in title:
                for gadget in weapon_div.select('div.operator__loadout__weapon'):
                    gadget_name = gadget.find('p').text.strip()
                    gadgets.append(proper_case(gadget_name).replace("Emp ", "EMP "))

        data.append({
            "Name": proper_case(unidecode(name)),
            "Side": side_text,
            "Speed": speed,
            "Primaries": ", ".join(primaries),
            "Secondaries": ", ".join(secondaries),
            "Gadgets": ", ".join(gadgets)
        })

    data.reverse()
    for i in range(len(data)):
        if data[i]["Name"] == "Striker" or data[i]["Name"] == "Sentry":
            data.insert(0, data[i])
            data.pop(i + 1)

    # Step 4: Create a DataFrame
    df = pd.DataFrame(data)
    print(df)
    
    print(f"\n\n\nAll operators are updated from their respective webpages.\n\n")

    # Optionally, save the DataFrame to a CSV file
    df.to_csv('operators_loadout.csv', index=False)

def update_personal_cols():
    df = pd.read_csv("operators_loadout.csv")

    # auto acogs (both)
    def_w_auto_acogs = ["Castle", "Goyo", "Frost", "Rook", "Doc", "Echo"]
    df["Auto_ACOG"] = df.apply(
        lambda row: row.get("Name", "") in def_w_auto_acogs or
        (row.get("Side", "") == "Attacker" and
        any(weapon in row.get("Primaries", "") for weapon in ["Assault Rifle", "Submachine Gun", "Light Machine Gun"])),
        axis=1
    )

    # shotguns (both)
    df["Secondary_Shotgun"] = df.apply(lambda row: "Shotgun" in row.get("Secondaries", "") or row.get("Name", "") == "Buck", axis=1)
    
    # extra cam (both)
    ops_with_xtra_cam = ["Brava", "Flores", "Zero", "Iana", "Twitch", "Mozzie", "Maestro", "Echo", "Valkyire"]
    df["Extra_Cam"] = df.apply(lambda row: row.get("Name", "") in ops_with_xtra_cam or "Bulletproof Camera" in row.get("Gadgets", ""), axis=1)

    # open hatches (attack)
    att_with_soft_breach = ["Ram", "Flores", "Kali", "Amaru", "Zofia", "Buck", "Sledge", "Ash", "Glaz", "Thermite", "Ace", "Hibana", "Maverick"]
    df["Open_Hatches"] = df.apply(lambda row: row.get("Secondary_Shotgun", False) or "Gonne-6" in row.get("Secondaries", "") or row.get("Name", "") in att_with_soft_breach or any(gadget in row.get("Gadgets", "") for gadget in ["Frag Grenade", "Hard Breach Charge", "Breach Charge"]), axis=1)
    
    # rush barricades (attack)
    att_with_rush_barr = ["Ash", "Zofia", "Ram", "Sledge"]
    df["Rush_Barricades"] = df.apply(lambda row: row.get("Name", "") in att_with_rush_barr or "Gonne-6" in row.get("Secondaries", "") or "Breach Charge" in [gadget.strip() for gadget in row.get("Gadgets", "").split(",")], axis = 1)
    
    # rotates (defense)
    df["Make_Rotates"] = df.apply(lambda row: row.get("Side", "") == "Defender" and (row.get("Name", "") == "Oryx" or row.get("Name", "") == "Tachanka" or row.get("Secondary_Shotgun", False) or "Impact Grenades" in row.get("Gadgets", "")), axis=1)

    df.columns = df.columns.str.replace('_', ' ') # clean column headers
    
    df.to_csv('completed_operators_list.csv', index=False)

    
def main():
    scrape_from_int()
    update_personal_cols()
    
if __name__ == "__main__":
    main()

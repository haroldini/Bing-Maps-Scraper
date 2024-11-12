import requests
import pandas as pd
import os
import time

headers = {
    'authority': 'www.bingapis.com',
    'accept': '*/*',
    'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'origin': 'https://www.bing.com',
    'referer': 'https://www.bing.com/',
    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'cross-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

def flatten(lst):
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(flatten(item))
        elif isinstance(item, dict):
            result.append(item)
    return result

def save_results(data):
    df = pd.DataFrame(data)
    df.to_csv(os.path.join(project_dir, "output.csv"), index=False)

def get_results(tile_id):
    params = {
        'tileId': tile_id,
        'q': 'supermarket',
        'chainid': '',
        'categoryid': '91493',
        'appid': '5BA026015AD3D08EF01FBD643CF7E9061C63A23B',
    }
    response = requests.get('https://www.bingapis.com/api/v7/micropoi', params=params, headers=headers).json()
    if not "results" in response:
        return []
    for entry in response["results"]:
        geo_data = entry.pop("geo", {})
        entry.update(geo_data)
    results = flatten(response["results"])
    return results

project_name = "micropoi-test"
app_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.join(app_dir, "output", project_name)
os.makedirs(project_dir, exist_ok=True)


tile_ids = [
    #"0313130100031" # aberyst
    # "0313130311" # cardiff
    "0313130" # south wales
]

all_results = []

while tile_ids:
    time.sleep(1)
    print(tile_ids)

    tile_id = tile_ids.pop(0)
    results = get_results(tile_id)

    # If fewer than 100 results, save data
    if len(results) <= 100:
        all_results.extend(results)
    
    # If more than 100 results, split search grid
    else:
        tile_ids.extend([tile_id+str(i) for i in range(4)])



save_results(all_results)

print(len(all_results))
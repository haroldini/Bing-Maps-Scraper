import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import requests
import time
import os

from tqdm import tqdm

class MapsScraper():
    app_dir = os.path.dirname(os.path.abspath(__file__))

    headers = {
        'authority': 't.ssl.ak.tiles.virtualearth.net',
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
    url = "https://t.ssl.ak.tiles.virtualearth.net/tiles/cmd/StreetSideBubbleMetaData"

    result_cap = 100

    def __init__(self, project_name, initial_boundary, key):

        # Initialise project
        self.project_dir = os.path.join(MapsScraper.app_dir, "output", project_name)
        os.makedirs(self.project_dir, exist_ok=True)

        self.init_scraper(initial_boundary, key)
        self.init_visualiser()

    def init_scraper(self, initial_boundary, key):
        self.initial_boundary = initial_boundary
        self.boundaries = [initial_boundary]
        self.all_results = []
        self.params = {
            'count': MapsScraper.result_cap,
            'key': key,
            'g': '13651',
        }

    def init_visualiser(self):
        self.col = {
            "dark": "#23242c",
            "mid": "#525467",
            "light": "#5f6278",
            "red": "#ef2b3c"
        }
        self.fig, self.ax = plt.subplots()
        self.fig.set_facecolor(self.col["light"])
        self.full_square = self.ax.add_patch(patches.Rectangle((0, 0), 0, 0, linewidth=1, edgecolor=self.col["mid"], facecolor=self.col["mid"], label='Completed', zorder=0))
        self.current_subregion = self.ax.add_patch(patches.Rectangle((0, 0), 0, 0, linewidth=1, edgecolor=self.col["red"], facecolor=self.col["dark"], label='Current Subregion', zorder=2))
        self.subregions = []

        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['bottom'].set_visible(False)
        self.ax.spines['left'].set_visible(False)

        self.ax.xaxis.label.set_color(self.col["dark"])
        self.ax.yaxis.label.set_color(self.col["dark"])
        self.ax.title.set_color(self.col["dark"])
        self.ax.tick_params(axis='x', colors=self.col["dark"])
        self.ax.tick_params(axis='y', colors=self.col["dark"])

    def get_results(self, boundary):
        self.params.update(boundary)
        results = MapsScraper.flatten(self.get_response())[1:]
        return results
    
    def recursive_binary_search(self):

        with tqdm(total=len(self.boundaries), desc="Processing Boundaries") as pbar:
            while self.boundaries:
                time.sleep(0.25)

                # get first boundary from list, get the results for it
                boundary = self.boundaries.pop(0)
                self.visualise_search(boundary)
                results = self.get_results(boundary)

                # if results are capped, add new boundaries to self.boundaries
                if len(results) >= MapsScraper.result_cap:

                    # even iterations, split north/south
                    if boundary["split_type"] == "lng" or boundary["split_type"] == "none":

                        # Calculate postions of new boundary boxes
                        mid_lat = str((float(boundary["north"]) + float(boundary["south"])) / 2)
                        north_box = boundary.copy()
                        south_box = boundary.copy()
                        north_box["south"] = mid_lat
                        south_box["north"] = mid_lat
                        north_box["split_type"] = "lat"
                        south_box["split_type"] = "lat"
                        self.boundaries.extend([
                            north_box, south_box
                        ])

                    # odd iterations, split east/west
                    elif boundary["split_type"] == "lat":
                        mid_lng = str((float(boundary["east"]) + float(boundary["west"])) / 2)
                        east_box = boundary.copy()
                        west_box = boundary.copy()
                        east_box["west"] = mid_lng
                        west_box["east"] = mid_lng
                        east_box["split_type"] = "lng"
                        west_box["split_type"] = "lng"
                        self.boundaries.extend([
                            east_box, west_box
                        ])
                
                else:

                    # if results not capped, add results to output
                    for result in results:
                        result.update(boundary)
                    self.all_results.extend(results)
                
                # Update progress bar
                pbar.update(1)
                pbar.set_postfix({"Locations Found": len(self.all_results)})

        temp_df = pd.DataFrame(self.all_results)
        temp_df_unique = temp_df.drop_duplicates(subset="id")
        self.all_results = temp_df_unique.to_dict(orient="records")

    def get_response(self):
        response = requests.get(
            MapsScraper.url,
            params=self.params,
            headers=MapsScraper.headers,
        ).json()
        return response
    
    def save_results(self):
        df = pd.DataFrame(self.all_results)
        df.to_csv(os.path.join(self.project_dir, "output.csv"), index=False)

    @staticmethod
    def flatten(lst):
        result = []
        for item in lst:
            if isinstance(item, list):
                result.extend(MapsScraper.flatten(item))
            elif isinstance(item, dict):
                result.append(item)
        return result

    def visualise_search(self, boundary):
        # Clear all subregions
        for subregion in self.subregions:
            subregion.remove()

        self.subregions = []

        # Full search grid
        self.full_square.set_xy((float(self.initial_boundary["west"]), float(self.initial_boundary["south"])))
        self.full_square.set_width(float(self.initial_boundary["east"]) - float(self.initial_boundary["west"]))
        self.full_square.set_height(float(self.initial_boundary["north"]) - float(self.initial_boundary["south"]))

        # Update current subregion
        self.current_subregion.set_xy((float(boundary["west"]), float(boundary["south"])))
        self.current_subregion.set_width(float(boundary["east"]) - float(boundary["west"]))
        self.current_subregion.set_height(float(boundary["north"]) - float(boundary["south"]))

        # Draw subregions for active boundaries
        for subregion_boundary in self.boundaries:
            subregion = self.ax.add_patch(patches.Rectangle((0, 0), 0, 0, linewidth=1, edgecolor=self.col["mid"], facecolor=self.col["dark"], label='Subregion', zorder=1))
            subregion.set_xy((float(subregion_boundary["west"]), float(subregion_boundary["south"])))
            subregion.set_width(float(subregion_boundary["east"]) - float(subregion_boundary["west"]))
            subregion.set_height(float(subregion_boundary["north"]) - float(subregion_boundary["south"]))
            self.subregions.append(subregion)

        # Set axis limits
        self.ax.set_xlim(float(self.initial_boundary["west"]), float(self.initial_boundary["east"]))
        self.ax.set_ylim(float(self.initial_boundary["south"]), float(self.initial_boundary["north"]))

        # Display the updated plot and pause to update
        plt.pause(0.1)


if __name__ == "__main__":
    scraper = MapsScraper(
        project_name = "2024-01/testing",
        initial_boundary = {
            'split_type': "none",
            'north': '51.28669762519701',
            'south': '50.19613948173247',
            'east': '-0.5794151679534707',
            'west': '-1.885124383872494'
        },
        key = "AmLGOGqUAnIdOz449jxf7vvvZaONNtUZtNlDYSADywYZCzy44lJdrsEcwF8QEkbs"
    )

    scraper.recursive_binary_search()
    scraper.save_results()
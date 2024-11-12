import json
import os
import time
import requests
import sys
from io import BytesIO
from PIL import Image

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from matplotlib.colors import to_rgba
from matplotlib.patches import Rectangle
from requests.exceptions import RequestException
from tqdm import tqdm

from sidt.utils.os import get_current_path, open_dir, get_root_path
from sidt.utils.data import flatten_structure
from sidt.utils.decorators import retry
from sidt.utils.git import GitController
from sidt.utils.io import XLWriter


class Utils():
    """Utility class containing static methods for data manipulation and saving"""

    IO_error = "IO file may be open, close it and input any key to continue."

    colors = {
        "dark": "#18181f",
        "mid": "#525363",
        "light": "#babccf",
        "red": "#ef2b3c"
    }


    @staticmethod
    def extract_first_if_list(item):
        """Converts an item to its first element if it's a list"""
        if isinstance(item, list) and len(item) > 0:
            return item[0]
        return item


    @staticmethod
    def load_data(filepath):
        """Loads results directly from csv file, useful for debugging 
        geocoding method, or rerunning geocoding with different params"""
        df = pd.read_csv(filepath)
        data = df.to_dict(orient="records")
        return df, data


    @staticmethod
    def display_scatter(data):
        """Displays a scatter plot given a list of dictionaries"""
        df = pd.DataFrame(data)
        sns.scatterplot(x="longitude", y="latitude", data=df)
        plt.xlabel("Longitude")
        plt.ylabel("Latitude")
        plt.title("Locations found")
        plt.pause(0.1)


    @retry(n_attempts=3, require_input=IO_error)
    def save_dfs_to_xlsx(filepath, dfs):
        """Saves a list of dataframes to a csv file"""
        XLWriter.dfs_to_xlsx(dfs, filepath, wrap_cells=False)


    @retry(n_attempts=3, require_input=IO_error)
    def save_data_to_csv(filepath, data):
        """Saves a list of dictionaries to a csv file"""
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)


class MapsScraper():
    """Class for handling the scraper Bing Maps scraper itself"""

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
    url = "https://www.bingapis.com/api/v7/micropoi"

    result_cap = 100
    sleep_duration = 0.1

    def __init__(self, params):
        """Initialises the scraper and visualisation if needed"""
        self.visualiser_settings = params["visualiser_settings"]
        self.prog_bar = tqdm(dynamic_ncols=True) 
        self.init_scraper(params)

        if self.visualiser_settings["display"]:
            self.tile_plot = TilePlot(initial_tiles=self.initial_tiles, settings=self.visualiser_settings)
    

    def log(self, status):
        """Uses tqdm progress bar as an equivalent to printing but erases previous line.
        This needs a dedicated class or to be outsourced to a library"""
        self.prog_bar.set_description(status)


    def init_scraper(self, params):
        """Initialises the scraper by processing the input parameters including tilesets and API params"""

        # Load location data
        self.log("Initialising scraper")
        with open(os.path.join(App.data_dir, "config.json"), "r") as file:
            all_tile_sets = json.load(file)["tile_sets"]
            tile_sets = {key: val for key, val in all_tile_sets.items() if key in params["tile_sets"]}

        # Prepare tiles
        self.tiles = []
        for tile_set in tile_sets.values():
            for tile in tile_set["tiles"]:

                # Ensure all tiles are at least 5 digits long
                if len(tile) >= 5:
                    self.tiles.append({
                        "tile_set": tile_set["name"],
                        "tile_id": tile,
                        "tile_parent_id": tile
                    })
                
                # Split tiles into subtiles until all are 5 digits long
                else:
                    new_tiles = self.split_tiles_until_length(tile, 5)
                    for new_tile in new_tiles:
                        self.tiles.append({
                            "tile_set": tile_set["name"],
                            "tile_id": new_tile,
                            "tile_parent_id": tile
                        })

        self.initial_tiles = self.tiles
        self.new_tiles = []
        
        # Initialise API params
        self.category_id = params["category_id"]
        self.category_id_i = params["category_id_i"]
        self.params = {
            "tileId": "",
            "q": params["search_term"],
            "chainid": params["chain_id"],
            "categoryid": self.category_id,
            "appid": params["app_id"],
        }

        self.all_results = []


    def run(self):
        """Runs the scraper, then cleans the results by removing duplicate results.
        Returns a list of dictionaries containing all results"""

        # Run the recursive_grid_search
        start = time.time()
        self.log("Running scraper")
        self.recursive_grid_search()

        # Remove duplicate records
        self.log("Removing duplicate records")
        temp_df = pd.DataFrame(self.all_results)
        temp_df_unique = temp_df.drop_duplicates(subset="id")
        self.all_results = temp_df_unique.to_dict(orient="records")

        # Complete
        plt.close("all")

        self.log(f"Scraper finished in {round(time.time()-start)}s")
        return self.all_results


    def recursive_grid_search(self):
        """Iterates over all tiles given in each tileset in input params
        Remaining tiles are stored in self.tiles, tiles are popped as they are processed"""

        index = -1
        while self.tiles:
            index += 1
            tile = self.tiles.pop(0)

            # Update progress bar
            self.prog_bar.update(1)
            status = {
                "Category ID": f"{self.category_id_i}: {self.category_id}",
                "Tiles Completed": index,
                "Tiles Remaining": len(self.tiles),
                "Locations Found": len(self.all_results),
                "Current Parent Tile": tile["tile_parent_id"],
                "Current Search Tile": tile["tile_id"],
                }
            self.prog_bar.set_postfix(status)
            
            # Process the tile, get the data, ensure its validity
            if self.visualiser_settings["display"]:
                self.tile_plot.update_labels(status)
                self.tile_plot.update(tile, self.new_tiles)
            self.process_tile(tile)      


    def process_tile(self, tile):
        """Fetches data from the API for the tile, uses the hardcoded cap to determine
        whether search grid should be split further (> cap = split). Handles API issues
        when response contains zero results by checking subtiles in this case."""

        # Get results for tile
        results = self.get_results(tile)
        time.sleep(MapsScraper.sleep_duration)

        # If more results than cap, split search grid
        if len(results) >= MapsScraper.result_cap:
            self.new_tiles = self.split_tile(tile)
            self.tiles.extend(self.new_tiles)
            
        # If 0 results, split tile into 4 subtiles and ensure they sum to 0.
        elif len(results) == 0:
            sub_tiles_results, sub_tiles = self.get_subtile_results(tile)
            if len(sub_tiles_results) != 0:
                self.new_tiles = sub_tiles
                self.tiles.extend(sub_tiles)
            else:
                self.new_tiles = []

        # If num results lower than cap, but not zero, store the results
        elif len(results) <= MapsScraper.result_cap:
            self.new_tiles = []
            self.all_results.extend(results)


    def get_subtile_results(self, tile):
        """Returns a list of results for the four subtiles of a tile. 
        Used to determine whether 0 results are actually 0."""

        sub_tiles = self.split_tile(tile)
        sub_tiles_results = []
        for sub_tile in sub_tiles:
            sub_tile_results = self.get_results(sub_tile)
            sub_tiles_results.extend(sub_tile_results)
        return sub_tiles_results, sub_tiles


    def get_results(self, tile):
        """Given a tile ID, makes a request and returns a list of results. 
        Called in the process_tile function."""

        self.params["tileId"] = tile["tile_id"]
        response = self.get_response()

        # Handle case where no results in response
        if not "results" in response: 
            return []
        
        # Flatten list of lists and subdictionaries containing geodata
        results = flatten_structure(response["results"])
        for result in results:
            result["category_id"] = self.category_id
            geo_data = result.pop("geo", {})
            result.update(geo_data)
            result.update(tile)
        
        return results
    

    @retry(n_attempts=3, wait=10, exponential_backoff=True)
    def get_response(self):
        """Error handling for the request, allows up to 3 retries before raising"""
        try:
            response = requests.get(
                MapsScraper.url,
                params=self.params,
                headers=MapsScraper.headers,
            )
            response.raise_for_status()

            res_json = response.json()
        except RequestException as e:
            print(f"Request failed for {self.params['tileId']}: {e}")
            raise

        return res_json
    

    def split_tiles_until_length(self, tiles, min_length=5):
        """Receives a tileID string, splits the tile into 4 subtiles using the split_tile method until
        all subtiles are at least min_length long. Returns the subtiles"""

        # Ensure tiles is a list
        if isinstance(tiles, str):
            new_tiles = [tiles]
        else:
            new_tiles = tiles

        # Sort the tiles by length
        new_tiles = sorted(new_tiles, key=len)

        while len(new_tiles[0]) < min_length:
            new_tiles = self.split_tile(new_tiles[0]) + new_tiles[1:]
            new_tiles = sorted(new_tiles, key=len)
            
        return new_tiles



    def split_tile(self, tile, keys={}):
        """Splits a tile into its four subtiles
        Tile ids contain integers from 0 to 3. Each grid contains 4 subgrids.
        E.g. id=13130 contains the subgrids 131300, 131301, 131302, 131303"""

        # Ensure tile is a dictionary
        original_type = type(tile)
        if original_type == str:
            tile = {"tile_id": tile}

        new_tiles = []
        for i in range(4):
            new_tile = tile.copy()
            new_tile["tile_id"] = tile["tile_id"]+str(i)

            # Give custom keys to subtiles
            for key, val in keys.items():
                new_tile[key] = val
            
            new_tiles.append(new_tile)
        
        # Return as string if original tile was a string
        if original_type == str:
            return [tile["tile_id"] for tile in new_tiles]
        
        return new_tiles


class TilePlot():
    """Class for plotting the visualisation. The visualisation is helpful to
    gauge progress as each tile searched may create four new tiles. A standard
    tqdm bar could not handle this. Also useful for debugging recursive search."""

    sleep_duration = 0.1

    def __init__(self, initial_tiles, settings):
        """Creates the plot, provides the initial data and state of the plot.
        Plot highlights the current tile, past tiles, and remaining tiles."""

        # Initialise settings
        self.settings = settings
        self.opacity = 0.5 if settings["overlay_map"] else 1

        # Colours for current tile plot
        self.cur_edgecolor = to_rgba(Utils.colors["red"], alpha=1)
        self.cur_facecolor = to_rgba(Utils.colors["dark"], alpha=self.opacity)

        # Initialise plot
        sns.set_theme(style="whitegrid")
        self.initial_tiles_xy = TilePlot.tiles_to_xy(initial_tiles)
        self.fig, self.ax = plt.subplots(figsize=(9, 6))
        self.fig.subplots_adjust(right=0.66)
        self.label_font = {"fontname": "Arial", "size": "12", "color": Utils.colors["light"]}
        self.title_font = {"fontname": "Arial", "size": "14", "color": Utils.colors["light"], "weight": "bold"}
        self.ax.set_title(label="Bing Maps Search Progress", x=1.05, y=0.9, ha="left", **self.title_font)
        self.ax.set_xlabel("Longitude", **self.label_font)
        self.ax.set_ylabel("Latitude", **self.label_font)
        self.ax.set_aspect("equal", adjustable="box")

        # Plot background tiles
        self.initial_tile_patches = []
        for xy in self.initial_tiles_xy:
            rectangle = Rectangle((xy["x1"], xy["y1"]), xy["x2"] - xy["x1"], xy["y2"] - xy["y1"], edgecolor=Utils.colors["light"], facecolor=Utils.colors["dark"], zorder=0, alpha=1)
            new_patch = self.ax.add_patch(rectangle)

            # Add tile_id as text centered on the rectangle
            if self.settings["overlay_ids"]:
                center_x = xy["x1"] + (xy["x2"] - xy["x1"]) / 2
                center_y = xy["y1"] + (xy["y2"] - xy["y1"]) / 2
                self.ax.text(center_x, center_y, xy["tile_id"], ha="center", va="center", fontsize=8, color="red", zorder=10)

            # Display map
            if self.settings["overlay_map"]:
                self.fetch_and_display_image(xy["tile_id"], rectangle)
            self.initial_tile_patches.append(new_patch)

        self.current_tile_patch = None

        # Plot all initial subtiles
        self.subtile_patches = []
        for xy in self.initial_tiles_xy:
            rectangle = Rectangle((xy["x1"], xy["y1"]), xy["x2"] - xy["x1"], xy["y2"] - xy["y1"], edgecolor=Utils.colors["light"], facecolor=Utils.colors["dark"], zorder=1, alpha=self.opacity)
            new_patch = self.ax.add_patch(rectangle)
            new_patch.tile_xy = xy
            self.subtile_patches.append(new_patch)
        
        # Initialise status labels
        self.status_labels = []

        self.format()
        plt.draw()
        plt.pause(TilePlot.sleep_duration)
    

    def pause(self, t):
        """Freezes the plot"""
        plt.pause(t)


    def format(self):
        """De-uglifies the plot"""

        # Set plot limits
        initial_tiles_df = pd.DataFrame(self.initial_tiles_xy)
        x_min, x_max = initial_tiles_df["x1"].min(), initial_tiles_df["x2"].max()
        y_min, y_max = initial_tiles_df["y1"].min(), initial_tiles_df["y2"].max()

        # Calculate the range to make both axes equal
        max_range = max(x_max - x_min, y_max - y_min)
        self.ax.set_xlim([x_min, x_min + max_range])
        self.ax.set_ylim([y_min, y_min + max_range])

        # Set the aspect ratio to be equal and adjust to data limits
        self.ax.set_aspect("equal", adjustable="datalim")

        # Set face color
        self.fig.set_facecolor(Utils.colors["dark"])
        self.ax.set_facecolor(Utils.colors["dark"])
        self.ax.grid(False)

        # Format spines and axis labels
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["bottom"].set_visible(False)
        self.ax.spines["left"].set_visible(False)
        self.ax.xaxis.label.set_color(Utils.colors["light"])
        self.ax.yaxis.label.set_color(Utils.colors["light"])
        self.ax.title.set_color(Utils.colors["light"])
        self.ax.tick_params(axis="x", colors=Utils.colors["light"])
        self.ax.tick_params(axis="y", colors=Utils.colors["light"])


    def update(self, current_tile, new_tiles):
        """Plot is updated for each tile searched, sleeping for 0.1s between updates.
        Current tile and new_tiles change with each update. Current tile is highlighted
        in red, new_tiles (from a tile split) are added to the remaining tiles."""

        # Convert tiles to plottable format
        self.tile_xy = TilePlot.tiles_to_xy([current_tile], first=True)
        self.new_tiles_xy = TilePlot.tiles_to_xy(new_tiles)

        # Remove previous tile patch
        if self.current_tile_patch:
            self.current_tile_patch.remove()

        # Add new current tile
        current_tile_rect = Rectangle((self.tile_xy["x1"], self.tile_xy["y1"]),
                              self.tile_xy["x2"] - self.tile_xy["x1"],
                              self.tile_xy["y2"] - self.tile_xy["y1"],
                              edgecolor=self.cur_edgecolor, facecolor=self.cur_facecolor, zorder=2)
        self.current_tile_patch = self.ax.add_patch(current_tile_rect)
        self.current_tile_patch.tile_xy = self.tile_xy

        # Remove subtile under current tile
        match = None
        for subtile_patch in self.subtile_patches:
            if getattr(subtile_patch, "tile_xy", None) == self.current_tile_patch.tile_xy:
                match = subtile_patch
        if match:
            match.remove()
            self.subtile_patches.remove(match)

        # Add new subtiles
        for xy in self.new_tiles_xy:
            rectangle = Rectangle((xy["x1"], xy["y1"]), xy["x2"] - xy["x1"], xy["y2"] - xy["y1"], edgecolor=Utils.colors["light"], facecolor=Utils.colors["dark"], zorder=1, alpha=self.opacity)
            new_patch = self.ax.add_patch(rectangle)
            new_patch.tile_xy = xy
            self.subtile_patches.append(new_patch)
        
        plt.pause(TilePlot.sleep_duration)


    def update_labels(self, status):
        """Receives a dictionary of status updates and updates the labels to the right of the plot."""
        # Clear any existing labels
        for label in self.status_labels:
            label.remove()
        self.status_labels.clear()
        
        # Add new labels to the right of the plot
        self.status_labels = []
        x_pos = 1.05
        y_pos = 0.85
        for key, value in status.items():
            label = self.fig.text(x_pos, y_pos, f"{key}: {value}", transform=self.ax.transAxes, zorder=1, **self.label_font)
            self.status_labels.append(label)
            y_pos -= 0.05 
        
        plt.draw()

    @staticmethod
    def tiles_to_xy(tiles, first=False):
        """Converts a tile ID into two pairs of x,y coordinates, from 0 to 1
        Allows tiles to be plotted on an axis from 0 to 1."""

        tiles_xy = []
        for tile in tiles:
            tile_id = tile["tile_id"]

            x1, y1 = 0, 0
            x2, y2 = 1, 1
            for digit in str(tile_id):
                x_mid = (x2 + x1)/2
                y_mid = (y2 + y1)/2
                if digit in ["0", "1"]:
                    y1 = y_mid
                if digit in ["2", "3"]:
                    y2 = y_mid
                if digit in ["0", "2"]:
                    x2 = x_mid
                if digit in ["1", "3"]:
                    x1 = x_mid
            tiles_xy.append({"x1": x1, "x2": x2, "y1": y1, "y2": y2, "tile_id": tile_id})

        if first:
            return tiles_xy[0]
        return tiles_xy


    def fetch_and_display_image(self, tile_id, patch):
        """Retrives the image for a tile_id from bing maps, plots it on a given patch."""

        url = f"https://t.ssl.ak.dynamic.tiles.virtualearth.net/comp/ch/{tile_id}?mkt=en-GB&it=G,LC,BF,L,LA&shading=hill&jp=0&n=z&og=2390&cstl=s23&o=webp&ur=gb"
        response = requests.get(url)
        if response.status_code == 200:
            image = Image.open(BytesIO(response.content))
            
            # Plot image on patch
            x0, y0 = patch.get_xy()
            width, height = patch.get_width(), patch.get_height()
            self.ax.imshow(image, aspect="auto", extent=(x0, x0 + width, y0, y0 + height), zorder=0, alpha=1)


class App():
    """Main class called from the run.py file. Handles calls to other classes and their methods."""

    app_dir = get_current_path()
    root_dir = get_root_path(app_dir, max_depth=3, look_for=[".git", "requirements.txt"])
    data_dir = os.path.join(app_dir, "data")

    def __init__(self, month, name):
        """Initialises a project by creating the output folder if needed."""

        self.git = GitController.check_for_app_updates(App.root_dir, allow_force_update=True)

        self.project_name = f"{month}/{name}"
        self.project_dir = os.path.join(App.app_dir, "output", month, name)
        os.makedirs(self.project_dir, exist_ok=True)


    def load_from_file(self, filepath):
        """Load data from previously scraped ungeocoded / unaggregated file"""

        _, self.results = Utils.load_data(
            filepath = os.path.join(App.app_dir, filepath)
            )
    

    def run_scraper(self, category_ids, tile_sets, visualiser):
        """Loops over the category_ids given by user. Initialises a new MapsScraper
        for each category_id. Appends the results to the self.results df. Intermittently
        saves the data with each category_id."""
        
        self.results = []
        for category_id_i, category_id in enumerate(category_ids):
            # Initialise scraper
            scraper = MapsScraper(
                params = {
                    # API config
                    "app_id": "5BA026015AD3D08EF01FBD643CF7E9061C63A23B",
                    "category_id_i": category_id_i,
                    "category_id": category_id,
                    "chain_id": "",
                    "search_term": "",
                    "tile_sets": tile_sets,
                    "visualiser_settings": visualiser
                }
            )

            # Run scraper and save results
            self.results.extend(scraper.run())
            Utils.save_data_to_csv(
                filepath = os.path.join(self.project_dir, "scraped.csv"),
                data = self.results
                )

    
    def aggregate_results(self, gdf):
        """Finalise the results and then aggregate them by region"""

        # Finalise results
        self.results = self.geo_df.to_dict(orient="records")
        Utils.save_data_to_csv(
            filepath = os.path.join(self.project_dir, "geocoded.csv"),
            data = self.results
        )

        # Aggregate results by region
        filtered_results = self.geo_df[self.geo_df["geocoded"].isin(["within_region", "within_distance"])]
        geo_cols = [col for col in gdf.columns if col != "geometry"]
        pivot_df = pd.pivot_table(filtered_results, index=geo_cols, columns="category_id",
                                  aggfunc="size", fill_value=0)
        pivot_df = pivot_df.reset_index()

        # Rename new columns from category_id
        non_geo_cols = [col for col in pivot_df.columns if col not in geo_cols]
        rename_dict = {col: f"{col}_count" for col in non_geo_cols}
        pivot_df.rename(columns=rename_dict, inplace=True)

        # Set to zero for rows in gdf not in pivot_df
        filtered_gdf = gdf[geo_cols].reset_index(drop=True)
        pivot_df = filtered_gdf.merge(pivot_df, on=geo_cols, how="left")
        pivot_df.fillna(0, inplace=True)
        self.aggregated = pivot_df.to_dict(orient="records")


    def save_final_results(self, open_file=True):
        """Saves the final results to an xlsx file using xlwriter."""

        filename = os.path.join(self.project_dir, "final_results.xlsx")
        writer = XLWriter(filename)
        writer.add_sheet(pd.DataFrame(self.results), "Scraped Data", "Scraped Data", description="Scraped data with geocoded locations.")
        writer.add_sheet(pd.DataFrame(self.aggregated), "Aggregated Data", "Aggregated Data", description="Data aggregated by geocoded region.")
        writer.add_contents("Bing Maps Scrape Output", stars=False)
        writer.write()

        if open_file:
            open_dir(self.project_dir)
            open_dir(filename)

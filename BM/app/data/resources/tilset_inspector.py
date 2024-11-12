import json
import sys
import os

script_dir = os.path.dirname(os.path.realpath(__file__))
data_dir = os.path.dirname(script_dir)
app_dir = os.path.dirname(data_dir)
sys.path.append(app_dir)

from main import TilePlot


def view_tileset(tileset):
    """Reads a tile_set from the config.json file. Plots the tiles using TilePlot
    to preview. Helps with putting together a tileset."""

    # Read config data
    config_path = os.path.join(data_dir, "config.json")
    with open(config_path, "r") as json_file:
        config_data = json.load(json_file)

    # Get list of tile_ids
    tileset_data = config_data["tile_sets"][tileset]
    tile_ids = []
    for tile in tileset_data["tiles"]:
        tile_ids.append({"tile_id": tile})
    
    # Visualise the tiles using TilePlot, setting the opacity to 0.25 to highlight overlapping tiles
    plot = TilePlot(
        tile_ids,
        settings={
            "display": True,
            "overlay_map": True,
            "overlay_ids": True,
        }
    )
    plot.pause(9999999)


if __name__ == "__main__":
    view_tileset("uk")
import time
import json
import sys
import os

import pandas as pd
import geopandas as gpd


script_dir = os.path.dirname(os.path.realpath(__file__))
data_dir = os.path.dirname(script_dir)
app_dir = os.path.dirname(data_dir)
sys.path.append(app_dir)


def inspect_geojson(file_name):
    """Inspects a geojson file by reading it as a gpd."""

    file_path = os.path.join(data_dir, "geojson", file_name)
    gdf = gpd.read_file(file_path)

    # Describe gdf
    print(gdf)
    print(gdf.columns)
    print(gdf.info)
    print(gdf.crs)
    print(gdf.shape)
    print(gdf.describe())

    # gdf.rename(columns={"name": "country"}, inplace=True)
    # gdf.to_file(file_path, driver="GeoJSON")
    


if __name__ == "__main__":
    inspect_geojson("countries.geojson")
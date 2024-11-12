import geopandas as gpd
import pandas as pd 
import sys
import os

path = f"{sys.path[0]}"
# lad = gpd.read_file(os.path.join(path, "uk_lad.json"))
# lgd = gpd.read_file(os.path.join(path, "uk_lgd.json"))

# lad['name'] = lad['LAD13NM']
# lgd['name'] = lgd['LGDNAME']

# lad_geojson = lad[['name', 'geometry']]
# lgd_geojson = lgd[['name', 'geometry']]

# merged_geojson = pd.concat([lad, lgd], ignore_index=True)
# merged_geojson.to_file(os.path.join(path, "uk_all"), driver='GeoJSON')

# lad = gpd.read_file(os.path.join(path, "uk_lads_converted.geojson"))
# cnt = gpd.read_file(os.path.join(path, "uk_lads.geojson"))
us = gpd.read_file(os.path.join(path, "us.geojson"))
# lad_crs = lad.crs
# us_crs = us.crs
# cnt_crs = cnt.crs
# print("UK new GeoJSON CRS:", lad_crs)
# print("US GeoJSON CRS:", us_crs)
# print("uk old GeoJSON CRS:", cnt_crs)

print(us)
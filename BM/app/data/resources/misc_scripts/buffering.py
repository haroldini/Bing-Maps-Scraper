from shapely.geometry import Point, Polygon
import geopandas as gpd
import matplotlib.pyplot as plt

# Create a GeoDataFrame with two adjacent polygons representing countries
polygon1 = Polygon([(0, 0), (0, 2), (2, 2), (2, 0)])
polygon2 = Polygon([(2, 0), (2, 2), (4, 2), (4, 0)])

gdf = gpd.GeoDataFrame(geometry=[polygon1, polygon2], crs="EPSG:4326")

# Plot the original geometries
gdf.plot(color=['blue', 'green'], alpha=0.5)
plt.title("Original Geometries")
plt.show()

# Apply a buffer to each geometry and dissolve individually
buffer_distance = 0.5
buffered_geometries = [country.buffer(buffer_distance) for country in gdf.geometry]

# Create a new GeoDataFrame with the buffered geometries
buffered_gdf = gpd.GeoDataFrame(geometry=buffered_geometries, crs="EPSG:4326")

# Plot the individual buffered geometries
buffered_gdf.plot(color='red', alpha=0.5)
plt.title("Buffered Geometries")
plt.show()

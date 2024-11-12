import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle


def tile_to_xy(tile):
    tile_id = tile#["tile_id"]

    x1, y1 = 0, 0
    x2, y2 = 1, 1
    for digit in tile_id:
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
    coords.append({"x1": x1, "x2": x2, "y1": y1, "y2": y2})


tiles = [
                "002",
                "02",
                "0302",
                "0303",
                "0320"
]

coords = []
for tile in tiles:
    tile_to_xy(tile)

print(coords)

df_rectangles = pd.DataFrame(coords)

sns.set(style="whitegrid")

# Create a Seaborn scatter plot (or any other type of plot)
sns.scatterplot(x='x1', y='y1', data=df_rectangles, marker='o', color='red', label='Top Left Corner')
sns.scatterplot(x='x2', y='y2', data=df_rectangles, marker='o', color='blue', label='Bottom Right Corner')

# Create rectangles using matplotlib.patches.Rectangle
ax = plt.gca()
for index, row in df_rectangles.iterrows():
    rectangle = Rectangle((row['x1'], row['y1']), row['x2'] - row['x1'], row['y2'] - row['y1'], edgecolor='green', facecolor='none')
    ax.add_patch(rectangle)

# Show the plot
plt.legend()
plt.show()
from app.main import App, Utils
from sidt.utils.geocoders import Geocoder

if __name__ == "__main__":

    """Initialise the app"""
    app = App(
        month = "2024-11",
        name = "testing-ui-changes",
    )

    """Load previously scraped data from a file"""
    # app.load_from_file("output/testing/us_can_hunting_stores/scraped.csv")
    
    """Run the scraper"""
    app.run_scraper(
        category_ids=["30049"],
        tile_sets = ["uk"],
        visualiser = {
            "display": True,
            "overlay_map": True,
            "overlay_ids": False,
        }
    )
    Utils.display_scatter(app.results)

    """
    Geocode the scrape results / previously scraped data
    Valid packages: us_states, us_counties, us_primary_roads, european_countries, countries, uk_local_authorities
    """
    app.geo_df, gdf = Geocoder.find_regions_within_distance(app.results, distance=100, package_gdf="uk_local_authorities", return_gdf=True)

    """Save the results to a file"""
    app.aggregate_results(gdf)
    app.save_final_results(open_file=True)
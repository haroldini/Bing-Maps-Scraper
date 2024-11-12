from app.main import App, Utils

if __name__ == "__main__":

    """Initialise the app"""
    app = App(
        project_name = "samples/europe-fire-stations"
    )

    """Load previously scraped data from a file"""
    # app.load_from_file("output/samples/europe-fire-stations/scraped.csv")
    
    """Run the scraper, use arg visualise_search=False to disable plot"""
    app.run_scraper(
        category_ids=["91256"],
        tile_sets = ["europe"],
        visualiser = {
            "display": True,
            "overlay_map": True,
            "overlay_ids": False,
        }
    )
    Utils.display_scatter(app.results)

    """Geocode the scrape results / previously scraped data"""
    app.geocode_data(geocode_by="europe_countries")

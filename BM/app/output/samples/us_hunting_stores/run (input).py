from app.main import App, Utils

if __name__ == "__main__":

    """Initialise the app"""
    app = App(
        project_name = "samples/us-hunting-stores"
    )

    """Load previously scraped data from a file"""
    # app.load_from_file("output/samples/us-hunting-stores/scraped.csv")
    
    """Run the scraper, use arg visualise_search=False to disable plot"""
    app.run_scraper(
        category_ids=["91521"],
        tile_sets = ["us_can"],
        )
    Utils.display_scatter(app.results)

    """Geocode the scrape results / previously scraped data"""
    app.geocode_data(geocode_by="us_states")
    
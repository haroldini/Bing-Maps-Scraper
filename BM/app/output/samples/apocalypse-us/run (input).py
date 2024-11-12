from app.main import App, Utils

if __name__ == "__main__":

    """Initialise the app"""
    app = App(
        project_name = "samples/apocalypse-us"
    )

    """Load previously scraped data from a file"""
    # app.load_from_file("output/samples/apocalypse-us/scraped.csv")
    
    """Run the scraper, use arg visualise_search=False to disable plot"""
    app.run_scraper(
        category_ids=["90078", "90089", "90331", "90408", "90287", "90541", "90738", "90749", "90771", "90804", "90826", "91256", "91521", "91523"],
        tile_sets = ["us_can"],
        )
    Utils.display_scatter(app.results)

    """Geocode the scrape results / previously scraped data"""
    app.geocode_data(geocode_by="us_states")
    
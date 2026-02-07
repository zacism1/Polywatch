import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    @staticmethod
    def database_uri():
        default_path = os.path.join(os.getcwd(), "instance", "politracker.db")
        return os.environ.get("DATABASE_URL", f"sqlite:///{default_path}")

    SQLALCHEMY_DATABASE_URI = database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SCHEDULER_ENABLED = os.environ.get("SCHEDULER_ENABLED", "1") == "1"

    USER_AGENT = os.environ.get(
        "SCRAPER_USER_AGENT",
        "PoliTrackerBot/1.0 (contact: admin@example.com)",
    )
    REQUEST_TIMEOUT_SECS = int(os.environ.get("REQUEST_TIMEOUT_SECS", "20"))
    REQUEST_DELAY_SECS = float(os.environ.get("REQUEST_DELAY_SECS", "2.0"))
    REQUEST_RETRIES = int(os.environ.get("REQUEST_RETRIES", "3"))

    APH_REGISTER_URLS = {
        "house": os.environ.get(
            "APH_REGISTER_HOUSE_PDF",
            "https://www.aph.gov.au/Senators_and_Members/Members/Register",
        ),
        "senate": os.environ.get(
            "APH_REGISTER_SENATE_PDF",
            "https://www.aph.gov.au/Parliamentary_Business/Committees/Senate/Senators_Interests/Tabled_volumes",
        ),
    }

    APH_HANSARD_BASE = os.environ.get(
        "APH_HANSARD_BASE",
        "https://www.aph.gov.au/Parliamentary_Business/Hansard",
    )

    MARKET_DATA_PROVIDER = os.environ.get("MARKET_DATA_PROVIDER", "yahoo")
    ALPHA_VANTAGE_API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY", "")

    PRICE_GAIN_THRESHOLD = float(os.environ.get("PRICE_GAIN_THRESHOLD", "0.15"))
    CORRELATION_WINDOW_DAYS = int(os.environ.get("CORRELATION_WINDOW_DAYS", "30"))

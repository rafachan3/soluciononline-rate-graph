import pandas as pd
from browser_manager import BrowserManager
from plan_quoter import Quoter
from selenium.webdriver.common.by import By
import logging
from logging.handlers import RotatingFileHandler
from database_handler import DatabaseHandler

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log", mode="w"),  # Overwrites the log file on each run
    ]
)

# Suppress logs from Selenium and other third-party libraries
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Create a logger for this module
logger = logging.getLogger(__name__)

class MainController:
    def __init__(self):
        browser_manager = BrowserManager()
        logger.info("Initializing MainController...")
        self.browser_manager = browser_manager  # Use the shared BrowserManager instance
        self.quoter = Quoter(self.browser_manager)  # Pass it to Quoter
        self.db_handler = DatabaseHandler()  # Initialize database handler
        self.browser_manager.login()  # Log in using the browser manager
        self.browser_manager.create_initial_prospect()
        self.browser_manager.set_age_start_quoting(71)

        self.products = [
            {
                'product': 'Alfa Medical',
                'product_identifier': (By.ID, '60'),
                'plans': [
                    {'name': 'Pleno', 'value': '060001001213'},
                    {'name': 'Integro', 'value': '060001001214'}
                ]
            },
            {
                'product': 'Alfa Medical Flex',
                'product_identifier': (By.ID, '72'),
                'plans': [
                    {'name': 'Flex A', 'value': '060001001217'},
                    {'name': 'Flex B', 'value': '060001001219'}
                ]
            }
        ]

        self.plans_df = {}

    def run(self):
        logger.info("Starting the quoting process...")
        for product in self.products:
            logger.info(f"Processing product: {product['product']}")
            self.process_product_plans(product)

        logger.info("Saving dataframes...")
        self.save_dataframes()
        logger.info("Quoting process completed.")

    def process_product_plans(self, product):
        logger.info(f"Accessing product: {product['product']}")
        self.quoter.access_product(product['product_identifier'])

        for plan in product['plans']:
            logger.info(f"Processing plan: {plan['name']}")
            self.process_plan(plan, product)

    def process_plan(self, plan, product):
        logger.info(f"Selecting plan: {plan['name']}")
        dropdown_selector = (By.ID, "ddlPlan")
        self.quoter.select_plan_from_dropdown(dropdown_selector, plan['value'])

        start_age = 71 if plan['name'] == 'Pleno' else 0

        for age in range(start_age, 75):
            logger.debug(f"Quoting for age: {age}")
            data = self.quoter.quote_plan(age, plan, product)
            # Store data in database
            self.db_handler.insert_plan_data(plan['name'], age, data)

        logger.info(f"Saving data for plan: {plan['name']}")

    def save_dataframes(self):
        # Export to Excel from database
        output_file = self.db_handler.export_to_excel()
        logger.info(f"All data exported to {output_file}")
        
if __name__ == '__main__':
    logger.info("Starting the application...")
    controller = MainController()
    try:
        controller.run()
    except Exception as e:
        logger.critical(f"An unhandled exception occurred: {e}", exc_info=True)

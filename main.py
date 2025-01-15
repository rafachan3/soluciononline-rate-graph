import pandas as pd
from browser_manager import BrowserManager
from plan_quoter import Quoter
from selenium.webdriver.common.by import By
import logging
from logging.handlers import RotatingFileHandler

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
        self.browser_manager.login()  # Log in using the browser manager
        self.browser_manager.create_initial_prospect()
        self.browser_manager.set_age_start_quoting(0)

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

        plan_data = []
        for age in range(0, 76):
            logger.debug(f"Quoting for age: {age}")
            data = self.quoter.quote_plan(age, plan, product)
            plan_data.append({'Edad': age, **data})

        logger.info(f"Saving data for plan: {plan['name']}")
        self.plans_df[plan['name']] = pd.DataFrame(plan_data)

    def save_dataframes(self):
        for plan_name, dataframe in self.plans_df.items():
            filename = f"{plan_name.replace(' ', '_').lower()}_data.csv"
            dataframe.to_csv(filename, index=False)
            logger.info(f"Data for {plan_name} saved to {filename}")

if __name__ == '__main__':
    logger.info("Starting the application...")
    controller = MainController()
    try:
        controller.run()
    except Exception as e:
        logger.critical(f"An unhandled exception occurred: {e}", exc_info=True)

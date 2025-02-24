from config import PRODUCTS, ELEMENT_IDS, AGE_RANGE
import pandas as pd
from browser_manager import BrowserManager
from plan_quoter import Quoter
from selenium.webdriver.common.by import By
import logging
from exceptions import QuoterError, PlanSelectionError, DataCollectionError, NavigationError, ElementInteractionError
from database_handler import DatabaseHandler
from logging_config import setup_logging
import time

# Initialize logging at the start of your program
logger = setup_logging()
logger.info("Application starting...")

class MainController:
    def __init__(self):
        browser_manager = BrowserManager()
        logger.info("Initializing MainController...")
        self.browser_manager = browser_manager  # Use the shared BrowserManager instance
        self.quoter = Quoter(self.browser_manager)  # Pass it to Quoter
        self.db_handler = DatabaseHandler()  # Initialize database handler
        self.browser_manager.login()  # Log in using the browser manager
        self.browser_manager.create_initial_prospect()  # Create initial prospect with defaults

        self.products = PRODUCTS

    def run(self):
        start_time = time.time()
        logger.info("Starting the quoting process...")
        
        for product in self.products:
            self.process_product_plans(product)

        logger.info("Saving dataframes...")
        self.save_dataframes()

        total_time = time.time() - start_time
        logger.info(f"Quoting process completed in {total_time:.2f} seconds.")

    def process_product_plans(self, product):
        logger.info(f"Processing product: {product['product']}")

        # Reset age to 0 and start quote process before accessing new product
        logger.debug("Setting age to 0 before processing new product...")
        self.browser_manager.set_age_start_quoting(0)

        logger.debug(f"Accessing product: {product['product']}")
        self.quoter.access_product(product['product_identifier'], product['product'])

        for plan in product['plans']:
            self.process_plan(plan, product)
        
        logger.info(f"Completed processing all plans for {product['product']}")

    def process_plan(self, plan, product):
        logger.info(f"[{product['product']}/{plan['name']}] Processing Plan")

        try:
        
            # Select the plan from dropdown
            logger.debug(f"[{product['product']}/{plan['name']}] Selecting Plan")
            dropdown_selector = (By.ID, ELEMENT_IDS['plan']['plan_dropdown'])
            self.quoter.select_plan_from_dropdown(dropdown_selector, plan, product)

            # Process all ages for this plan
            for age in range(AGE_RANGE['min_age'], AGE_RANGE['max_age'] + 1):
                logger.debug(f"[{product['product']}/{plan['name']}] Quoting for age: {age}")
                try: 
                    # Quote and collect data for current age
                    data = self.quoter.quote_plan(age, plan, product)

                    if data:  # Only store if we got valid data
                        self.db_handler.insert_plan_data(plan['name'], age, data)
                    else:
                        logger.warning(f"No data collected for {plan['name']} at age {age}")
                
                    if age < AGE_RANGE['max_age']:
                        self._prepare_next_age(age, product, dropdown_selector, plan)

                except QuoterError as e:
                    logger.error(f"Failed to process age {age} for plan {plan['name']}: {str(e)}")
                    continue  # Skip to next age if there's an error

        except Exception as e:
            logger.error(f"Failed to process plan {plan['name']}: {str(e)}")

        logger.info(f"[{product['product']}/{plan['name']}] Completed processing all ages for plan")

         # If this isn't the last plan, reset age to 0 and start quote process for next plan
        if plan != product['plans'][-1]:
            logger.debug("Resetting age to 0 before processing next plan...")
            self.browser_manager.set_age_start_quoting(0)
            # Reaccess product after resetting age
            self.quoter.access_product(product['product_identifier'], product['product'])

    def _prepare_next_age(self, age, product, dropdown_selector, plan):
        """Prepares the system for processing the next age by resetting the necessary states.
        
        Args:
            age (int): Current age being processed
            product (dict): Product information dictionary
            dropdown_selector (tuple): Selector tuple for the plan dropdown
            plan (dict): Plan information dictionary
        """
        logger.debug(f"[{product['product']}/{plan['name']}] Setting up for next age: {age + 1}")
        
        try:
            # Set the next age and start quote process
            self.browser_manager.set_age_start_quoting(age + 1)
            
            # Reaccess product after setting new age
            self.quoter.access_product(product['product_identifier'], product['product'])
            
            # Reselect plan
            self.quoter.select_plan_from_dropdown(dropdown_selector, plan, product)
            
        except Exception as e:
            logger.error(f"Failed to prepare for next age: {str(e)}")
            raise NavigationError(f"Could not set up for age {age + 1}") from e

    def save_dataframes(self):
        # Export to Excel from database
        output_file = self.db_handler.export_to_excel()
        logger.info(f"All data exported to {output_file}")
        
if __name__ == '__main__':
    controller = MainController()
    try:
        controller.run()
    except Exception as e:
        logger.critical(f"An unhandled exception occurred: {e}", exc_info=True)

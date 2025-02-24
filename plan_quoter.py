import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException
from config import ELEMENT_IDS, PLAN_CONFIG, RETRY_CONFIG, COVERAGE_OPTIONS
from exceptions import QuoterError, PlanSelectionError, DataCollectionError, NavigationError, ElementInteractionError
import time
from data_collector import DataCollector

logger = logging.getLogger(__name__)

class Quoter:
    def __init__(self, browser_manager):
        self.browser_manager = browser_manager  # Assign the passed instance
        self.wait = browser_manager.wait       # Reuse WebDriverWait from BrowserManager
        self.data_collector = DataCollector(self.wait)  # Initialize DataCollector
        self.data = []                         # Initialize other data attributes if needed

    def access_product(self, product_identifier):
        start_time = time.time()
        logger.info("Waiting for product button to become clickable...")
        product_button = self.wait.until(EC.element_to_be_clickable(product_identifier))
        product_button.click()
        logger.info("Product button clicked.")

        try:
            try:
                logger.info("Waiting for 'btn_nvo' button to become clickable...")
                plan_type_button = self.wait.until(EC.element_to_be_clickable((By.ID, 'btn_nvo')))
                logger.info("'btn_nvo' button is clickable.")
            except ElementNotInteractableException:
                plan_type_button = self.wait.until(EC.element_to_be_clickable((By.ID, 'btn_nvo')))
                logger.info("'btn_nvo' button is clickable.")
        except TimeoutException:
            logger.error("Timeout: 'btn_nvo' button was not found or not clickable.")
            raise

        logger.info("Handling pop-up...")
        plan_type_button.click()
        accept_button = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'btn-success')))
        accept_button.click()
        logger.info("Pop-up handled.")
        logger.info(f"Product access completed in {time.time() - start_time:.2f} seconds")

    def select_plan_from_dropdown(self, dropdown_selector, plan_value):
        if plan_value == "060001001213" or plan_value == "060001001219":
            return
            
        # Create a quick wait with 2 second timeout
        quick_wait = WebDriverWait(self.browser_manager.driver, RETRY_CONFIG['short_wait_time'])
        logger.info("Attempting to locate plan dropdown...")
        
        try:
            # Try the first selector with quick wait
            dropdown_menu = quick_wait.until(EC.presence_of_element_located(dropdown_selector))
        except TimeoutException:
            # If first selector fails, try the alternative immediately
            logger.info("Primary dropdown selector not found, trying alternative...")
            alternative_selector = (By.ID, "ctl00_ContentPlaceHolder1_ddlPlan")
            try:
                dropdown_menu = quick_wait.until(EC.presence_of_element_located(alternative_selector))
                logger.info("Alternative dropdown selector found successfully")
            except TimeoutException:
                logger.error("Both dropdown selectors failed")
                raise
        
        # Once we have the dropdown, proceed with selection using normal wait times
        dropdown_menu.click()
        plan_option = self.wait.until(
            EC.presence_of_element_located((By.XPATH, f'//option[@value="{plan_value}"]'))
        )
        plan_option.click()

        self.browser_manager.pop_up_handler()

        self.wait.until(EC.invisibility_of_element((By.ID, 'modal')))
        logger.info("Modal no longer visible. Proceeding with the next step.")

    def quote_plan(self, age, plan, product):
        max_retries = RETRY_CONFIG['max_quote_retries']
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"Quoting plan: {plan['name']} for age {age}")

                if plan['name'] in ["Pleno", "Integro"]:
                    return self._handle_pleno_integro_plan(plan, age)
                elif plan['name'] in ["Flex A", "Flex B"]:
                    return self._handle_flex_plan(plan, age)
                else:
                    raise PlanSelectionError(f"Unknown plan type: {plan['name']}")
            
            except ElementInteractionError as e:
                logger.error(f"Failed to interact with element: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Retrying quote_plan (attempt {retry_count + 1} of {max_retries})")
                    self.browser_manager.driver.refresh()
                    continue
                raise QuoterError(f"Failed to quote plan after {max_retries} attempts") from e
            
            except DataCollectionError as e:
                logger.error(f"Failed to collect plan data: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Retrying data collection (attempt {retry_count + 1} of {max_retries})")
                    self.browser_manager.driver.refresh()
                    continue
                return {}
            
            except NavigationError as e:
                logger.error(f"Navigation failed: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Retrying navigation (attempt {retry_count + 1} of {max_retries})")
                    self.browser_manager.driver.refresh()
                    continue
                raise QuoterError(f"Navigation failed after {max_retries} attempts") from e
            
    def _handle_pleno_integro_plan(self, plan, age):
        """Handle quoting process for Pleno and Integro (Alfa Medical) plans"""
        try:
            # Set state of residence
            self._set_residence('alfa_medical')
            
            # Set deductible
            self._set_deductible_amount()

            self._set_unique_deductible()
            
            # Set coverage options
            self._set_coverage_options_pleno_integro()
            
            # Calculate and collect data
            data = self._calculate_and_collect_data(plan, age)

            # Navigate back
            self._navigate_back_to_start()
            
            return data
            
        except Exception as e:
            raise DataCollectionError(f"Error processing {plan['name']} plan: {str(e)}")

    def _handle_flex_plan(self, plan, age):
        """Handle quoting process for Flex plans"""
        try:
            # Set state of residence
            self._set_residence('flex')
            
            # Set coverage options
            self._set_coverage_options_flex()
            
            # Calculate and collect data
            data = self._calculate_and_collect_data(plan, age)

            # Navigate back
            self._navigate_back_to_start()

            return data
            
        except Exception as e:
            raise DataCollectionError(f"Error processing {plan['name']} plan: {str(e)}")
        
    def _set_residence(self, plan_type):
        """Set residence to Veracruz based on plan type
        
        Args:
            plan_type (str): The type of plan ('flex' or 'alfa_medical')
        """
        try:
            # Select the appropriate residence element ID based on plan type
            residence_id = (ELEMENT_IDS['plan']['residence_dropdown']['flex'] 
                        if plan_type == 'flex' 
                        else ELEMENT_IDS['plan']['residence_dropdown']['alfa_medical'])
            
            # Get the appropriate option xpath based on plan type
            option_xpath = (f'//*[@id="ctl00_ContentPlaceHolder1_ddlResidencia"]/option[{PLAN_CONFIG["state_option_index"]}]'
                        if plan_type == 'flex'
                        else f'//*[@id="ddlResidencia"]/option[{PLAN_CONFIG['state_option_index']}]')

            logger.info(f"Setting residence for {plan_type} plan type")
            
            # Locate and click residence dropdown
            residence = self.wait.until(EC.presence_of_element_located((By.ID, residence_id)))
            residence.click()
            
            # Select Veracruz option
            residence_option = self.wait.until(
                EC.presence_of_element_located((By.XPATH, option_xpath))
            )
            residence_option.click()
            
            # Handle popup
            self.browser_manager.pop_up_handler()
            self.wait.until(EC.invisibility_of_element((By.ID, 'modal')))
            logger.info("Residence set successfully")
            
        except Exception as e:
            raise ElementInteractionError(f"Failed to set residence for {plan_type} plan: {str(e)}")
        
    def _set_deductible_amount(self):
        """Set deductible to 40,000"""
        try:
            logger.info("Setting deductible to 40,000")
            
            # Locate and click deductible dropdown
            deductible = self.wait.until(EC.presence_of_element_located((By.ID, ELEMENT_IDS['plan']['deductible_dropdown'])))
            deductible.click()
            
            # Select 40,000 option
            deductible_option = self.wait.until(
                EC.presence_of_element_located((By.XPATH, f'//*[@id="ddlDeducible"]/option[{PLAN_CONFIG["deductible_option_index"]}]'))
            )
            deductible_option.click()
            logger.info("Deductible set successfully")
            
        except Exception as e:
            raise ElementInteractionError(f"Failed to set deductible: {str(e)}")
        
    def _set_unique_deductible(self):
        """Check 'Deducible único' checkbox"""
        try:
            logger.info("Checking 'Deducible único' checkbox")
            
            # Locate and click checkbox
            unique_deductible = self.wait.until(EC.element_to_be_clickable((By.ID, ELEMENT_IDS['plan']['unique_deductible'])))
            unique_deductible.click()
            logger.info(" Unique deductible checkbox checked successfully")
            
        except Exception as e:
            raise ElementInteractionError(f"Failed to check 'Deducible único' checkbox: {str(e)}")
        
    def _set_coverage_options_pleno_integro(self):
        """Set coverage options for Alfa Medical plans using config"""
        try:
            logger.info("Setting coverage options for Alfa Medical plans")
            
            for option_key, option_data in COVERAGE_OPTIONS['alfa_medical'].items():
                checkbox = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, option_data['xpath'])
                ))
                checkbox.click()
                logger.info(f"Set {option_data['description']}")
                
        except Exception as e:
            raise ElementInteractionError(f"Failed to set coverage options for Alfa Medical plans: {str(e)}")
        
    def _set_coverage_options_flex(self):
        """Set coverage options for Flex plans using config"""
        try:
            logger.info("Setting coverage options for Alfa Medical Flex plans")
            
            for option_key, option_data in COVERAGE_OPTIONS['flex'].items():
                checkbox = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, option_data['xpath'])
                ))
                checkbox.click()
                logger.info(f"Set {option_data['description']}")
                
        except Exception as e:
            raise ElementInteractionError(f"Failed to set coverage options for Alfa Medical Flex plans: {str(e)}")
            
        except Exception as e:
            raise ElementInteractionError(f"Failed to set coverage options for Alfa Medical Flex plans: {str(e)}")
    
    def _calculate_and_collect_data(self, plan, age):
        """Switch to results tab, calculate plan details and collect resulting data.
        
        Args:
            plan (dict): The plan information dictionary
            
        Returns:
            dict: The collected data or empty dict if collection fails
            
        Raises:
            DataCollectionError: If calculation or data collection fails
        """
        start_time = time.time()
        try:
            # Click Calculate button
            calculate_button = self.wait.until(EC.element_to_be_clickable(
                (By.ID, ELEMENT_IDS['plan']['calculate_button'])
                ))
            calculate_button.click()
            logger.info("Calculate button clicked.")
            
            # Switch to results tab using dedicated method
            self._switch_to_results_tab()
                    
            # Collect and return data
            logger.info(f"Collecting data for plan: {plan['name']}")

            data = self.data_collector.collect_all_data()

            quote_time = time.time() - start_time
            logger.info(f"Successfully quoted {plan['name']} plan for age {age} in {quote_time:.2f} seconds")

            logger.info(f"Data collected: {data}")
            
            return data or {}
            
        except Exception as e:
            logger.error(f"Failed to calculate and collect data in {time.time() - start_time:.2f} seconds: {str(e)}")
            raise DataCollectionError(f"Failed to calculate and collect data: {str(e)}")
        
    def _switch_to_results_tab(self):
        """Switch to the Results tab with retry logic and popup handling.
        
        This method attempts to switch to the 'Resultado' tab multiple times if needed,
        handling any popups that appear during the process.
        
        Raises:
            NavigationError: If unable to switch to the Results tab after all retries
        """
        tab_retries = RETRY_CONFIG['max_tab_retries']
        
        for attempt in range(tab_retries):
            try:
                # Handle any popups that might be blocking the tab
                self.browser_manager.pop_up_handler()
                
                # Wait for the Results tab to be clickable
                result_tab = self.wait.until(
                    EC.element_to_be_clickable((By.LINK_TEXT, ELEMENT_IDS['plan']['result_tab']))
                )
                
                # Try to click the tab
                result_tab.click()
                logger.info("Successfully switched to 'Resultado' tab")
                
                # Verify we actually switched tabs by checking for a unique element
                self.wait.until(
                    EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_txbSumaAsegurada'))
                )
                
                return  # Success - exit the method
                
            except Exception as e:
                if attempt == tab_retries - 1:
                    # If this was our last attempt, raise the error
                    logger.error(f"Failed to switch to Results tab after {tab_retries} attempts")
                    raise NavigationError(f"Could not switch to Results tab: {str(e)}") from e
                
                logger.warning(f"Failed to switch to Results tab, attempt {attempt + 1} of {tab_retries}: {str(e)}")
                time.sleep(1)  # Short pause before retrying
    
    def _navigate_back_to_start(self):
        """Navigate back to the starting page using the two back buttons"""
        try:
            first_back_button = self.wait.until(EC.element_to_be_clickable(
                (By.ID, ELEMENT_IDS['plan']['back_button_1'])
                ))
            first_back_button.click()
            
            second_back_button = self.wait.until(EC.element_to_be_clickable(
                (By.ID, ELEMENT_IDS['plan']['back_button_2'])
                ))
            second_back_button.click()
            
            logger.info("Successfully navigated back to start")
            
        except Exception as e:
            raise NavigationError("Failed to navigate back to start") from e

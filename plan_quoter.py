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

    def access_product(self, product_identifier, product_name):
        start_time = time.time()
        logger.debug(f"[{product_name}] Waiting for product button to become clickable...")
        product_button = self.wait.until(EC.element_to_be_clickable(product_identifier))
        product_button.click()

        try:
            try:
                logger.debug("Waiting for 'btn_nvo' button to become clickable...")
                plan_type_button = self.wait.until(EC.element_to_be_clickable((By.ID, 'btn_nvo')))
            except ElementNotInteractableException:
                plan_type_button = self.wait.until(EC.element_to_be_clickable((By.ID, 'btn_nvo')))
        except TimeoutException:
            logger.error("Timeout: 'btn_nvo' button was not found or not clickable.")
            raise

        logger.debug("Handling pop-up...")
        plan_type_button.click()
        accept_button = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'btn-success')))
        accept_button.click()
        logger.info(f"[{product_name}] Product access completed in {time.time() - start_time:.2f} seconds")

    def select_plan_from_dropdown(self, dropdown_selector, plan, product):
        if plan['value'] == "060001001213" or plan['value'] == "060001001219":
            return
            
        # Create a quick wait for the initial dropdown selection
        quick_wait = WebDriverWait(self.browser_manager.driver, RETRY_CONFIG['short_wait_time'])
        logger.debug(f"[{product['product']}/{plan['name']}] Attempting to locate plan dropdown...")
        
        try:
            # Try the first selector with quick wait
            dropdown_menu = quick_wait.until(EC.presence_of_element_located(dropdown_selector))
        except TimeoutException:
            # If first selector fails, try the alternative immediately
            logger.debug(f"[{product['product']}/{plan['name']}] Primary dropdown selector not found, trying alternative...")
            alternative_selector = (By.ID, "ctl00_ContentPlaceHolder1_ddlPlan")
            try:
                dropdown_menu = quick_wait.until(EC.presence_of_element_located(alternative_selector))
                logger.debug(f"[{product['product']}/{plan['name']}] Alternative dropdown selector found successfully")
            except TimeoutException:
                logger.error(f"[{product['product']}/{plan['name']}] Both dropdown selectors failed")
                raise
        
        # Once we have the dropdown, proceed with selection using normal wait times
        dropdown_menu.click()
        plan_option = self.wait.until(
            EC.presence_of_element_located((By.XPATH, f'//option[@value="{plan['value']}"]'))
        )
        plan_option.click()

        self.browser_manager.pop_up_handler()

        self.wait.until(EC.invisibility_of_element((By.ID, 'modal')))

    def quote_plan(self, age, plan, product):
        max_retries = RETRY_CONFIG['max_quote_retries']
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                if plan['name'] in ["Pleno", "Integro"]:
                    return self._handle_pleno_integro_plan(product, plan, age)
                elif plan['name'] in ["Flex A", "Flex B"]:
                    return self._handle_flex_plan(product, plan, age)
                else:
                    raise PlanSelectionError(f"Unknown plan type: {plan['name']}")
            
            except ElementInteractionError as e:
                logger.error(f"[{product['product']}/{plan['name']}/Age {age}] Failed to interact with element: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"[{product['product']}/{plan['name']}/Age {age}] Retrying quote_plan (attempt {retry_count + 1} of {max_retries})")
                    self.browser_manager.driver.refresh()
                    continue
                raise QuoterError(f"[{product['product']}/{plan['name']}/Age {age}] Failed to quote plan after {max_retries} attempts") from e
            
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
            
    def _handle_pleno_integro_plan(self, product, plan, age):
        """Handle quoting process for Pleno and Integro (Alfa Medical) plans"""
        try:
            # Set state of residence
            self._set_residence(product, plan, age)
            
            # Set deductible
            self._set_deductible_amount(product, plan, age)

            self._set_unique_deductible(product, plan, age)
            
            # Set coverage options
            self._set_coverage_options_pleno_integro(product, plan, age)
            
            # Calculate and collect data
            data = self._calculate_and_collect_data(product, plan, age)

            # Navigate back
            self._navigate_back_to_start()
            
            return data
            
        except Exception as e:
            raise DataCollectionError(f"[{product['product']}/{plan['name']}/Age {age}] Error processing the plan: {str(e)}")

    def _handle_flex_plan(self, product, plan, age):
        """Handle quoting process for Alfa Medical Flex plans"""
        try:
            # Set state of residence
            self._set_residence(product, plan, age)
            
            # Set coverage options
            self._set_coverage_options_flex(product, plan, age)
            
            # Calculate and collect data
            data = self._calculate_and_collect_data(product, plan, age)

            # Navigate back
            self._navigate_back_to_start()

            return data
            
        except Exception as e:
            raise DataCollectionError(f"[{product['product']}/{plan['name']}/Age {age}] Error processing the plan: {str(e)}")
        
    def _set_residence(self, product, plan, age):
        """Set residence to Veracruz based on plan type
        
        Args:
            product (dict): The product information dictionary
            plan (dict): The plan information dictionary
            age (int): The age being processed
            plan_type (str): The type of plan ('flex' or 'alfa_medical')
        """
        try:
            # Select the appropriate residence element ID based on plan type
            residence_id = (ELEMENT_IDS['plan']['residence_dropdown']['flex'] 
                        if product['product'] == 'Alfa Medical Flex'
                        else ELEMENT_IDS['plan']['residence_dropdown']['alfa_medical'])
            
            # Get the appropriate option xpath based on plan type
            option_xpath = (f'//*[@id="ctl00_ContentPlaceHolder1_ddlResidencia"]/option[{PLAN_CONFIG["state_option_index"]}]'
                        if product['product'] == 'Alfa Medical Flex'
                        else f'//*[@id="ddlResidencia"]/option[{PLAN_CONFIG['state_option_index']}]')

            logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Setting residence")
            
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
            
        except Exception as e:
            raise ElementInteractionError(f"[{product['product']}/{plan['name']}] Failed to set residence: {str(e)}")
        
    def _set_deductible_amount(self, product, plan, age):
        """Set deductible to 40,000"""
        try:
            logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Setting deductible to 40,000")
            
            # Locate and click deductible dropdown
            deductible = self.wait.until(EC.presence_of_element_located((By.ID, ELEMENT_IDS['plan']['deductible_dropdown'])))
            deductible.click()
            
            # Select 40,000 option
            deductible_option = self.wait.until(
                EC.presence_of_element_located((By.XPATH, f'//*[@id="ddlDeducible"]/option[{PLAN_CONFIG["deductible_option_index"]}]'))
            )
            deductible_option.click()
            
        except Exception as e:
            raise ElementInteractionError(f"[{product['product']}/{plan['name']}/Age {age}] Failed to set deductible: {str(e)}")
        
    def _set_unique_deductible(self, product, plan, age):
        """Check 'Deducible único' checkbox"""
        try:
            logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Checking 'Deducible único' checkbox")
            
            # Locate and click checkbox
            unique_deductible = self.wait.until(EC.element_to_be_clickable((By.ID, ELEMENT_IDS['plan']['unique_deductible'])))
            unique_deductible.click()
            
        except Exception as e:
            raise ElementInteractionError(f"[{product['product']}/{plan['name']}/Age {age}] Failed to check 'Deducible único' checkbox: {str(e)}")
        
    def _set_coverage_options_pleno_integro(self, product, plan, age):
        """Set coverage options for Alfa Medical plans using config"""
        try:
            logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Setting coverage options")
            
            for option_key, option_data in COVERAGE_OPTIONS['alfa_medical'].items():
                checkbox = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, option_data['xpath'])
                ))
                checkbox.click()
                logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Set {option_data['description']}")
                
        except Exception as e:
            raise ElementInteractionError(f"[{product['product']}/{plan['name']}/Age {age}] Failed to set coverage options {str(e)}")
        
    def _set_coverage_options_flex(self, product, plan, age):
        """Set coverage options for Flex plans using config"""
        try:
            logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Setting coverage options")
            
            for option_key, option_data in COVERAGE_OPTIONS['flex'].items():
                checkbox = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, option_data['xpath'])
                ))
                checkbox.click()
                logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Set {option_data['description']}")
                
        except Exception as e:
            raise ElementInteractionError(f"[{product['product']}/{plan['name']}/Age {age}] Failed to set coverage options {str(e)}")
            
        except Exception as e:
            raise ElementInteractionError(f"[{product['product']}/{plan['name']}/Age {age}] Failed to set coverage options: {str(e)}")
    
    def _calculate_and_collect_data(self, product, plan, age):
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
            logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Calculate button clicked.")
            
            # Switch to results tab using dedicated method
            self._switch_to_results_tab(product, plan, age)
                    
            # Collect and return data
            data = self.data_collector.collect_all_data(product, plan, age)

            quote_time = time.time() - start_time
            logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Successfully quoted {plan['name']} plan for age {age} in {quote_time:.2f} seconds")

            logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Data collected: {data}")
            
            return data or {}
            
        except Exception as e:
            logger.error(f"[{product['product']}/{plan['name']}/Age {age}] Failed to calculate and collect data in {time.time() - start_time:.2f} seconds: {str(e)}")
            raise DataCollectionError(f"[{product['product']}/{plan['name']}/Age {age}] Failed to calculate and collect data: {str(e)}")
        
    def _switch_to_results_tab(self, product, plan, age):
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
                logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Successfully switched to 'Resultado' tab")
                
                # Verify we actually switched tabs by checking for a unique element
                self.wait.until(
                    EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_txbSumaAsegurada'))
                )
                
                return  # Success - exit the method
                
            except Exception as e:
                if attempt == tab_retries - 1:
                    # If this was our last attempt, raise the error
                    logger.error(f"[{product['product']}/{plan['name']}/Age {age}] Failed to switch to Results tab after {tab_retries} attempts")
                    raise NavigationError(f"[{product['product']}/{plan['name']}/Age {age}] Could not switch to Results tab: {str(e)}") from e
                
                logger.warning(f"[{product['product']}/{plan['name']}/Age {age}] Failed to switch to Results tab, attempt {attempt + 1} of {tab_retries}: {str(e)}")
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

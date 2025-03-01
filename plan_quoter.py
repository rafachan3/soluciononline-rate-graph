import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException
from config import ELEMENT_IDS, PLAN_CONFIG, RETRY_CONFIG, COVERAGE_OPTIONS
from exceptions import QuoterError, PlanSelectionError, DataCollectionError, NavigationError, ElementInteractionError
from selenium.webdriver.common.keys import Keys 
import time
from data_collector import DataCollector

logger = logging.getLogger(__name__)

class Quoter:
    """
    Manages the process of quoting insurance plans by navigating through the web interface.
    
    This class handles the process of selecting products, plans, and options, then calculating
    and collecting pricing data. It works with different insurance products (Alfa Medical and 
    Alfa Medical Flex) and their respective plans, handling the unique navigation paths and 
    option selections required for each product type.
    """
    def __init__(self, browser_manager):
        self.browser_manager = browser_manager  # Assign the passed instance
        self.wait = browser_manager.wait       # Reuse WebDriverWait from BrowserManager
        self.data_collector = DataCollector(self.wait)  # Initialize DataCollector
        self.data = []                         # Initialize other data attributes if needed
        self.current_age = 0                   # Add age tracker

    def access_product(self, product_identifier, product_name):
        """
        Navigate to a specific insurance product in the web interface.
        
        This is the first step in the quoting process - selecting which insurance product
        to quote (Alfa Medical or Alfa Medical Flex). After selecting the product, this method
        also handles the initial popup that appears when selecting a new plan type.
        
        Args:
            product_identifier: Selenium locator tuple for the product button
            product_name: Human-readable name of the product for logging
        
        Raises:
            TimeoutException: If product elements cannot be found
        """
        start_time = time.time()
        logger.debug(f"[{product_name}] Waiting for product button to become clickable...")
        # This button represents selecting a new quote workflow rather than modifying an existing one
        product_button = self.wait.until(EC.element_to_be_clickable(product_identifier))
        product_button.click()

        try:
            try:
                logger.debug("Waiting for 'btn_ant' button to become clickable...")
                plan_type_button = self.wait.until(EC.element_to_be_clickable((By.ID, 'btn_ant')))
            except ElementNotInteractableException:
                plan_type_button = self.wait.until(EC.element_to_be_clickable((By.ID, 'btn_ant')))
        except TimeoutException:
            logger.error("Timeout: 'btn_ant' button was not found or not clickable.")
            raise

        logger.debug("Handling pop-up...")
        plan_type_button.click()
        # After clicking the new quote button, a confirmation dialog appears
        # that must be accepted to proceed with the quote process
        accept_button = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'btn-success')))
        accept_button.click()
        logger.info(f"[{product_name}] Product access completed in {time.time() - start_time:.2f} seconds")

    def select_plan_from_dropdown(self, dropdown_selector, plan, product):
        """
        Select a specific insurance plan from the dropdown menu.
        
        The insurance system has different plans within each product category.
        This method selects the appropriate plan (e.g., Pleno, Integro, Flex A, Flex B).
        
        Note: Plans with specific values (060001001155 or 060001001219) are skipped
        as they are handled differently in the workflow.
        
        Args:
            dropdown_selector: Selenium locator tuple for the plan dropdown
            plan: Dict containing plan information (name, value)
            product: Dict containing product information
            
        Raises:
            TimeoutException: If plan dropdown cannot be found
        """

        # Skip certain plans as they're handled differently in the workflow
        # (060001001155 = Pleno, 060001001219 = Flex A)
        if plan['value'] == "060001001155" or plan['value'] == "060001001219":
            return
            
        if plan['value'] == "060001001157":
            age = 0
            self._set_validity_date(product, plan, age, date_string="01/05/2024")

        # Create a quick wait for the initial dropdown selection
        quick_wait = WebDriverWait(self.browser_manager.driver, RETRY_CONFIG['short_wait_time'])
        logger.debug(f"[{product['product']}/{plan['name']}] Attempting to locate plan dropdown...")
        
        try:
            # Try the first selector with quick wait
            dropdown_menu = quick_wait.until(EC.presence_of_element_located(dropdown_selector))
        except TimeoutException:
            # If first selector fails, try the alternative immediately
            # This is necessary as the DOM structure can vary between plan types
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

        # Handle any popup that appears after plan selection (common in insurance UIs)
        self.browser_manager.pop_up_handler()
        self.wait.until(EC.invisibility_of_element((By.ID, 'modal')))

    def quote_plan(self, age, plan, product, deductible):
        """
        Execute the full quoting process for a specific plan and age.
        
        This is the main workflow method that orchestrates the entire quoting process:
        1. Select appropriate plan handler based on plan type
        2. Set all required parameters (residence, deductible, coverage options)
        3. Calculate pricing
        4. Collect the resulting pricing data
        
        The method includes retry logic to handle transient errors in the web interface.
        
        Args:
            age: Age of the prospective insured person
            plan: Dict containing plan information
            product: Dict containing product information
            
        Returns:
            Dict containing the collected pricing data or empty dict on failure
            
        Raises:
            QuoterError: If the quoting process fails after all retries
        """
        max_retries = RETRY_CONFIG['max_quote_retries']
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Different plan types require different handling procedures
                if plan['name'] in ["Pleno", "Integro"]:
                    # These are Alfa Medical base plans
                    return self._handle_pleno_integro_plan(product, plan, age, deductible)
                elif plan['name'] in ["Flex A", "Flex B"]:
                    # These are Alfa Medical Flex plans with different options
                    return self._handle_flex_plan(product, plan, age)
                else:
                    raise PlanSelectionError(f"Unknown plan type: {plan['name']}")
            
            except ElementInteractionError as e:
                logger.error(f"[{product['product']}/{plan['name']}/Age {age}] Failed to interact with element: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"[{product['product']}/{plan['name']}/Age {age}] Retrying quote_plan (attempt {retry_count + 1} of {max_retries})")
                    # Refresh the page to start the process over with a clean state
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
            
    def _handle_pleno_integro_plan(self, product, plan, age, deductible, validity_date="01/05/2024"):
        """
        Handle the quoting process specific to Alfa Medical Pleno and Integro plans.
        
        Args:
            product: Dict containing product information
            plan: Dict containing plan information
            age: Age of the prospective insured person
            
        Returns:
            Dict containing the collected pricing data
            
        Raises:
            DataCollectionError: If any part of the process fails
        """
        try:
            if validity_date and plan['name'] == "Pleno":
                self._set_validity_date(product, plan, age, validity_date)

            # Set state of residence - pricing varies by location due to
            # regional differences in healthcare costs
            self._set_residence(product, plan, age)
            
            # Set deductible - this is the amount the customer pays before insurance kicks in
            # Standardized to 40,000 MXN for consistent comparison
            self._set_deductible_amount(product, plan, age, deductible)

            # Set unique deductible option - makes deductible apply per condition
            # rather than per event (typically preferred by customers)
            # self._set_unique_deductible(product, plan, age)

            self._set_coinsurance(product, plan, age)
            
            # Set coverage options - adds CAE (international coverage) and CEDA (accident coverage)
            # These are popular additions that enhance the basic plan
            self._set_coverage_options_pleno_integro(product, plan, age)
            
            # Calculate and collect pricing data based on all selected options
            plan_pricing_data = self._calculate_and_collect_data(product, plan, age)

            # Navigate back to start for next iteration
            self._navigate_back_to_start()
            
            return plan_pricing_data
            
        except Exception as e:
            raise DataCollectionError(f"[{product['product']}/{plan['name']}/Age {age}] Error processing the plan: {str(e)}")

    def _handle_flex_plan(self, product, plan, age, validity_date="01/05/2024"):
        """
        Handle the quoting process specific to Alfa Medical Flex plans.
        
        Flex plans have a simpler configuration process but different coverage options:
        1. Flex-specific coverage options (CAE for international, CRCPA for accident copay reduction)
        
        Args:
            product: Dict containing product information
            plan: Dict containing plan information
            age: Age of the prospective insured person
            
        Returns:
            Dict containing the collected pricing data
            
        Raises:
            DataCollectionError: If any part of the process fails
        """
        try:

            if validity_date:
                self._set_validity_date(product, plan, age, validity_date)

            # Set state of residence
            self._set_residence(product, plan, age)
            
            # Set coverage options - Flex plans have different available options
            # compared to standard Alfa Medical plans
            self._set_coverage_options_flex(product, plan, age)
            
            # Calculate and collect pricing data based on all selected options
            plan_pricing_data = self._calculate_and_collect_data(product, plan, age)

            # Navigate back to start for next iteration
            self._navigate_back_to_start()

            return plan_pricing_data
            
        except Exception as e:
            raise DataCollectionError(f"[{product['product']}/{plan['name']}/Age {age}] Error processing the plan: {str(e)}")
        
    def _set_validity_date(self, product, plan, age, date_string):
        """
        Set the Vigencia (validity) date for the plan.
        
        Args:
            product: Dict containing product information
            plan: Dict containing plan information
            age: Age of the prospective insured person
            date_string: Date string in format DD/MM/YYYY
        """
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Setting validity date to {date_string}, attempt {attempt+1}")
                
                # Wait for any ongoing AJAX calls to finish
                self.browser_manager.driver.execute_script("return window.jQuery && jQuery.active === 0")
                
                # Get a fresh reference to the element each time
                validity_date_input = self.wait.until(EC.presence_of_element_located(
                    (By.ID, ELEMENT_IDS['plan']['validity']) 
                ))
                
                current_value = validity_date_input.get_attribute('value')
                
                # If the date is already correct, we're done
                if current_value == date_string:
                    logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Date already set correctly to {date_string}")
                    return
                
                # Use JavaScript to set the value
                self.browser_manager.driver.execute_script(
                    "arguments[0].value = arguments[1];", 
                    validity_date_input, 
                    date_string
                )
                
                # Then trigger the change event separately
                # This gives us control over when the postback happens
                logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Triggering change event")
                self.browser_manager.driver.execute_script(
                    "arguments[0].dispatchEvent(new Event('change'));", 
                    validity_date_input
                )
                
                # Wait for the page to reload after the postback
                logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Waiting for page to stabilize after date change")
                time.sleep(2)
                
                # Wait for any loading indicators to disappear
                try:
                    WebDriverWait(self.browser_manager.driver, 10).until(
                        EC.invisibility_of_element_located((By.ID, 'loading-overlay'))
                    )
                except:
                    # If there's no loading overlay, just continue
                    pass
                
                # Verify the date was set successfully (using a fresh reference)
                try:
                    new_input = WebDriverWait(self.browser_manager.driver, 5).until(
                        EC.presence_of_element_located((By.ID, ELEMENT_IDS['plan']['validity']))
                    )
                    new_value = new_input.get_attribute('value')
                    if new_value == date_string:
                        logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Date successfully changed to {date_string}")
                        
                        # Handle any validation popups
                        self.browser_manager.pop_up_handler()
                        return  # Success!
                    else:
                        logger.warning(f"[{product['product']}/{plan['name']}/Age {age}] Date not changed. Expected {date_string}, got {new_value}")
                except Exception as verify_error:
                    logger.warning(f"[{product['product']}/{plan['name']}/Age {age}] Could not verify date change: {str(verify_error)}")
                    
            except Exception as e:
                logger.warning(f"[{product['product']}/{plan['name']}/Age {age}] Attempt {attempt+1} failed: {str(e)}")
                
                if attempt == max_attempts - 1:
                    # Only raise on the last attempt
                    logger.error(f"[{product['product']}/{plan['name']}/Age {age}] Failed to set Vigencia date after {max_attempts} attempts: {str(e)}")
                    raise ElementInteractionError(f"Failed to set Vigencia date: {str(e)}")
    
    def _set_residence(self, product, plan, age):
        """
        Set the state of residence for the insurance quote.
        
        Standardized to Veracruz for consistent comparison across all quotes.
        
        Args:
            product: Dict containing product information
            plan: Dict containing plan information
            age: Age of the prospective insured person
            
        Raises:
            ElementInteractionError: If the residence cannot be set
        """
        try:
            # Select the appropriate residence element ID based on plan type
            # Different products have differently structured DOMs
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
            
            # Select Veracruz option - using the index from config for consistency
            residence_option = self.wait.until(
                EC.presence_of_element_located((By.XPATH, option_xpath))
            )
            residence_option.click()
            
            # Handle possible popup after residence selection
            # (e.g., notices about regional coverage limitations)            
            self.browser_manager.pop_up_handler()
            self.wait.until(EC.invisibility_of_element((By.ID, 'modal')))
            
        except Exception as e:
            raise ElementInteractionError(f"[{product['product']}/{plan['name']}] Failed to set residence: {str(e)}")
        
    def _set_deductible_amount(self, product, plan, age, deductible):
        """
        Set the deductible amount to 40,000 MXN.
        
        The deductible is the amount the insured must pay before the insurance coverage begins.
        Standardizing to 40,000 MXN allows for consistent comparison across all quotes.
        This is a common mid-range deductible that balances premium cost with out-of-pocket expense.
        
        Args:
            product: Dict containing product information
            plan: Dict containing plan information
            age: Age of the prospective insured person
            
        Raises:
            ElementInteractionError: If the deductible cannot be set
        """
        try:
            logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Setting deductible to {deductible}")
            
            if deductible == "38,000":
                # Select 38,000 option
                deductible_option = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="ddlDeducible"]/option[5]'))
                )
                deductible_option.click()
            
            if deductible == "43,000":
                # Select 43,000 option
                deductible_option = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="ddlDeducible"]/option[6]'))
                )
                deductible_option.click()           
            
        except Exception as e:
            raise ElementInteractionError(f"[{product['product']}/{plan['name']}/Age {age}] Failed to set deductible: {str(e)}")
        
    def _set_unique_deductible(self, product, plan, age):
        """
        Enable the 'Deducible único' (Unique Deductible) option.
        
        This option provides that the deductible applies per illness/condition rather than per event.
        This is typically preferred by customers as it means they only pay the deductible once
        for an ongoing condition rather than for each hospital visit related to that condition.
        
        Args:
            product: Dict containing product information
            plan: Dict containing plan information
            age: Age of the prospective insured person
            
        Raises:
            ElementInteractionError: If the option cannot be set
        """
        try:
            logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Checking 'Deducible único' checkbox")
            
            # Locate and click checkbox
            unique_deductible = self.wait.until(EC.element_to_be_clickable((By.ID, ELEMENT_IDS['plan']['unique_deductible'])))
            unique_deductible.click()

            self.browser_manager.pop_up_handler()
            
        except Exception as e:
            raise ElementInteractionError(f"[{product['product']}/{plan['name']}/Age {age}] Failed to check 'Deducible único' checkbox: {str(e)}")
        
    def _set_coverage_options_pleno_integro(self, product, plan, age):
        """
        Set additional coverage options for Alfa Medical plans.
        
        For standard Alfa Medical plans, we enable:
        1. CAE (Cobertura de Asistencia en el Extranjero) - Provides coverage for emergency care abroad
        2. CEDA (Eliminación de Deducible por Accidente) - Waives the deductible for accident-related claims
        
        These options are popular additions that enhance the basic coverage and provide
        better value for the customer.
        
        Args:
            product: Dict containing product information
            plan: Dict containing plan information
            age: Age of the prospective insured person
            
        Raises:
            ElementInteractionError: If the options cannot be set
        """
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
    
    def _set_coinsurance(self, product, plan, age):
        try:
            logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Setting 'Coaseguro' to 10%")
            
            # Locate and click checkbox
            coinsurance_option = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="ddlCoaseguro"]/option[2]'))
            )
            coinsurance_option.click()

            self.browser_manager.pop_up_handler()
            
        except Exception as e:
            raise ElementInteractionError(f"[{product['product']}/{plan['name']}/Age {age}] Failed set coinsurance checkbox: {str(e)}")

        
    def _set_coverage_options_flex(self, product, plan, age):
        """
        Set additional coverage options for Alfa Medical Flex plans.
        
        For Flex plans, we enable:
        1. CAE (Cobertura de Asistencia en el Extranjero) - Provides coverage for emergency care abroad
        2. CRCPA (Cobertura Reducción Copago por Accidente) - Reduces copayment for accident-related claims
        
        Flex plans have different available options compared to standard plans,
        reflecting their different structure and target market.
        
        Args:
            product: Dict containing product information
            plan: Dict containing plan information
            age: Age of the prospective insured person
            
        Raises:
            ElementInteractionError: If the options cannot be set
        """
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
        """
        Calculate the plan pricing and collect the resulting data.
        
        This method:
        1. Clicks the Calculate button to run the pricing engine
        2. Switches to the Results tab to view the calculated prices
        3. Collects all relevant pricing data points (premium, fees, taxes, etc.)
        
        Args:
            product: Dict containing product information
            plan: Dict containing plan information
            age: Age of the prospective insured person
            
        Returns:
            Dict containing all collected pricing data
            
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
            plan_pricing_data = self.data_collector.collect_all_data(product, plan, age)

            quote_time = time.time() - start_time
            logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Successfully quoted {plan['name']} plan for age {age} in {quote_time:.2f} seconds")

            logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Data collected: {plan_pricing_data}")
            
            return plan_pricing_data or {}
            
        except Exception as e:
            logger.error(f"[{product['product']}/{plan['name']}/Age {age}] Failed to calculate and collect data in {time.time() - start_time:.2f} seconds: {str(e)}")
            raise DataCollectionError(f"[{product['product']}/{plan['name']}/Age {age}] Failed to calculate and collect data: {str(e)}")
        
    def _switch_to_results_tab(self, product, plan, age):
        """
        Switch to the Results tab with retry logic and popup handling.
        
        This method is crucial because it navigates to where the calculated pricing data
        is displayed. The system requires multiple retries because:
        1. The calculation may take time to complete
        2. Popups may appear blocking the tab
        3. The tab may not be immediately clickable
        
        Args:
            product: Dict containing product information
            plan: Dict containing plan information
            age: Age of the prospective insured person
            
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
        """
        Navigate back to the starting page using the two back buttons.
        
        This method returns to the initial page to prepare for the next quote.
        The system requires clicking two separate back buttons to return to the start:
        1. First back button returns from results to options
        2. Second back button returns from options to the prospect page
        
        Raises:
            NavigationError: If navigation back fails
        """
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                logger.debug(f"Navigation back attempt {attempt + 1}: Waiting for first back button...")
                
                # Wait a moment for any page processing to complete
                time.sleep(1)
                
                # Use a longer wait for the first button
                first_back_button = WebDriverWait(self.browser_manager.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, ELEMENT_IDS['plan']['back_button_1']))
                )
                
                # Use JavaScript to scroll to and click the button for better reliability
                self.browser_manager.driver.execute_script("arguments[0].scrollIntoView(true);", first_back_button)
                self.browser_manager.driver.execute_script("arguments[0].click();", first_back_button)
                
                logger.debug("First back button clicked, waiting for second back button...")
                
                # Wait for any transitions after the first click
                time.sleep(2)
                
                # Now wait for the second button
                second_back_button = WebDriverWait(self.browser_manager.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, ELEMENT_IDS['plan']['back_button_2']))
                )
                
                # Again use JavaScript for more reliable clicking
                self.browser_manager.driver.execute_script("arguments[0].scrollIntoView(true);", second_back_button)
                self.browser_manager.driver.execute_script("arguments[0].click();", second_back_button)
                
                logger.info("Successfully navigated back to start")
                return
                
            except Exception as e:
                logger.warning(f"Navigation back attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < max_attempts - 1:
                    # Try a refresh to get to a clean state before next attempt
                    try:
                        self.browser_manager.driver.refresh()
                        time.sleep(2)
                    except:
                        pass
                else:
                    # On last attempt, raise the error
                    raise NavigationError(f"Failed to navigate back to start after {max_attempts} attempts: {str(e)}")

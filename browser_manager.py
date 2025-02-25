import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException, StaleElementReferenceException
from config import ELEMENT_IDS, BASE_URL, RETRY_CONFIG
from dotenv import load_dotenv
import os
import time

logger = logging.getLogger(__name__)

class BrowserManager:
    """
    Manages browser automation for the insurance quoting process.
    
    This class handles browser initialization, authentication, navigation,
    prospect creation, and UI interaction challenges like popups. It provides
    a reliable foundation for the scraping operation by handling common browser
    automation tasks and error conditions.
    """
    def __init__(self):
        """
        Initialize browser, load environment variables, and navigate to base URL.
        
        Sets up the Chrome browser with appropriate options, loads credentials from
        environment variables, and navigates to the starting URL of the insurance portal.
        """
        load_dotenv()
        
        # Configure Chrome options for automation
        chrome_options = webdriver.ChromeOptions()

        # Keep the browser open after script completion
        chrome_options.add_experimental_option("detach", True)

        # Initialize the browser and navigate to the base URL
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.get(BASE_URL)

        # Load credentials from environment variables
        self.USERNAME = os.getenv('SOLUCIONONLINE_USERNAME')
        self.PASSWORD = os.getenv('SOLUCIONONLINE_PASSWORD')

        self.age = 0    # Initialize age tracker

        # Create wait object for handling element waits throughout the class
        self.wait = WebDriverWait(self.driver, RETRY_CONFIG['wait_time'] )

    def login(self):
        """
        Log in to the insurance portal.
        
        This method handles the authentication process, including checking if already
        logged in, filling credentials, and verifying successful login. It includes
        retry logic to handle transient login failures.
        
        Raises:
            Exception: If login process fails after maximum attempts
        """
        start_time = time.time()
        max_attempts = RETRY_CONFIG['max_login_attempts']
        attempt = RETRY_CONFIG['max_quote_retries']
        
        while attempt < max_attempts:
            try:
                # First check if we're already logged in by looking for the "Nuevo Prospecto" link
                # This prevents unnecessary login attempts if session is still valid
                try:
                    quick_wait = WebDriverWait(self.driver, RETRY_CONFIG['short_wait_time'])
                    quick_wait.until(EC.presence_of_element_located((By.LINK_TEXT, ELEMENT_IDS['login']['new_prospect'])))
                    logger.info("Already logged in successfully!")
                    return
                except TimeoutException:
                    # Not logged in yet, proceed with login process
                    pass
                
                # Wait for the page to be fully loaded
                # This prevents race conditions where the login form isn't ready yet
                self.wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
                
                # Check if login form is present
                try:
                    quick_wait = WebDriverWait(self.driver, RETRY_CONFIG['short_wait_time'])
                    username_field = quick_wait.until(EC.presence_of_element_located((By.ID, ELEMENT_IDS['login']['username'])))
                    password_field = quick_wait.until(EC.presence_of_element_located((By.ID, ELEMENT_IDS['login']['password'])))
                except TimeoutException:
                    # If login form is not present and we're not logged in, something is wrong
                    logger.warning("Neither login form nor logged-in state detected.")
                    attempt += 1
                    time.sleep(1)
                    continue
                
                # Only fill credentials if fields are empty
                # This prevents clearing potentially auto-filled data
                if not username_field.get_attribute('value'):
                    username_field.clear()
                    username_field.send_keys(self.USERNAME)
                
                if not password_field.get_attribute('value'):
                    password_field.clear()
                    password_field.send_keys(self.PASSWORD)
                
                # Wait for successful login
                time.sleep(1)  # Brief pause to allow for captcha verification
                
                # Check for successful login again
                try:
                    quick_wait = WebDriverWait(self.driver, RETRY_CONFIG['short_wait_time'])
                    quick_wait.until(EC.presence_of_element_located((By.LINK_TEXT, ELEMENT_IDS['login']['new_prospect'])))
                    login_time = time.time() - start_time
                    logger.info("Login successful!")
                    logger.info(f"Login completed in {login_time:.2f} seconds after {attempt} attempts")
                    return
                except TimeoutException:
                    # Not logged in yet, continue monitoring
                    attempt += 1
                    continue
                    
            except Exception as e:
                attempt += 1
                logger.warning(f"Attempt {attempt}: Login attempt failed. Error: {str(e)}")
                time.sleep(1)
        
        raise Exception("Login process timed out - please check the application state")

        
    
    def create_initial_prospect(self):
        """
        Create an initial prospect with default information.
        
        In the insurance portal, a "prospect" is a potential customer for whom quotes
        are generated. This method creates a generic prospect with standard values
        that will be used as the basis for all quotes. The age will be set separately
        for each specific quote.
        
        Key steps:
        1. Click "New Prospect" link
        2. Fill first name and last name
        3. Select gender (male)
        
        The age is intentionally left blank here as it will be set during the quoting process.
        """
        # Navigate to new prospect creation screen
        new_prospect = self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, ELEMENT_IDS['login']['new_prospect'])))
        new_prospect.click()

        # Locate and populate required fields
        first_name = self.wait.until(EC.presence_of_element_located((By.NAME, ELEMENT_IDS['prospect']['first_name'])))
        last_name = self.wait.until(EC.presence_of_element_located((By.NAME, ELEMENT_IDS['prospect']['last_name'])))
        male_button = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, ELEMENT_IDS['prospect']['gender_male']))
        )

        # Set standard values for the prospect
        first_name.send_keys('Prospecto')  # Generic first name
        last_name.send_keys('Nuevo')  # Generic last name
        male_button.click()  # Select male gender

        # Note: Age is intentionally not set here as it will be specific to each quote

    def set_age_start_quoting(self, age):
        """
        Set the prospect's age and start the quoting process.
        
        Age is a critical factor in insurance pricing, and this method sets the age
        for the current quote. After setting the age, it clicks the "Start Quoting"
        button to begin the actual quotation process.
        
        Args:
            age (int): The age to set for the prospect
            
        Raises:
            TimeoutException: If age input or quote button cannot be found
        """
        try:
            logger.debug(f"Setting age to {age}...")

            try: 
                # Wait for age input to appear
                age_input = self.wait.until(EC.presence_of_element_located((By.NAME, ELEMENT_IDS['prospect']['age'])))
            
            except StaleElementReferenceException:
                # Handle stale element reference by relocating the element
                # This can happen if the DOM was updated after initial page load
                age_input = self.wait.until(EC.presence_of_element_located((By.NAME, ELEMENT_IDS['prospect']['age'])))
            
            # Clear any existing value and set the new age
            age_input.clear()
            age_input.send_keys(age)

            # Start the quoting process by clicking the "Quote" button
            logger.debug("Attempting to click 'Start Quoting' button...")
            quote_button = self.wait.until(EC.element_to_be_clickable((By.ID, ELEMENT_IDS['prospect']['quote_button'])))
            quote_button.click()
            logger.debug("Quoting process started.")
        except TimeoutException:
            logger.error("Timeout: Unable to locate 'Edad' input or 'cmdCotizarProducto' button.")
            raise

    def pop_up_handler(self):
        """
        Handle modal popups that appear during the quoting process.
        
        This method attempts to detect and dismiss various types of modal popups
        that can appear during navigation. It uses several selector strategies to 
        find and click "Accept" buttons, with fallbacks if the first attempt fails.
        
        This is crucial because popups can block interaction with the underlying page
        and cause test failures if not handled properly.
        
        The method uses short waits to avoid slowing down the process when no popups
        are present, and includes multiple retry strategies for robustness.
        """            
        # Create a shorter wait time for checking button presence
        short_wait = WebDriverWait(self.driver, RETRY_CONFIG['short_wait_time'])
        max_retries = 2  # Try a couple of times with short waits
        
        # Button selectors ordered by specificity - try more specific selectors first
        # Multiple selectors are needed because popups can have different structures
        button_selectors = [
            (By.CSS_SELECTOR, '.btn.btn-success[data-dismiss="modal"]'),
            (By.XPATH, "//button[contains(@class, 'btn-success') and contains(text(), 'Aceptar')]"),
            (By.XPATH, '//*[@id="modal"]/div/div/div[3]/button'),
            (By.CSS_SELECTOR, '#modal button.btn-success')
        ]
        
        for attempt in range(max_retries):
            if attempt > 0:
                # Small delay between retries to allow popup to appear
                time.sleep(1)
                
            try:
                for selector in button_selectors:
                    try:
                        button = short_wait.until(EC.presence_of_element_located(selector))
                        if button.is_displayed():
                            logger.debug(f"Accept button found on attempt {attempt + 1}, attempting to click...")
                            # Ensure element is in view to avoid "element not interactable" errors
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                            
                            # Try multiple click methods
                            try:
                                button.click()
                            except ElementNotInteractableException:
                                # Fallback to JavaScript click if standard click fails
                                self.driver.execute_script("arguments[0].click();", button)
                            
                            # Quick check that the modal is gone
                            short_wait.until(EC.invisibility_of_element((By.ID, 'modal')))
                            return
                    except (TimeoutException, ElementNotInteractableException):
                        continue
                
                if attempt == max_retries - 1:
                    # Only log on final attempt to reduce noise
                    logger.debug("No immediate popup requiring handling detected.")
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    # Only log on final attempt
                    logger.debug(f"No popup handling needed: {str(e)}")
        
        return  # No popup found or handled
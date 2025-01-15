import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException, StaleElementReferenceException
from dotenv import load_dotenv
import os
import time

logger = logging.getLogger(__name__)

class BrowserManager:
    def __init__(self):
        load_dotenv()

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_experimental_option("detach", True)

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.get('https://www.solucionlinemonterrey.mx/CotizadorWebApp/Forms/Firma.aspx')

        self.USERNAME = os.getenv('SOLUCIONONLINE_USERNAME')
        self.PASSWORD = os.getenv('SOLUCIONONLINE_PASSWORD')

        self.age = 0

        self.wait = WebDriverWait(self.driver, 90)

    def login(self):
        max_attempts = 30  # Increased to allow for multiple captcha attempts
        attempt = 0
        login_successful = False
        
        while not login_successful and attempt < max_attempts:
            try:
                # First, wait for the page to be fully loaded after any refresh
                self.wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
                
                # Wait for login fields to be present again (in case of refresh)
                username = self.wait.until(EC.presence_of_element_located((By.ID, 'Login1_UserName')))
                password = self.wait.until(EC.presence_of_element_located((By.ID, 'Login1_Password')))
                
                current_username = username.get_attribute('value')
                current_password = password.get_attribute('value')
                
                # If either field is empty, refill both
                if not current_username or not current_password:
                    logger.info("Login fields empty or page refreshed, refilling credentials...")
                    
                    # Wait a short moment for any page transitions to complete
                    time.sleep(0.5)
                    
                    # Clear and fill username
                    username.clear()
                    username.send_keys(self.USERNAME)
                    
                    # Clear and fill password
                    password.clear()
                    password.send_keys(self.PASSWORD)
                
                # Check if we've successfully logged in
                try:
                    # Using a very short timeout for this check to make it responsive
                    quick_wait = WebDriverWait(self.driver, 1)
                    quick_wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Nuevo Prospecto")))
                    login_successful = True
                    logger.info("Login successful!")
                    return
                except TimeoutException:
                    # Not logged in yet, continue monitoring
                    attempt += 1
                    time.sleep(1)  # Brief pause before next check
                    continue
                    
            except Exception as e:
                attempt += 1
                logger.warning(f"Attempt {attempt}: Handling login page state. {str(e)}")
                time.sleep(1)  # Wait before retrying
                
        if not login_successful:
            raise Exception("Login process timed out - please check the application state")

        
    
    def create_initial_prospect(self):
        new_prospect = self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Nuevo Prospecto")))
        new_prospect.click()
        first_name = self.wait.until(EC.presence_of_element_located((By.NAME, 'Nombre')))
        last_name = self.wait.until(EC.presence_of_element_located((By.NAME, 'Paterno')))
        male_button = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, '//input[@name="Sexo" and @value="1"]'))
        )

        first_name.send_keys('Prospecto')
        last_name.send_keys('Nuevo') 
        male_button.click()

    def set_age_start_quoting(self, age):
        try:
            logger.info(f"Setting age to {age}...")

            try: 
                # Wait for age input to appear
                age_input = self.wait.until(EC.presence_of_element_located((By.NAME, 'Edad')))
            
            except StaleElementReferenceException:
                age_input = self.wait.until(EC.presence_of_element_located((By.NAME, 'Edad')))
            
            age_input.clear()
            age_input.send_keys(age)
            logger.info(f"Successfully set age to {age}.")

            # Wait for the quote button and click it
            logger.info("Attempting to click 'Start Quoting' button...")
            quote_button = self.wait.until(EC.element_to_be_clickable((By.ID, "cmdCotizarProducto")))
            quote_button.click()
            logger.info("Quoting process started.")
        except TimeoutException:
            logger.error("Timeout: Unable to locate 'Edad' input or 'cmdCotizarProducto' button.")
            raise

    def pop_up_handler(self):
            # Create a shorter wait time for checking button presence
            short_wait = WebDriverWait(self.driver, 3)
            max_retries = 2  # Try a couple of times with short waits
            
            # Button selectors ordered by specificity
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
                                logger.info(f"Accept button found on attempt {attempt + 1}, attempting to click...")
                                # Ensure element is in view
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                                
                                # Try multiple click methods
                                try:
                                    button.click()
                                except ElementNotInteractableException:
                                    self.driver.execute_script("arguments[0].click();", button)
                                
                                # Quick check that the modal is gone
                                short_wait.until(EC.invisibility_of_element((By.ID, 'modal')))
                                logger.info("Modal handled successfully.")
                                return
                        except (TimeoutException, ElementNotInteractableException):
                            continue
                    
                    if attempt == max_retries - 1:
                        # Only log on final attempt
                        logger.debug("No immediate popup requiring handling detected.")
                        
                except Exception as e:
                    if attempt == max_retries - 1:
                        # Only log on final attempt
                        logger.debug(f"No popup handling needed: {str(e)}")
            
            return
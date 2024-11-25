from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException
from dotenv import load_dotenv
import os

class BrowserManager:
    def __init__(self):
        load_dotenv()

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_experimental_option("detach", True)

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.get('https://www.solucionlinemonterrey.mx/CotizadorWebApp/Forms/Firma.aspx')

        self.USERNAME = os.getenv('SOLUCIONONLINE_USERNAME')
        self.PASSWORD = os.getenv('SOLUCIONONLINE_PASSWORD')

    def login(self):
        username = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'Login1_UserName')))
        password = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'Login1_Password')))

        while not username.get_attribute('value') and not password.get_attribute('value'):
            username.send_keys(self.USERNAME)
            password.send_keys(self.PASSWORD)


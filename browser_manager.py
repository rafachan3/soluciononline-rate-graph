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

        self.age = 0

        self.wait = WebDriverWait(self.driver, 10)

    def login(self):
        username = self.wait.until(EC.presence_of_element_located((By.ID, 'Login1_UserName')))
        password = self.wait.until(EC.presence_of_element_located((By.ID, 'Login1_Password')))

        while not username.get_attribute('value') and not password.get_attribute('value'):
            username.send_keys(self.USERNAME)
            password.send_keys(self.PASSWORD)
    
    def generate_prospect(self):
        nuevo_prospecto = self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Nuevo Prospecto")))
        nuevo_prospecto.click()
        nombre = self.wait.until(EC.presence_of_element_located((By.NAME, 'Nombre')))
        apellido_paterno = self.wait.until(EC.presence_of_element_located((By.NAME, 'Paterno')))
        masculino_button = self.wait.until(
        EC.element_to_be_clickable((By.XPATH, '//input[@name="Sexo" and @value="1"]'))
    )
        edad= self.wait.until(EC.presence_of_element_located((By.NAME, 'Edad')))
        
        nombre.send_keys('Prospecto')
        apellido_paterno.send_keys('Nuevo')
        masculino_button.click()
        edad.send_keys(self.age)

    def quote(self):
        cotizar_por_producto = self.wait.until(EC.element_to_be_clickable((By.ID, "cmdCotizarProducto")))
        cotizar_por_producto.click()
        
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException
import time

logger = logging.getLogger(__name__)

class Quoter:
    def __init__(self, browser_manager):
        self.browser_manager = browser_manager  # Assign the passed instance
        self.wait = browser_manager.wait       # Reuse WebDriverWait from BrowserManager
        self.data = []                         # Initialize other data attributes if needed

    def access_product(self, product_identifier):
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

    def select_plan_from_dropdown(self, dropdown_selector, plan_value):
        if plan_value == "060001001213" or plan_value == "060001001217":
            pass
        else:
            dropdown_menu = self.wait.until(EC.presence_of_element_located(dropdown_selector))
            dropdown_menu.click()
            plan_option = self.wait.until(
                EC.presence_of_element_located((By.XPATH, f'//option[@value="{plan_value}"]'))
            )
            plan_option.click()

            self.browser_manager.pop_up_handler()

            self.wait.until(EC.invisibility_of_element((By.ID, 'modal')))
            logger.info("Modal no longer visible. Proceeding with the next step.")

    def quote_plan(self, age, plan, product):
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"Quoting plan: {plan['name']} for age {age}")
            
                # Skip setting age for age == 0
                if age != 0 and not (age == 71 and plan['name'] == 'Pleno'):

                    logger.debug("Setting age for quoting...")
                    try:
                        self.browser_manager.set_age_start_quoting(age)
                        logger.debug(f"Age {age} set for quoting.")
                        self.access_product(product['product_identifier'])
                    except Exception as e:
                        logger.error(f"Error setting age or accessing product: {e}")
                        # Try to refresh the page and retry
                        self.browser_manager.driver.refresh()
                        self.wait.until(EC.presence_of_element_located((By.NAME, 'Edad')))
                        retry_count += 1
                        continue

                try:
                    if plan['name'] in ["Pleno", "Integro"]:
                        logger.info(f"Setting plan-specific options for {plan['name']}.")

                        # Set Veracruz as the state of residence
                        logger.info("Selecting state of residence...")
                        residence = self.wait.until(EC.presence_of_element_located((By.ID, 'ddlResidencia')))
                        residence.click()
                        residence_option = self.wait.until(
                            EC.presence_of_element_located((By.XPATH, '//*[@id="ddlResidencia"]/option[30]'))
                        )
                        residence_option.click()
                        logger.info("State of residence selected.")

                        self.browser_manager.pop_up_handler()
                        self.wait.until(EC.invisibility_of_element((By.ID, 'modal')))
                        logger.info("Modal no longer visible. Proceeding with the next step.")

                        # Set "Deducible" to 40,000
                        deductible = self.wait.until(EC.presence_of_element_located((By.ID, 'ddlDeducible')))
                        deductible.click()
                        deductible_option = self.wait.until(
                            EC.presence_of_element_located((By.XPATH, '//*[@id="ddlDeducible"]/option[5]'))
                        )
                        deductible_option.click()
                        logger.info("Deductible set to 40,000.")

                        # Check "Deducible único" checkbox
                        unique_deductible = self.wait.until(EC.element_to_be_clickable((By.ID, 'chbDeducibleUnico')))
                        unique_deductible.click()
                        logger.info("Unique deductible checkbox checked.")

                        self.browser_manager.pop_up_handler()
                        self.wait.until(EC.invisibility_of_element((By.ID, 'modal')))
                        logger.info("Modal no longer visible. Proceeding with the next step.")

                        # Check coverage options "Asistencia en el Extranjero (CAE)" and "Eliminación de Deducible por Accidente (CEDA)"
                        cae = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@name='ctl00$ContentPlaceHolder1$grvCoberturas$ctl03$chkseleccion']")))
                        ceda = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@name='ctl00$ContentPlaceHolder1$grvCoberturas$ctl05$chkseleccion']")))
                        cae.click()
                        ceda.click()
                        logger.info("Coverage options checked.")

                        logger.info("Clicking 'Calculate' button...")
                        # Click "Calcular" button
                        calculate_button = self.wait.until(EC.element_to_be_clickable((By.ID, 'btnCalcular')))
                        calculate_button.click()
                        logger.info("Calculate button clicked.")

                        logger.info("Switching to 'Resultado' tab...")
                        # Switch to "Resultado" tab with retries
                        tab_retries = 3
                        for attempt in range(tab_retries):
                            try:
                                # First make sure any modal is gone
                                self.browser_manager.pop_up_handler()
                                result_tab = self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Resultado")))
                                result_tab.click()
                                logger.info("Switched to 'Resultado' tab.")
                                break
                            except Exception as e:
                                if attempt == tab_retries - 1:
                                    raise
                                logger.warning(f"Failed to switch to Resultado tab, attempt {attempt + 1}: {e}")
                                time.sleep(1)

                        # Collect data
                        logger.info(f"Collecting data for plan: {plan['name']}")
                        data = self.collect_data()
                        logger.info(f"Data collected: {data}")

                        # Navigate back to the previous page
                        first_back_button = self.wait.until(EC.element_to_be_clickable((By.ID, 'ctl00_ContentPlaceHolder1_btnRegresar')))
                        first_back_button.click()
                        second_back_button = self.wait.until(EC.element_to_be_clickable((By.ID, 'RegresarDP')))
                        second_back_button.click()

                        return data or {}
                        
                    elif plan['name'] in ["Flex A", "Flex B"]:
                        logger.info(f"Setting plan-specific options for {plan['name']}.")

                        # Set Veracruz as the state of residence
                        logger.info("Selecting state of residence...")
                        residence = self.wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_ddlResidencia')))
                        residence.click()
                        residence_option = self.wait.until(
                            EC.presence_of_element_located((By.XPATH, '//*[@id="ddlResidencia"]/option[30]'))
                        )
                        residence_option.click()
                        logger.info("State of residence selected.")

                        self.browser_manager.pop_up_handler()
                        self.wait.until(EC.invisibility_of_element((By.ID, 'modal')))
                        logger.info("Modal no longer visible. Proceeding with the next step.")

                        # Check coverage options "Asistencia en el Extranjero (CAE)" and "Cobertura Reducción Copago por Accidente (CRCPA)"
                        cae = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@name='ctl00$ContentPlaceHolder1$grvCoberturas$ctl05$chkseleccion']")))
                        crcpa = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@name='ctl00$ContentPlaceHolder1$grvCoberturas$ctl05$chkseleccion']")))
                        cae.click()
                        crcpa.click()

                        logger.info("Clicking 'Calculate' button...")
                        # Click "Calcular" button
                        calculate_button = self.wait.until(EC.element_to_be_clickable((By.ID, 'btnCalcular')))
                        calculate_button.click()
                        logger.info("Calculate button clicked.")

                        logger.info("Switching to 'Resultado' tab...")
                        # Switch to "Resultado" tab with retries
                        tab_retries = 3
                        for attempt in range(tab_retries):
                            try:
                                # First make sure any modal is gone
                                self.browser_manager.pop_up_handler()
                                result_tab = self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Resultado")))
                                result_tab.click()
                                logger.info("Switched to 'Resultado' tab.")
                                break
                            except Exception as e:
                                if attempt == tab_retries - 1:
                                    raise
                                logger.warning(f"Failed to switch to Resultado tab, attempt {attempt + 1}: {e}")
                                time.sleep(1)

                        # Collect data
                        logger.info(f"Collecting data for plan: {plan['name']}")
                        data = self.collect_data()
                        logger.info(f"Data collected: {data}")

                        # Navigate back to the previous page
                        first_back_button = self.wait.until(EC.element_to_be_clickable((By.ID, 'ctl00_ContentPlaceHolder1_btnRegresar')))
                        first_back_button.click()
                        second_back_button = self.wait.until(EC.element_to_be_clickable((By.ID, 'RegresarDP')))
                        second_back_button.click()

                        return data or {}

                except Exception as e:
                    logger.error(f"Error during plan quoting: {e}")
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.info(f"Retrying quote_plan (attempt {retry_count + 1} of {max_retries})")
                        # Refresh the page and try again
                        self.browser_manager.driver.refresh()
                        continue
                    else:
                        logger.error("Max retries reached, returning empty data")
                        return {}

            except Exception as e:
                logger.error(f"Error during quoting process for age {age} and plan {plan['name']}: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Retrying entire quote_plan process (attempt {retry_count + 1} of {max_retries})")
                    # Refresh the page and try again
                    self.browser_manager.driver.refresh()
                    continue
                else:
                    return {}


    def collect_data(self):
        logger.debug("Collecting data fields...")
        data = {
        'Suma asegurada': self.insured_sum(),
        'Prima básica anual': self.annual_basic_premium(),
        'Prima de beneficios adicionales anual': self.annual_a_benefits_premium(),
        'Derecho de póliza': self.policy_fee(),
        'IVA': self.vat(),
        'Prima neta anual': self.annual_net_premium(),
        'Primer Pago': self.first_payment()
    }
        logger.info("All data fields collected successfully.")
        return data

    # Suma asegurada
    def insured_sum(self):
        insured_sum = self.wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_txbSumaAsegurada')))
        insured_sum_value = insured_sum.get_attribute('value')
        return insured_sum_value
    
    # Prima básica anual
    def annual_basic_premium(self):
        annual_basic_premium = self.wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_txbPrimaBasicaAnual')))
        annual_basic_premium_value = annual_basic_premium.get_attribute('value')
        return annual_basic_premium_value

    # Prima de beneficios adicionales anual
    def annual_a_benefits_premium(self):
        annual_a_benefits_premium = self.wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_txbPrimaBeneficiosA')))
        annual_a_benefits_premium_value = annual_a_benefits_premium.get_attribute('value')
        return annual_a_benefits_premium_value

    # Derecho de póliza
    def policy_fee(self):
        policy_fee = self.wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_txbDerechoDePoliza')))
        policy_fee_value = policy_fee.get_attribute('value')
        return policy_fee_value

    # IVA
    def vat(self):
        vat = self.wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_txbIva')))
        vat_value = vat.get_attribute('value')
        return vat_value

    # Prima neta anual
    def annual_net_premium(self):
        annual_net_premium = self.wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_txbPrimaNetaAnual')))
        annual_net_premium_value = annual_net_premium.get_attribute('value')
        return annual_net_premium_value

    # Primer Pago
    def first_payment(self):
        first_payment = self.wait.until(EC.presence_of_element_located((By.ID, 'ctl00_ContentPlaceHolder1_txbPrimerPago')))
        first_payment_value = first_payment.get_attribute('value')
        return first_payment_value

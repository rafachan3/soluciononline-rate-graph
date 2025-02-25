from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from exceptions import ElementInteractionError
import logging
import time

logger = logging.getLogger(__name__)

class DataCollector:
    """
    Handles collection of insurance plan pricing data from web forms.
    
    This class is responsible for retrieving various pricing components from the 
    insurance quote results page. It extracts key financial data that will be stored
    and analyzed, ensuring consistent data extraction across all products and plans.
    """    
    def __init__(self, wait):
        """
        Initialize the DataCollector with a WebDriverWait instance.
        
        Args:
            wait (WebDriverWait): WebDriverWait instance for handling element waits
        """
        self.wait = wait


    def _get_field_value(self, field_id):
        """
        Get value from a field by its ID.
        
        This is a helper method that safely extracts values from form fields,
        handling potential errors and edge cases in the web interface.
        
        Args:
            field_id (str): The HTML ID of the field to get value from
                
        Returns:
            str: The value of the field
            
        Raises:
            ElementInteractionError: If the field cannot be found or accessed
        """
        try:
            element = self.wait.until(EC.presence_of_element_located((By.ID, field_id)))
            value = element.get_attribute('value')
        
            if value is None:
                raise ElementInteractionError(f"No value found for field {field_id}")
                
            return value
        
        except Exception as e:
            raise ElementInteractionError(f"Failed to get value for field {field_id}: {str(e)}")



    def collect_all_data(self, product, plan, age):
        """
        Collect all pricing data fields from the results page.
        
        This method orchestrates the collection of all individual pricing components
        from the insurance quote results page. These components include:
        - Insured sum (maximum coverage amount)
        - Annual basic premium (core cost of the insurance)
        - Additional benefits premium (cost of added coverage options)
        - Policy fee (administrative charge)
        - VAT (tax amount)
        - Annual net premium (total annual cost including all components)
        - First payment (initial payment amount if paying in installments)
        
        Args:
            product (dict): The product information dictionary
            plan (dict): The plan information dictionary 
            age (int): The age being processed
            
        Returns:
            dict: All collected pricing data fields in a structured dictionary
        """
        start_time = time.time()
        logger.debug(f"[{product['product']}/{plan['name']}/Age {age}] Collecting data fields...")

        pricing_data = {
            'Suma asegurada': self.insured_sum(),
            'Prima básica anual': self.annual_basic_premium(),
            'Prima de beneficios adicionales anual': self.annual_additional_benefits_premium(),
            'Derecho de póliza': self.policy_fee(),
            'IVA': self.vat(),
            'Prima neta anual': self.annual_net_premium(),
            'Primer Pago': self.first_payment()
        }
        collection_time = time.time() - start_time
        logger.info(f"[{product['product']}/{plan['name']}/Age {age}] All data fields collected successfully in {collection_time:.2f} seconds")
        return pricing_data
    
    # Individual field collectors with descriptive method names
    # Each method targets a specific field on the results page

    # Suma asegurada
    def insured_sum(self):
        """
        Get the insured sum (suma asegurada) value.
        
        This is the maximum amount the insurance will pay for covered expenses.
        It represents the total coverage limit of the policy.
        
        Returns:
            str: The insured sum value in MXN
        """
        return self._get_field_value('ctl00_ContentPlaceHolder1_txbSumaAsegurada')
    
    # Prima básica anual
    def annual_basic_premium(self):
        """
        Get the annual basic premium (prima básica anual).
        
        This is the core cost of the insurance coverage before any additional
        benefits, fees, or taxes. It's determined by age, plan type, and coverage amount.
        
        Returns:
            str: The annual basic premium value in MXN
        """
        return self._get_field_value('ctl00_ContentPlaceHolder1_txbPrimaBasicaAnual')

    # Prima de beneficios adicionales anual
    def annual_additional_benefits_premium(self):
        """
        Get the premium for additional benefits (prima de beneficios adicionales).
        
        This value represents the additional cost for any supplementary coverages
        selected, such as international coverage or accident deductible waivers.
        
        Returns:
            str: The annual additional benefits premium in MXN
        """
        return self._get_field_value('ctl00_ContentPlaceHolder1_txbPrimaBeneficiosA')

    # Derecho de póliza
    def policy_fee(self):
        """
        Get the policy fee (derecho de póliza).
        
        This is a fixed administrative fee charged by the insurance company
        for issuing and maintaining the policy, regardless of the premium amount.
        
        Returns:
            str: The policy fee in MXN
        """
        return self._get_field_value('ctl00_ContentPlaceHolder1_txbDerechoDePoliza')

    # IVA
    def vat(self):
        """
        Get the VAT amount (IVA).
        
        This is the value-added tax (currently 16% in Mexico) that applies to 
        insurance premiums and fees. It's a mandatory tax component of the total cost.
        
        Returns:
            str: The VAT amount in MXN
        """
        return self._get_field_value('ctl00_ContentPlaceHolder1_txbIva')

    # Prima neta anual
    def annual_net_premium(self):
        """
        Get the annual net premium (prima neta anual).
        
        This is the total annual cost of the insurance, including basic premium,
        additional benefits premium, policy fee, and taxes.
        
        Returns:
            str: The annual net premium in MXN
        """
        return self._get_field_value('ctl00_ContentPlaceHolder1_txbPrimaNetaAnual')

    # Primer Pago
    def first_payment(self):
        """
        Get the first payment amount (primer pago).
        
        This represents the initial payment due when setting up the policy. It may
        differ from subsequent payments if the premium is paid in installments.
        
        Returns:
            str: The first payment amount in MXN
        """
        return self._get_field_value('ctl00_ContentPlaceHolder1_txbPrimerPago')

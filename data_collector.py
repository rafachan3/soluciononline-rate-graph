from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from exceptions import ElementInteractionError
import logging

logger = logging.getLogger(__name__)

class DataCollector:
    """Handles collection of insurance plan data from web forms"""
    
    def __init__(self, wait):
        self.wait = wait


    def _get_field_value(self, field_id):
        """Get value from a field by its ID.
        
        Args:
            field_id (str): The ID of the field to get value from
                
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



    def collect_all_data(self):
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
    
    # Individual field collectors

    # Suma asegurada
    def insured_sum(self):
        """Get the insured sum (suma asegurada) value
    
        Returns:
            str: The insured sum value
        """
        return self._get_field_value('ctl00_ContentPlaceHolder1_txbSumaAsegurada')
    
    # Prima básica anual
    def annual_basic_premium(self):
        return self._get_field_value('ctl00_ContentPlaceHolder1_txbPrimaBasicaAnual')

    # Prima de beneficios adicionales anual
    def annual_a_benefits_premium(self):
        return self._get_field_value('ctl00_ContentPlaceHolder1_txbPrimaBeneficiosA')

    # Derecho de póliza
    def policy_fee(self):
        return self._get_field_value('ctl00_ContentPlaceHolder1_txbDerechoDePoliza')

    # IVA
    def vat(self):
        return self._get_field_value('ctl00_ContentPlaceHolder1_txbIva')

    # Prima neta anual
    def annual_net_premium(self):
        return self._get_field_value('ctl00_ContentPlaceHolder1_txbPrimaNetaAnual')

    # Primer Pago
    def first_payment(self):
        return self._get_field_value('ctl00_ContentPlaceHolder1_txbPrimerPago')

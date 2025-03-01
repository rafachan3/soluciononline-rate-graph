from selenium.webdriver.common.by import By

# Web Elements
ELEMENT_IDS = {
    'login': {
        'username': 'Login1_UserName',
        'password': 'Login1_Password',
        'new_prospect': 'Nuevo Prospecto'
    },
    'prospect': {
        'first_name': 'Nombre',
        'last_name': 'Paterno',
        'gender_male': '//input[@name="Sexo" and @value="1"]',
        'age': 'Edad',
        'quote_button': 'cmdCotizarProducto'
    },
    'plan': {
        'plan_dropdown': 'ddlPlan',
        'validity': 'ctl00_ContentPlaceHolder1_vigencia',
        'residence_dropdown': {
            'alfa_medical': 'ddlResidencia',
            'flex': 'ctl00_ContentPlaceHolder1_ddlResidencia'
        },
        'deductible_dropdown': 'ddlDeducible',
        'unique_deductible': 'chbDeducibleUnico',
        'coinsurance': 'ddlCoaseguro',
        'calculate_button': 'btnCalcular',
        'result_tab': 'Resultado',
        'back_button_1': 'ctl00_ContentPlaceHolder1_btnRegresar',
        'back_button_2': 'RegresarDP'
    }
}

# URL Configuration
BASE_URL = 'https://www.solucionlinemonterrey.mx/CotizadorWebApp/Forms/Firma.aspx'

# Retry Configuration
RETRY_CONFIG = {
    'max_login_attempts': 30,
    'max_quote_retries': 3,
    'max_tab_retries': 3,
    'wait_time': 90,
    'short_wait_time': 3
}

# Product Configuration
PRODUCTS = [
    {
        'product': 'Alfa Medical',
        'product_identifier': (By.ID, '60'),
        'plans': [
            {'name': 'Pleno', 'value': '060001001155'},
            {'name': 'Integro', 'value': '060001001157'}
        ]
    },
    {
        'product': 'Alfa Medical Flex',
        'product_identifier': (By.ID, '72'),
        'plans': [
            {'name': 'Flex A', 'value': '060001001219'},
            {'name': 'Flex B', 'value': '060001001217'}
        ]
    }
]

# Plan Specific Configuration
PLAN_CONFIG = {
    'alfa_medical_plans': ["Pleno", "Integro"],
    'flex_plans': ["Flex A", "Flex B"],
    'default_state': 'Veracruz',
    'state_option_index': 30,
    'deductible_option_index': 5
}

# Database Configuration
DB_CONFIG = {
    'default_db_name': 'insurance_data.db',
    'default_export_filename': '01-05-2024_Anterior.xlsx'
}

# Age Range Configuration
AGE_RANGE = {
    'min_age': 0,
    'max_age': 75
}

# Plan's Coverage Options Configuration
COVERAGE_OPTIONS = {
    'alfa_medical': {
        'cae': {
            'xpath': "//input[@name='ctl00$ContentPlaceHolder1$grvCoberturas$ctl03$chkseleccion']",
            'description': "Asistencia en el Extranjero (CAE)"
        },
        'ceda': {
            'xpath': "//input[@name='ctl00$ContentPlaceHolder1$grvCoberturas$ctl05$chkseleccion']",
            'description': "Eliminación de Deducible por Accidente (CEDA)"
        }
    },
    'flex': {
        'cae': {
            'xpath': '//*[@id="ctl00_ContentPlaceHolder1_grvCoberturas_ctl03_chkseleccion"]',
            'description': "Asistencia en el Extranjero (CAE)"
        },
        'crcpa': {
            'xpath': '//*[@id="ctl00_ContentPlaceHolder1_grvCoberturas_ctl05_chkseleccion"]',
            'description': "Cobertura Reducción Copago por Accidente (CRCPA)"
        }
    }
}
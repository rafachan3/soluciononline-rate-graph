import sqlite3
from datetime import datetime
import pandas as pd
from config import DB_CONFIG
from openpyxl.comments import Comment
import logging
import time

logger = logging.getLogger(__name__)

class DatabaseHandler:
    def __init__(self, db_name='insurance_data.db'):
        self.db_name = db_name
        self.create_tables()

    def create_tables(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Create a table to store plan data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plan_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_name TEXT,
                age INTEGER,
                deductible TEXT,
                suma_asegurada TEXT,
                prima_basica_anual TEXT,
                prima_beneficios_adicionales TEXT,
                derecho_poliza TEXT,
                iva TEXT,
                prima_neta_anual TEXT,
                primer_pago TEXT,
                fetch_date DATETIME
            )
        ''')

        conn.commit()
        conn.close()

    def insert_plan_data(self, plan_name, age, pricing_data, deductible=None):
        """
        Insert new plan pricing data into the database.
        
        This method stores a complete set of pricing data for a specific plan and age.
        It includes all the pricing components, deductible amount, and a timestamp 
        for when the data was collected.
        
        Args:
            plan_name (str): Name of the insurance plan
            age (int): Age of the prospective insured
            pricing_data (dict): Dictionary containing all pricing components
            deductible (str, optional): Deductible amount, if applicable
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Insert the data along with current timestamp and deductible
        cursor.execute('''
            INSERT INTO plan_data (
                plan_name, age, deductible, suma_asegurada, prima_basica_anual,
                prima_beneficios_adicionales, derecho_poliza, iva,
                prima_neta_anual, primer_pago, fetch_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            plan_name,
            age,
            deductible,
            pricing_data.get('Suma asegurada', ''),
            pricing_data.get('Prima básica anual', ''),
            pricing_data.get('Prima de beneficios adicionales anual', ''),
            pricing_data.get('Derecho de póliza', ''),
            pricing_data.get('IVA', ''),
            pricing_data.get('Prima neta anual', ''),
            pricing_data.get('Primer Pago', ''),
            datetime.now()
        ))

        conn.commit()
        conn.close()

    def get_latest_data(self, plan_name=None, deductible=None):
        """
        Retrieve the most recent data for a specific plan or all plans.
        
        Args:
            plan_name (str, optional): Name of the plan to retrieve data for.
            deductible (str, optional): Specific deductible amount to filter by.
        
        Returns:
            list: List of tuples containing the requested data rows
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        if plan_name and deductible:
            # Get data for a specific plan and deductible
            cursor.execute('''
                SELECT * FROM plan_data 
                WHERE plan_name = ? AND deductible = ?
                ORDER BY fetch_date DESC
            ''', (plan_name, deductible))
        elif plan_name:
            # Get data for a specific plan (any deductible)
            cursor.execute('''
                SELECT * FROM plan_data 
                WHERE plan_name = ? 
                ORDER BY fetch_date DESC
            ''', (plan_name,))
        else:
            # Get all data
            cursor.execute('SELECT * FROM plan_data ORDER BY fetch_date DESC')

        data = cursor.fetchall()
        conn.close()
        return data

    def export_to_excel(self, filename=DB_CONFIG['default_export_filename']):
        """
        Export all stored data to an Excel file for analysis.
        
        This method exports the most recent data for each plan+deductible combination
        to a separate sheet in an Excel workbook. This format facilitates easy analysis
        and comparison across different plans, deductibles, and ages.
        
        Args:
            filename (str, optional): Name of the Excel file to create.
                                    Defaults to the value in DB_CONFIG.
        
        Returns:
            str: The name of the created Excel file
        """
        start_time = time.time()
        conn = sqlite3.connect(self.db_name)
        
        # Get unique plan+deductible combinations
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT plan_name, deductible FROM plan_data')
        plan_combinations = cursor.fetchall()
        
        # Create Excel writer
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            for plan_name, deductible in plan_combinations:
                # Generate a sheet name that includes both plan and deductible (if available)
                if deductible:
                    # Remove the thousand separator and just keep the number
                    clean_deductible = deductible.replace(',', '')
                    sheet_name = f"{plan_name.replace(' ', '_')}_{clean_deductible}"
                else:
                    sheet_name = plan_name.replace(' ', '_')
                
                # Ensure sheet name is valid (Excel has a 31 character limit)
                if len(sheet_name) > 31:
                    sheet_name = sheet_name[:31]
                
                # Get latest data for this plan+deductible combination
                query = f'''
                    SELECT age, suma_asegurada, prima_basica_anual,
                           prima_beneficios_adicionales, derecho_poliza,
                           iva, prima_neta_anual, primer_pago
                    FROM plan_data
                    WHERE plan_name = ? AND (deductible = ? OR (deductible IS NULL AND ? IS NULL))
                    ORDER BY fetch_date DESC
                '''
                df = pd.read_sql_query(query, conn, params=(plan_name, deductible, deductible))
                
                # Write to Excel
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Add a note about the deductible in cell A1
                if deductible:
                    worksheet = writer.sheets[sheet_name]
                    comment = Comment(f"Deducible Aplicado: {deductible}", "System")
                    worksheet.cell(row=1, column=1).comment = comment
        
        conn.close()
        export_time = time.time() - start_time
        logger.info(f"Excel export completed in {export_time:.2f} seconds to {filename}")
        return filename
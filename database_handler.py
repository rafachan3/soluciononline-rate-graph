import sqlite3
from datetime import datetime
import pandas as pd
from config import DB_CONFIG
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

    def insert_plan_data(self, plan_name, age, pricing_data):
        """
        Insert new plan pricing data into the database.
        
        This method stores a complete set of pricing data for a specific plan and age.
        It includes all the pricing components and a timestamp for when the data was collected.
        
        Args:
            plan_name (str): Name of the insurance plan
            age (int): Age of the prospective insured
            pricing_data (dict): Dictionary containing all pricing components
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Insert the data along with current timestamp
        cursor.execute('''
            INSERT INTO plan_data (
                plan_name, age, suma_asegurada, prima_basica_anual,
                prima_beneficios_adicionales, derecho_poliza, iva,
                prima_neta_anual, primer_pago, fetch_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            plan_name,
            age,
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

    def get_latest_data(self, plan_name=None):
        """
        Retrieve the most recent data for a specific plan or all plans.
        
        This method allows querying the latest pricing data, either for a 
        specific plan or across all plans, sorted by collection date.
        
        Args:
            plan_name (str, optional): Name of the plan to retrieve data for.
                                      If None, retrieves data for all plans.
        
        Returns:
            list: List of tuples containing the requested data rows
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        if plan_name:
            # Get data for a specific plan
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
        
        This method exports the most recent data for each plan to a separate
        sheet in an Excel workbook. This format facilitates easy analysis and
        comparison across different plans and ages.
        
        Args:
            filename (str, optional): Name of the Excel file to create.
                                    Defaults to the value in DB_CONFIG.
        
        Returns:
            str: The name of the created Excel file
        """
        start_time = time.time()
        conn = sqlite3.connect(self.db_name)
        
        # Get unique plan names
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT plan_name FROM plan_data')
        plan_names = [row[0] for row in cursor.fetchall()]
        
        # Create Excel writer
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            for plan_name in plan_names:
                # Get latest data for each plan
                query = f'''
                    SELECT age, suma_asegurada, prima_basica_anual,
                           prima_beneficios_adicionales, derecho_poliza,
                           iva, prima_neta_anual, primer_pago
                    FROM plan_data
                    WHERE plan_name = ?
                    ORDER BY fetch_date DESC
                '''
                df = pd.read_sql_query(query, conn, params=(plan_name,))
                
                # Write to Excel
                sheet_name = plan_name.replace(' ', '_')
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        conn.close()
        export_time = time.time() - start_time
        logger.info(f"Excel export completed in {export_time:.2f} seconds to {filename}")
        return filename
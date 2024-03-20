import json
import requests
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from datetime import datetime, timedelta

# DAG Configuration
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 11, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'catchup': False
}

dag = DAG(
    'download_aircraft_fuel_consumption',
    default_args=default_args,
    description='A DAG to download aircraft type fuel consumption rates',
    schedule_interval='@monthly',  # Adjust as necessary
    max_active_runs=1
)

S3_CONN_ID = 'my_s3_conn_id'  # Replace with your Airflow S3 connection id
S3_BUCKET = 'bdi-aircraft-kh'
FUEL_CONSUMPTION_URL = "https://example.com/fuel_consumption_rates.json"  # Replace with the actual URL


def download_and_upload_fuel_rates(**kwargs):
    """Download fuel consumption rates and upload them to AWS S3"""
    s3_hook = S3Hook(aws_conn_id=S3_CONN_ID)
    response = requests.get(FUEL_CONSUMPTION_URL)
    response.raise_for_status()

    target_file_name = f"fuel_consumption_rates_{datetime.now().strftime('%Y-%m')}.json"
    s3_hook.load_string(
        string_data=response.text,
        bucket_name=S3_BUCKET,
        key=f"fuel_consumption/{target_file_name}",
        replace=True
    )


download_upload_operator = PythonOperator(
    task_id='download_and_upload_fuel_rates',
    python_callable=download_and_upload_fuel_rates,
    dag=dag,
)

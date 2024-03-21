import json
import requests
import boto3
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
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
    schedule_interval='@monthly',
    max_active_runs=1
)

# S3_CONN_ID = 'aws_default'
S3_BUCKET = 'bdi-aircraft-kh'
FUEL_CONSUMPTION_URL = "https://raw.githubusercontent.com/martsec/flight_co2_analysis/main/data/aircraft_type_fuel_consumption_rates.json"


def download_and_upload_fuel_rates(**kwargs):
    """Download fuel consumption rates and upload them to AWS S3"""
    s3_client = boto3.client('s3')
    response = requests.get(FUEL_CONSUMPTION_URL)
    response.raise_for_status()

    target_file_name = f"fuel_consumption_rates_{datetime.now().strftime('%Y-%m')}.json"
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=f"fuel_consumption/{target_file_name}",
        Body=response.text.encode(),
        ContentType='application/json'
    )


download_upload_operator = PythonOperator(
    task_id='download_and_upload_fuel_rates',
    python_callable=download_and_upload_fuel_rates,
    dag=dag,
)

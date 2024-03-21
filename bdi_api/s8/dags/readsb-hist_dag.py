import json
import requests
import boto3
from bs4 import BeautifulSoup
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
from pathlib import Path

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
    'readsb_hist_data',
    default_args=default_args,
    description='A DAG to download readsb-hist data for the first day of each month',
    schedule_interval='@monthly',  # Cron expression could also be '0 0 1 * *'
    max_active_runs=1
)

# S3_CONN_ID = 'aws_default'
S3_BUCKET = 'bdi-aircraft-kh'
BASE_URL = "https://samples.adsbexchange.com/readsb-hist/2023/11/01/"


def download_task(execution_date, **kwargs):
    """Download files from a URL and upload them to AWS S3 using boto3"""
    s3_client = boto3.client('s3')
    s3_prefix_path = f"raw/day={execution_date.strftime('%Y%m%d')}/"

    response = requests.get(BASE_URL)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    file_list = [a['href'] for a in soup.find_all('a') if a['href'].endswith('Z.json.gz')]

    for file_name in file_list[:100]:
        file_url = f"{BASE_URL}{file_name}"
        response = requests.get(file_url)
        response.raise_for_status()

        s3_client.put_object(Bucket=S3_BUCKET, Key=f"{s3_prefix_path}{file_name}", Body=response.content)


def prepare_task(execution_date, **kwargs):
    """Download data from AWS S3 using boto3, process it, and re-upload it to S3"""
    s3_client = boto3.client('s3')
    s3_prefix_path = f"raw/day={execution_date.strftime('%Y%m%d')}/"
    prepared_prefix = f"prepared/day={execution_date.strftime('%Y%m%d')}/"

    response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=s3_prefix_path)
    objects = [obj['Key'] for obj in response.get('Contents', [])]

    for obj_key in objects:
        file_content = s3_client.get_object(Bucket=S3_BUCKET, Key=obj_key)['Body'].read()
        data = json.loads(file_content)
        aircraft_data = data.get("aircraft", [])
        timestamp = data.get("now", "")

        extracted_data = [{
            "icao": aircraft.get("hex", ""),
            "registration": aircraft.get("r", ""),
            "type": aircraft.get("t", ""),
            "flight_name": aircraft.get("flight", "").strip(),
            "timestamp": timestamp
        } for aircraft in aircraft_data]

        processed_data_string = json.dumps(extracted_data, indent=4)
        s3_client.put_object(Bucket=S3_BUCKET, Key=f"{prepared_prefix}{Path(obj_key).stem}.processed.json", Body=processed_data_string.encode())


download_operator = PythonOperator(
    task_id='download',
    python_callable=download_task,
    provide_context=True,
    op_kwargs={'execution_date': '{{ ds }}'},
    dag=dag,
)

prepare_operator = PythonOperator(
    task_id='prepare',
    python_callable=prepare_task,
    provide_context=True,
    op_kwargs={'execution_date': '{{ ds }}'},
    dag=dag,
)

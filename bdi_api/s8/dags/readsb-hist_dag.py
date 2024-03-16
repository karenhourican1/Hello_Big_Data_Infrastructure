import json
import requests
from bs4 import BeautifulSoup
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.hooks.S3_hook import S3Hook
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

# Replace 'my_s3_conn_id' with your Airflow S3 connection id
S3_CONN_ID = 'my_s3_conn_id'
S3_BUCKET = 'your_s3_bucket_name'
BASE_URL = "https://samples.adsbexchange.com/readsb-hist/2023/11/01/"


def download_task(execution_date, **kwargs):
    """Download files from a URL and upload them to AWS S3"""
    s3_hook = S3Hook(aws_conn_id=S3_CONN_ID)
    s3_prefix_path = f"raw/day={execution_date.strftime('%Y%m%d')}/"

    response = requests.get(BASE_URL)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    file_list = [a['href'] for a in soup.find_all('a') if a['href'].endswith('Z.json.gz')]

    for file_name in file_list[:100]:
        file_url = f"{BASE_URL}{file_name}"
        response = requests.get(file_url)
        response.raise_for_status()

        s3_hook.load_bytes(
            bytes_data=response.content,
            bucket_name=S3_BUCKET,
            key=f"{s3_prefix_path}{file_name}",
            replace=True
        )


def prepare_task(execution_date, **kwargs):
    """Download data from AWS S3, process it, and re-upload it to S3"""
    s3_hook = S3Hook(aws_conn_id=S3_CONN_ID)
    s3_prefix_path = f"raw/day={execution_date.strftime('%Y%m%d')}/"
    prepared_prefix = f"prepared/day={execution_date.strftime('%Y%m%d')}/"

    objects = s3_hook.list_keys(bucket_name=S3_BUCKET, prefix=s3_prefix_path)

    for obj_key in objects:
        # Download file from S3
        file_content = s3_hook.read_key(obj_key, bucket_name=S3_BUCKET)
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
        s3_hook.load_string(
            string_data=processed_data_string,
            bucket_name=S3_BUCKET,
            key=f"{prepared_prefix}{Path(obj_key).stem}.processed.json",
            replace=True
        )


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


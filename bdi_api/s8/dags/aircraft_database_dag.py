from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from datetime import datetime, timedelta
import requests

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
    'download_aircraft_database',
    default_args=default_args,
    description='A DAG to download the entire aircraft database',
    schedule_interval='@monthly',
    max_active_runs=1
)

S3_CONN_ID = 'aws_default'
S3_BUCKET = 'bdi-aircraft-kh'
AIRCRAFT_DATABASE_URL = "URL_TO_THE_AIRCRAFT_DATABASE"


def download_aircraft_database(**kwargs):
    """
    Download the aircraft database and upload it to AWS S3.
    Since this is a full refresh, we'll replace the existing file.
    """
    s3_hook = S3Hook(aws_conn_id=S3_CONN_ID)

    # Make the HTTP request to the aircraft database URL
    response = requests.get(AIRCRAFT_DATABASE_URL)
    response.raise_for_status()  # This will raise an exception if the request was not successful

    # Construct the target S3 key
    target_file_name = f"aircraft_database_{datetime.now().strftime('%Y-%m')}.json"

    # Upload the response content to S3, replacing the file if it already exists
    s3_hook.load_string(
        string_data=response.text,
        bucket_name=S3_BUCKET,
        key=f"aircraft_database/{target_file_name}",
        replace=True
    )


download_database_operator = PythonOperator(
    task_id='download_aircraft_database',
    python_callable=download_aircraft_database,
    dag=dag,
)


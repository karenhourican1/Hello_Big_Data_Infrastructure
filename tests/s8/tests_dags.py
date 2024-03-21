from datetime import datetime
from airflow.models import DagBag, TaskInstance
from airflow.operators.python_operator import PythonOperator
import pytest

# Load the DAGs from the specified folder
dag_bag = DagBag(dag_folder='"C:\Users\karen\OneDrive - Barcelona Technology School\Hello Big Data\big-data-infrastructure-exercises-main\bdi_api\s8\dags"', include_examples=False)


def test_dagbag_import():
    assert dag_bag.import_errors == {}  # No import errors
    assert len(dag_bag.dags) > 0  # There's at least one DAG


def test_readsb_hist_data_dag():
    dag_id = 'readsb_hist_data'
    dag = dag_bag.get_dag(dag_id)
    assert dag is not None
    tasks = dag.tasks
    task_ids = list(map(lambda task: task.task_id, tasks))
    assert task_ids == ['download', 'prepare']

    download_task = dag.get_task('download')
    prepare_task = dag.get_task('prepare')

    # Test task dependencies
    downstream_task_ids = list(map(lambda task: task.task_id, download_task.downstream_list))
    assert 'prepare' in downstream_task_ids
    assert len(download_task.downstream_list) == 1


def test_download_aircraft_fuel_consumption_dag():
    dag_id = 'download_aircraft_fuel_consumption'
    dag = dag_bag.get_dag(dag_id)
    assert dag is not None

    tasks = dag.tasks
    task_ids = list(map(lambda task: task.task_id, tasks))
    assert task_ids == ['download_and_upload_fuel_rates']


def test_download_aircraft_database_dag():
    dag_id = 'download_aircraft_database'
    dag = dag_bag.get_dag(dag_id)
    assert dag is not None

    tasks = dag.tasks
    task_ids = list(map(lambda task: task.task_id, tasks))
    assert task_ids == ['download_aircraft_database']


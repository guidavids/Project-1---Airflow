from airflow.sdk import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from datetime import timedelta, time
import requests, pandas as pd, psycopg2, os, csv

@dag
def country_processing():

    # Optional drop
    drop_table = SQLExecuteQueryOperator (
        conn_id = "postgres",
        task_id = "drop_table",
        sql = """
        DROP TABLE IF EXISTS countries
        """
    )

    # Create the table with the necessary fields
    create_table = SQLExecuteQueryOperator (
        conn_id = "postgres",
        task_id = "create_table",
        sql = """
        CREATE TABLE IF NOT EXISTS countries (
            country_id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            population INT,
            currency VARCHAR(100),
            gini_score FLOAT
        )
        """
    )

    # Extract data from API
    @task
    def extract_country_data():
        response = requests.get("https://restcountries.com/v3.1/all?fields=name,population,currencies,independent,gini")

        if response.status_code == 200:
            return response.json()

        return None

    # Transform the data to get what we want
    @task
    def transform_country_data(country_data):
        transformed_list = []

        for country in country_data:
            currency_acronym = list(country["currencies"].keys())[0] if country["currencies"].keys() else None
            gini_year = list(country["gini"].keys())[0] if country["gini"].keys() else None

            if country.get("independent"):

                transformed = {
                    "name": country["name"]["common"],
                    "population": country["population"],
                    "currency": country["currencies"][currency_acronym]["name"],
                    "gini_score": country["gini"][gini_year] if gini_year else None
                }
                transformed_list.append(transformed)

        print(len(transformed_list))
        return transformed_list

    # Load the data into a csv file
    @task
    def load_into_csv(country_info):

        with open("/tmp/transformed_country_info.csv", "w", newline = "") as file:
            writer = csv.DictWriter(file, fieldnames = country_info[0].keys())
            writer.writeheader()
            writer.writerows(country_info)

    # Store the country information in Postgres
    @task
    def store_information():
        hook = PostgresHook(postgres_conn_id = "postgres")
        hook.copy_expert(
            sql = "COPY countries(name, currency, gini_score, population) FROM STDIN WITH CSV HEADER",
            filename = "/tmp/transformed_country_info.csv"
        )

    # Set relationships and dependencies below
    country_data = extract_country_data()
    transformed = transform_country_data(country_data)

    drop_table >> create_table >> country_data
    transformed >> load_into_csv(transformed) >> store_information()

country_processing()
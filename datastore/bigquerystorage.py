import os
import string
from datetime import datetime
from dataclasses import dataclass
from typing import List
from google.cloud import bigquery
from dto.parkinglot import ParkingLot, TimeParkingAvailability


@dataclass
class BigQueryStorage():
    client: bigquery.Client = None

    def __post_init__(self):
        self.client = bigquery.Client()

    def get_parking_lot_data(self) -> List[ParkingLot]:

        table_name = self.__get_table_id('parking_lot')
        query = f"""
            SELECT *
            FROM `{table_name}`
        """
        query_job = self.client.query(query)

        parking_lot = []
        for row in query_job:
            parking_lot.append(
                ParkingLot(
                    official_id=row.official_id,
                    name=row.name,
                    description=row.description,
                    county=row.county,
                    district=row.district,
                    address=row.address,
                    total_parking_spaces=row.total_parking_spaces,
                    total_motorcycle_spaces=row.total_motorcycle_spaces,
                    total_charging_stations=row.total_charging_stations,
                )
            )
        return parking_lot

    def get_parkig_time_data(self, official_id, county) -> List[TimeParkingAvailability]:
        print('get time data')
        table_name = self.__get_table_id('time_parking_availability')
        query = f"""
            SELECT *
            FROM `{table_name}`
            WHERE official_id = @official_id
            AND county = @county
            order by time desc
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "official_id", "STRING", official_id),
                bigquery.ScalarQueryParameter("county", "STRING", county),
            ]
        )

        query_job = self.client.query(query, job_config)
        data = []
        for row in query_job:
            data.append(
                TimeParkingAvailability(
                    time=row.time,
                    remaining_parking_spaces=row.remaining_parking_spaces,
                    remaining_motorcycle_spaces=row.remaining_motorcycle_spaces,
                    remaining_charging_stations=row.remaining_charging_stations
                )
            )
        return data

    def __get_table_id(self, table_name: string) -> string:
        dataset_id = os.getenv("BIGQUERY_ID", default="")
        return f"{dataset_id}.{table_name}"

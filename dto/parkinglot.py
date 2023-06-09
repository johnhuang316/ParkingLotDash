from dataclasses import dataclass
import datetime


@dataclass
class ParkingLot():
    official_id: str
    name: str
    description: str = ""
    county: str = ""
    district: str = ""
    address: str = ""
    total_parking_spaces: int = -9
    total_motorcycle_spaces: int = -9
    total_charging_stations: int = -9
    
@dataclass
class TimeParkingAvailability():
    time: datetime
    remaining_parking_spaces: int = -9
    remaining_motorcycle_spaces: int = -9
    remaining_charging_stations: int = -9

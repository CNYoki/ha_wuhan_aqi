import logging
import requests
import urllib.parse
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from datetime import timedelta

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensor platform."""
    stations = config.get("stations", [])
    coordinator = await get_data_coordinator(hass, stations)
    await coordinator.async_refresh()  # Manually refresh the coordinator

    async_add_entities([AirQualitySensor(coordinator), PrimaryPollutantSensor(coordinator)], True)

class AirQualitySensor(CoordinatorEntity, SensorEntity):
    """Representation of an Air Quality sensor."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Wuhan Air Quality"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("aqi_value")

    @property
    def extra_state_attributes(self):
        """Return other details about the air quality."""
        return {
            "aqi_level": self.coordinator.data.get("aqi_level"),
            "state_class": "measurement",
            **self.coordinator.data
        }


class PrimaryPollutantSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Primary Pollutant sensor."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Wuhan Primary Pollutant"

    @property
    def state(self):
        """Return the state of the primary pollutant."""
        primary_pollutant = self.get_primary_pollutant()
        pollutant_name = {"co": "CO", "n2": "NO2", "o3": "O3", "p1": "PM10", "p2": "PM2.5", "s2": "SO2"}
        return pollutant_name.get(primary_pollutant["pollutant_symbol"], "null")

    @property
    def extra_state_attributes(self):
        """Return other details about the primary pollutant."""
        primary_pollutant = self.get_primary_pollutant()
        return {
            "pollutant_symbol": primary_pollutant["pollutant_symbol"],
            "pollutant_unit": primary_pollutant["pollutant_unit"],
            **self.coordinator.data
        }

    def get_primary_pollutant(self):
        """Determine the primary pollutant and its unit."""
        aqi_data = self.coordinator.data
        aqi_calculator = AirQualityIndexCalculator(
            pm25=aqi_data.get("pm25"),
            no2=aqi_data.get("no2"),
            so2=aqi_data.get("so2"),
            pm10=aqi_data.get("pm10"),
            o3=aqi_data.get("o3"),
            co=aqi_data.get("co")
        )

        pollutants = {
            "co": aqi_calculator.calculate_aqi_co(),
            "n2": aqi_calculator.calculate_aqi_no2(),
            "o3": aqi_calculator.calculate_aqi_o3(),
            "p1": aqi_calculator.calculate_aqi_pm10(),
            "p2": aqi_calculator.calculate_aqi_pm25(),
            "s2": aqi_calculator.calculate_aqi_so2()
        }

        primary_pollutant = max(pollutants, key=pollutants.get)
        pollutant_unit = "mg/m³" if primary_pollutant in ["co"] else "µg/m³"

        return {
            "pollutant_symbol": primary_pollutant,
            "pollutant_unit": pollutant_unit
        }

async def get_data_coordinator(hass, stations):
    """Get the data update coordinator."""
    async def async_update_data():
        # Fetch data for all stations
        data = await hass.async_add_executor_job(fetch_data, stations)
        if data is None:
            raise UpdateFailed("Failed to update air quality data")
        return data

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="air_quality_data",
        update_method=async_update_data,
        update_interval=timedelta(minutes=10),
    )
    await coordinator.async_refresh()  # Manually refresh the coordinator

    return coordinator


def fetch_data(stations):
    """Fetch data from an external API for all stations and calculate the average AQI."""
    all_data = {"aqi_values": [], "aqi_levels": [], "pollutants": {}}
    station_name = ""
    for station in stations:
        aqi_data = get_iaqi_data_wuhan(station)
        aqi = get_aqi_level(station)
        all_data["aqi_values"].append(aqi)
        # all_data["aqi_levels"].append(get_aqi_level_description(aqi))
        station_name += station + ", "

        # Collect pollutant data
        for pollutant in ["pm25", "no2", "so2", "pm10", "o3", "co"]:
            if pollutant not in all_data["pollutants"]:
                all_data["pollutants"][pollutant] = []
            all_data["pollutants"][pollutant].append(aqi_data.get(pollutant))

    avg_aqi = int(sum(all_data["aqi_values"]) / len(all_data["aqi_values"]))
    avg_aqi_level = get_aqi_level_description(avg_aqi)

    # Calculate average pollutant values and round them
    avg_pollutants = {pollutant: round(sum(values) / len(values), 3) if sum(values) % len(values) != 0 else int(sum(values) / len(values)) for pollutant, values in all_data["pollutants"].items()}

    return {
        "aqi_value": avg_aqi,
        "aqi_level": avg_aqi_level,
        "aqi_source_station": station_name[:-2],
        **avg_pollutants
    }


def get_aqi_level_description(aqi):
    """Get the AQI level description based on the AQI value."""
    if aqi <= 50:
        return "Good"
    elif 51 <= aqi <= 100:
        return "Moderate"
    elif 101 <= aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    elif 151 <= aqi <= 200:
        return "Unhealthy"
    elif 201 <= aqi <= 300:
        return "Very Unhealthy"
    else:
        return "Hazardous"


class AirQualityIndexCalculator:
    def __init__(self, pm25=0, no2=0, so2=0, pm10=0, o3=0, co=0, o3_8=0):
        self.pm25 = pm25
        self.no2 = no2
        self.so2 = so2
        self.pm10 = pm10
        self.o3 = o3
        self.o3_8 = o3_8
        self.co = co

    def calculate_aqi_pm25(self):
        # todo: 应当使用24小时平均值，但是这里使用1小时平均值
        pm25 = self.pm25  # µg/m³
        if pm25 <= 9.0:
            return round((50 / 9.0) * pm25)
        elif 9.0 < pm25 <= 35.4:
            return round(((49 / (35.4 - 9.0)) * (pm25 - 9.1)) + 51)
        elif 35.4 < pm25 <= 55.4:
            return round(((49 / (55.4 - 35.4)) * (pm25 - 35.5)) + 101)
        elif 55.4 < pm25 <= 125.4:
            return round(((49 / (125.4 - 55.4)) * (pm25 - 55.5)) + 151)
        elif 125.4 < pm25 <= 225.4:
            return round(((99 / (225.4 - 125.4)) * (pm25 - 125.5)) + 201)
        elif 225.4 < pm25 <= 325.4:
            return round(((199 / (325.4 - 225.4)) * (pm25 - 225.5)) + 301)
        else:
            return 500  # AQI values above 325.4 are generally considered "Hazardous"

    def calculate_aqi_no2(self):
        no2 = self.no2 * 0.5315  # Convert from µg/m³ to ppb 24.45/46.0055
        if no2 <= 53:
            return round((50 / 53) * no2)
        elif 53 < no2 <= 100:
            return round(((49 / 47) * (no2 - 54)) + 51)
        elif 100 < no2 <= 360:
            return round(((49 / 260) * (no2 - 101)) + 101)
        elif 360 < no2 <= 649:
            return round(((49 / 289) * (no2 - 361)) + 151)
        elif 649 < no2 <= 1249:
            return round(((99 / 600) * (no2 - 650)) + 201)
        elif 1249 < no2 <= 2049:
            return round(((99 / 800) * (no2 - 1250)) + 301)
        else:
            return 500

    def calculate_aqi_so2(self):
        so2 = self.so2 * 0.3816 # Convert from µg/m³ to ppb 24.45/64.066
        if so2 <= 35:
            return round((50 / 35) * so2)
        elif 35 < so2 <= 75:
            return round(((49 / 40) * (so2 - 36)) + 51)
        elif 75 < so2 <= 185:
            return round(((49 / 110) * (so2 - 76)) + 101)
        elif 185 < so2 <= 304:
            return round(((49 / 119) * (so2 - 186)) + 151)
        elif 304 < so2 <= 604:
            return round(((99 / 300) * (so2 - 305)) + 201)
        elif 604 < so2 <= 1004:
            return round(((99 / 400) * (so2 - 605)) + 301)
        else:
            return 500

    def calculate_aqi_pm10(self):
        pm10 = self.pm10
        if pm10 <= 54:
            return round((50 / 54) * pm10)
        elif 54 < pm10 <= 154:
            return round(((49 / 100) * (pm10 - 55)) + 51)
        elif 154 < pm10 <= 254:
            return round(((49 / 100) * (pm10 - 155)) + 101)
        elif 254 < pm10 <= 354:
            return round(((49 / 100) * (pm10 - 255)) + 151)
        elif 354 < pm10 <= 424:
            return round(((99 / 70) * (pm10 - 355)) + 201)
        elif 424 < pm10 <= 604:
            return round(((99 / 180) * (pm10 - 425)) + 301)
        else:
            return 500

    def calculate_aqi_o3(self):
        if self.o3 < 125:
            o3 = self.o3_8 * 0.5094  # Convert from µg/m³ to ppb（24.45/48)
            if o3 <= 54:
                return round((50 / 54) * o3)
            elif 54 < o3 <= 70:
                return round(((49 / 16) * (o3 - 55)) + 51)
            elif 70 < o3 <= 85:
                return round(((49 / 15) * (o3 - 71)) + 101)
            elif 85 < o3 <= 105:
                return round(((49 / 20) * (o3 - 86)) + 151)
            elif 105 < o3 <= 200:
                return round(((99 / 95) * (o3 - 106)) + 201)
            else:
                return 500
        else:
            o3 = self.o3 * 0.5094
            if 124 < o3 <= 164:
                return round(((49 / 40) * (o3 - 125)) + 101)
            elif 164 < o3 <= 204:
                return round(((49 / 40) * (o3 - 165)) + 151)
            elif 204 < o3 <= 404:
                return round(((99 / 200) * (o3 - 205)) + 201)
            elif 404 < o3 <= 604:
                return round(((99 / 200) * (o3 - 405)) + 301)
            else:
                return 500

    def calculate_aqi_co(self):
        co = self.co * 0.8729 # Convert from mg/m³ to ppm
        if co <= 4.4:
            return round((50 / 4.4) * co)
        elif 4.5 < co <= 9.4:
            return round(((49 / 5) * (co - 4.5)) + 51)
        elif 9.5 < co <= 12.4:
            return round(((49 / 3) * (co - 9.5)) + 101)
        elif 12.5 < co <= 15.4:
            return round(((49 / 3) * (co - 12.5)) + 151)
        elif 15.5 < co <= 30.4:
            return round(((99 / 15) * (co - 15.5)) + 201)
        elif 30.5 < co <= 50.4:
            return round(((99 / 20) * (co - 30.5)) + 301)
        else:
            return 500

    def get_final_aqi(self):
        aqis = [self.calculate_aqi_pm25(), self.calculate_aqi_no2(), self.calculate_aqi_so2(),
                self.calculate_aqi_pm10(), self.calculate_aqi_o3(), self.calculate_aqi_co()]
        return max(aqis)


def get_iaqi_data_wuhan(station_name):
    station_name_encoded = urllib.parse.quote(station_name)
    url = f"https://pm.hbj.wuhan.gov.cn/getAirHourMsgByStationName.jspx?stationName={station_name_encoded}"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        iaqi_data = data.get("hourlist")[0]
        result = {"time": iaqi_data.get("createtime"), "pm25": eval(iaqi_data.get("pm25onehour")), "no2": eval(iaqi_data.get("no2onehour")),
                  "so2": eval(iaqi_data.get("so2onehour")), "pm10": eval(iaqi_data.get("pm10onehour")),
                  "o3": eval(iaqi_data.get("o3onehour")), "co": eval(iaqi_data.get("coonehour")), "o3_8": eval(iaqi_data.get("o3eighthour"))}
        return result



def get_aqi_level(station):
    """Get AQI level for a specific station."""
    aqi_data = get_iaqi_data_wuhan(station)
    aqi_calculator = AirQualityIndexCalculator(pm25=aqi_data.get("pm25"), no2=aqi_data.get("no2"),
                                               so2=aqi_data.get("so2"), pm10=aqi_data.get("pm10"),
                                               o3=aqi_data.get("o3"), co=aqi_data.get("co"), o3_8=aqi_data.get("o3_8"))
    aqi = aqi_calculator.get_final_aqi()
    return aqi

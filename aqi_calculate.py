import requests
import urllib.parse

class AirQualityIndexCalculator:
    def __init__(self, pm25=0, no2=0, so2=0, pm10=0, o3=0, co=0):
        self.pm25 = pm25
        self.no2 = no2
        self.so2 = so2
        self.pm10 = pm10
        self.o3 = o3
        self.co = co

    def calculate_aqi_pm25(self):
        pm25 = self.pm25
        if pm25 <= 12:
            return round((50 / 12) * pm25)
        elif 12 < pm25 <= 35.4:
            return round(((49 / 23.4) * (pm25 - 12.1)) + 51)
        elif 35.4 < pm25 <= 55.4:
            return round(((49 / 20) * (pm25 - 35.5)) + 101)
        elif 55.4 < pm25 <= 150.4:
            return round(((49 / 94.9) * (pm25 - 55.5)) + 151)
        elif 150.4 < pm25 <= 250.4:
            return round(((99 / 100) * (pm25 - 150.5)) + 201)
        elif 250.4 < pm25 <= 350.4:
            return round(((99 / 100) * (pm25 - 250.5)) + 301)
        elif 350.4 < pm25 <= 500.4:
            return round(((99 / 149.9) * (pm25 - 350.5)) + 401)
        else:
            return 500

    def calculate_aqi_no2(self):
        no2 = self.no2
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
        elif 1249 < no2 <= 1649:
            return round(((99 / 400) * (no2 - 1250)) + 301)
        elif 1649 < no2 <= 2049:
            return round(((99 / 400) * (no2 - 1650)) + 401)
        else:
            return 500

    def calculate_aqi_so2(self):
        so2 = self.so2
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
        elif 604 < so2 <= 804:
            return round(((99 / 200) * (so2 - 605)) + 301)
        elif 804 < so2 <= 1004:
            return round(((99 / 200) * (so2 - 805)) + 401)
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
        elif 424 < pm10 <= 504:
            return round(((99 / 80) * (pm10 - 425)) + 301)
        elif 504 < pm10 <= 604:
            return round(((99 / 100) * (pm10 - 505)) + 401)
        else:
            return 500

    def calculate_aqi_o3(self):
        o3 = self.o3
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

    def calculate_aqi_co(self):
        co = self.co
        if co <= 4.4:
            return round((50 / 4.4) * co)
        elif 4.5 < co <= 9.4:
            return round(((49 / 4.9) * (co - 4.5)) + 51)
        elif 9.5 < co <= 12.4:
            return round(((49 / 2.9) * (co - 9.5)) + 101)
        elif 12.5 < co <= 15.4:
            return round(((49 / 2.9) * (co - 12.5)) + 151)
        elif 15.5 < co <= 30.4:
            return round(((99 / 14.9) * (co - 15.5)) + 201)
        elif 30.5 < co <= 40.4:
            return round(((99 / 9.9) * (co - 30.5)) + 301)
        elif 40.5 < co <= 50.4:
            return round(((99 / 9.9) * (co - 40.5)) + 401)
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
                  "o3": eval(iaqi_data.get("o3onehour")), "co": eval(iaqi_data.get("coonehour"))}
        return result



def get_aqi_level():
    # Example usage
    aqi_data = get_iaqi_data_wuhan("洪山地大")
    print(aqi_data)
    aqi_calculator = AirQualityIndexCalculator(pm25=aqi_data.get("pm25"), no2=aqi_data.get("no2"),
                                               so2=aqi_data.get("so2"),
                                               pm10=aqi_data.get("pm10"), o3=aqi_data.get("o3"), co=aqi_data.get("co"))
    aqi = aqi_calculator.get_final_aqi()

    return aqi

if __name__ == "__main__":
    get_aqi_level()
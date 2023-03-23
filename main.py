import requests

def get_tide_stations():
    endpoint = 'https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json'
    response = requests.get(endpoint)
    if response.status_code == 200:
        data = response.json()
        tide_stations = data['stations']
        return tide_stations
    else:
        print('Failed to retrieve tide station list')
        
        
tide_stations = get_tide_stations()

print(len(tide_stations))
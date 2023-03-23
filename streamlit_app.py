import requests
import json
import pandas as pd
import streamlit as st
import base64
from icalendar import Calendar, Event
from datetime import datetime, timezone, timedelta

class TidePredictor:
    """Initializes a TidePredictor object with the given parameters.
    
    Args:
        station_id (str): The ID of the station to retrieve tide data for.
        begin_date (str): The start date of the tide data to retrieve in the format 'YYYYMMDD'.
        end_date (str): The end date of the tide data to retrieve in the format 'YYYYMMDD'.
        units (str, optional): The units to retrieve the tide data in. Defaults to 'metric'.
        low (float, optional): The low tide threshold in meters. Defaults to None.
        high (float, optional): The high tide threshold in meters. Defaults to None.
    
    Attributes:
        station_id (str): The ID of the station to retrieve tide data for.
        begin_date (str): The start date of the tide data to retrieve in the format 'YYYYMMDD'.
        end_date (str): The end date of the tide data to retrieve in the format 'YYYYMMDD'.
        units (str): The units to retrieve the tide data in.
        low (float): The low tide threshold in meters.
        high (float): The high tide threshold in meters.
        tides (pandas.DataFrame): The raw tide data retrieved from the API.
        interpolated_tides (pandas.DataFrame): The tide data interpolated to 1-minute intervals.
        intervals (list): A list of tuples representing the start and end times of each high tide interval.
        station_info (dict): A dictionary containing information about the tide station.
    
    Returns:
        None"""

    
    def __init__(self, station_id, begin_date, end_date, units='metric', low=None, high=None):

        self.station_id = station_id
        self.begin_date = begin_date
        self.end_date = end_date
        self.units = units
        self.low = low
        self.high = high
        self.tides = None
        self.interpolated_tides = None
        self.intervals = None
        self.station_info = None


    def get_tide_predictions(self):
        """This function retrieves tide predictions from the NOAA API and stores them in a pandas DataFrame. 
    
        Args:
            self: The instance of the class calling the function.
            
        Returns:
            None. The function stores the retrieved data in the instance variable 'tides' of the calling class.
        """

        base_url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

        params = {
            "station": self.station_id,
            "product": 'predictions',
            "time_zone": 'GMT',
            "begin_date": self.begin_date,
            "end_date": self.end_date,
            "units": self.units,
            "datum": 'MLLW',
            'interval': 'hilo',
            "format": 'json',
            "application": 'Web_Services'
            }

        response = requests.get(base_url, params=params)

        if response.status_code == 200:
            data = json.loads(response.text)
            results = data["predictions"]

            self.tides = pd.DataFrame.from_dict(results)
            self.tides.rename(columns={'t': 'timestamp', 'v': 'height'}, inplace=True)
            self.tides['height'] = self.tides['height'].astype(float)
            self.tides['timestamp'] = pd.to_datetime(self.tides['timestamp'])
            self.tides.set_index('timestamp', inplace=True)
        else:
            self.tides = None


    def interpolate_tides(self):
        """Interpolates the tidal data to a 1-minute interval using the Piecewise Cubic Hermite Interpolating Polynomial (PCHIP) method.
        
        Args:
            self: The object instance.
            
        Returns:
            None.
        """  
        df  = self.tides[['height']]

        self.interpolated_tides = df.resample('1T').interpolate(method='pchip')


    def get_intervals(self):
        """This function gets the intervals of time where the interpolated tides are within the specified range of low and high values. 
        
        Args:
            self: The object instance.
            
        Returns:
            None. The function sets the intervals attribute of the object instance.
        """
        
        intervals = []
        start = None

        def check_interval(v):
            if self.low and self.high:
                return (v < self.high) and (v > self.low)
            elif self.low:
                return v > self.low
            elif self.high:
                return v < self.high
            else:
                return True

        for t, v in self.interpolated_tides.itertuples():
            if check_interval(v):
                if start is None:
                    start = t
            else:
                if start is not None:
                    end = t
                    intervals.append((start, end))
                    start = None
        self.intervals = intervals


    # def plot_tides(self):
    #     # plot the highs and lows with a smooth line
    #     fig, ax = plt.subplots()
    #     ax.plot(self.interpolated_tides.index, self.interpolated_tides['height'])
    #     ax.plot(self.tides.index, self.tides['height'], 'o', color='red')
    #     # Plot horizontal line at 0
    #     if self.low:
    #         ax.axhline(y=self.low, color='black', linestyle='-')
    #     if self.high:
    #         ax.axhline(y=self.high, color='black', linestyle='-')

    #     for i in self.intervals:
    #         # plot the intervals
    #         ax.axvspan(i[0], i[1], facecolor='green', alpha=0.1)

    #     fig.set_size_inches(18.5, 10.5)
    #     plt.show()



    def get_station_info(self):
        """This function retrieves information about a specific station from the NOAA API. 
    
        Args:
            self: The instance of the class calling the function.
            
        Returns:
            None. The function sets the station_info attribute of the instance to the retrieved data if the request is successful. Otherwise, it prints an error message.
        """
        
        endpoint = 'https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/' + self.station_id + '.json'
        response = requests.get(endpoint)
        if response.status_code == 200:
            data = response.json()
            self.station_info = data['stations']
        else:
            print('Failed to retrieve  station info')



    def create_ical_file(self):
        """ Creates an iCalendar file (.ics) with events based on the intervals and station information provided.
        
        Args:
            self: The instance of the class.
        
        Returns:
            None."""

        
        cal = Calendar()

        # set the timezone offset to GMT
        tz_offset = timezone(timedelta(hours=0))

        # loop through events and add to calendar
        station_name = self.station_info[0]['name']
        for start, stop in self.intervals:
            event = Event()
            event.add('summary', f'{station_name} min {self.low} max {self.high}')
            event.add('dtstart', start.replace(tzinfo=tz_offset))
            event.add('dtend', stop.replace(tzinfo=tz_offset))
            cal.add_component(event)

        # write ical file
        with open('mycalendar.ics', 'wb') as f:
            f.write(cal.to_ical())
            
        # create a download button for the ical file
        with open('mycalendar.ics', 'rb') as f:
            contents = f.read()
            b64 = base64.b64encode(contents).decode()
            href = f'<a href="data:file/ics;base64,{b64}" download="mycalendar.ics">Download iCalendar file</a>'
            st.markdown(href, unsafe_allow_html=True)
            
    def run(self):
        """This function runs the entire process of retrieving data, interpolating, and creating an iCalendar file.
        
        Args:
            self: The instance of the class.
            
        Returns:
            None."""
        
        self.get_tide_predictions()
        self.interpolate_tides()
        self.get_intervals()
        self.get_station_info()
        self.create_ical_file()


if __name__ == "__main__":

    st.title("Tide Calendar Generator")

    st.write("This app retrieves tide data from the NOAA API and creates an iCalendar file with intervals in a specified tide heights.")

    station_id = st.text_input("Enter the station ID (Get one from here https://tidesandcurrents.noaa.gov/tide_predictions.html):", "TWC0419")
    # begin_date = st.text_input("Enter the start date (YYYYMMDD):")
    b = st.date_input("Enter the start date", datetime.today())
    begin_date = b.strftime("%Y%m%d")
    # end_date = st.text_input("Enter the end date (YYYYMMDD):")
    e = st.date_input("Enter the end date", datetime.today()+ datetime.timedelta(days=7))
    end_date = e.strftime("%Y%m%d")
    units = st.selectbox("Select the units:", ["metric", "english"])
    low = st.number_input("Enter the low limit:", min_value=-20.0, max_value=20.0, step=0.1)
    high = st.number_input("Enter the high limit:", min_value=-20.0, max_value=20.0, step=0.1)

    if st.button("Run"):
        tidepredictor = TidePredictor(station_id, begin_date, end_date, units=units, low=low, high=high)
        tidepredictor.run()

        st.write("Tide data retrieved and iCalendar file created.")
        st.write("Intervals:")
        for start, stop in tidepredictor.intervals:
            st.write(f"{start} - {stop}")

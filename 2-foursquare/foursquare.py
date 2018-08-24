"""
This is the entry point to download foursquare venue details and tips.
The documentation of api can be found at "https://developer.foursquare.com/docs".
To start downloading client id and client secret must be updated
in config.py file.

There are four main components in downloading the venue data. Each of the component
can be run/scheduled separately.

By default, it reads and writes to 'KE5106' database. You may change it in config.py.
"""

import fsq_mrt
import venue_details
import process_venue_details
import venue_tips


def main():


    #1. Download the venues meta data using MRT seeds
    print("Downloading venues meta data using MRT location seeds")
    fsq_mrt.main()
    #2. For each downloaded venue, download the remaining details
    print("Downloading venue details for each venue")
    venue_details.main()
    #3. Clean up the venues, and move to access layer
    print("Cleaning up the downloaded venues")
    process_venue_details.main()
    #4. For downloaded venue download tips
    print("Downloading tips for the venues")
    venue_tips.main()

    return None

if __name__ == "__main__":
    main()

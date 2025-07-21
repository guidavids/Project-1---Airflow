import requests
import pandas as pd
import pprint as pp

def extract_data() -> dict:
    json_response = requests.get("https://restcountries.com/v3.1/all?fields=name,population,currencies,independent").json()
    print(json_response, "\n", type(json_response))

    return json_response

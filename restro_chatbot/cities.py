import os
import numpy as np
import pandas as pd

# Categerize the cities to Tier-1, Tier2 and Tier3 according population of city.
# The Reserve Bank of India (RBI) classifies centres into six tiers based on population.
def get_category(row):
    if(row['population_total'] >= 100000):
        return 'tier1'
    elif(row['population_total'] >= 50000 and row['population_total'] < 100000):
        return 'tier2'
    elif(row['population_total'] >= 20000 and row['population_total'] < 50000):
        return 'tier3'
    elif(row['population_total'] >= 10000 and row['population_total'] < 19000):
        return 'tier4'
    elif(row['population_total'] >= 5000 and row['population_total'] < 10000):
        return 'tier5'
    elif(row['population_total'] < 5000):
        return 'tier6'

#Get soundex code for city
def get_soundex(token):
    """Get the soundex code for the string"""
    token = token.upper()

    soundex = ""
    
    # first letter of input is always the first letter of soundex
    soundex += token[0]
    
    # create a dictionary which maps letters to respective soundex codes. Vowels and 'H', 'W' and 'Y' will be represented by '.'
    dictionary = {"BFPV": "1", "CGJKQSXZ":"2", "DT":"3", "L":"4", "MN":"5", "R":"6", "AEIOUHWY":"."}
    
    for char in token[1:]:
        for key in dictionary.keys():
            if char in key:
                code = dictionary[key] 
                if code != '.': 
                    if code != soundex[-1]: 
                        soundex += code 
                    
    
    # trim or pad to make soundex a 4-character code
    soundex = soundex[:4].ljust(4, "0")
    return soundex


# File location of cities details and its pincode details
cities_path =  os.path.abspath('data/knowledgebase/cities_r2.csv')
cities_pin_codes_path = os.path.abspath('data/knowledgebase/india_pincodes.csv')
tier_1_nd_2_cities = os.path.abspath('data/knowledgebase/cities')

# Load cities data and cities pincodes data of india
cities_data = pd.read_csv(cities_path)
cities_pincodes_data = pd.read_csv(cities_pin_codes_path)
print(cities_pincodes_data.info())
# change city names to lower case
cities_pincodes_data['Taluk'] = cities_pincodes_data['Taluk'].str.lower()
cities_data['name_of_city'] = cities_data['name_of_city'].str.lower()
cities_data['population_total'] = cities_data['population_total'].astype('int')
cities_data['category'] = cities_data.apply(lambda row : get_category(row), axis = 1)

# Initialize the soundex data for tier1 and tier2 cities
major_cities = None
cities_soundex_data = dict()
with open(tier_1_nd_2_cities) as data:
    major_cities = data.readline().lower().split()

for city in major_cities:
    cities_soundex_data[get_soundex(city)] = city

'''
Load Cities data and categerize them as tier-1, tier-2 and tier-3 cities
'''
class CitiesData:
        
    def __init__(self):
        pass
        
    # Fetch city category using city_name
    def get_city_category(self, city_name):
        city_soundex = get_soundex(city_name)
        
        if city_soundex in cities_soundex_data:
            return (cities_soundex_data[city_soundex], 'tier1_tier2')
        else:
            filtered_by_city = cities_data[cities_data['name_of_city'] == city_name.lower()]
            category = None
            if(len(filtered_by_city.index) > 0):
                category = cities_data[cities_data['name_of_city'] == city_name.lower()].iloc[0].category
                return (city_name, category)
            else:
                return None
            
    
    # Fetch city category based on city pincode
    def get_city_from_pincode(self, city_pincode, logger):
        logger.info("inside get_city_from_pincode")
        filter_by_pincode = cities_pincodes_data.loc[cities_pincodes_data['pincode'] == int(city_pincode), 'Taluk']
        
        if(len(filter_by_pincode) > 0):
            cities_list = list(filter_by_pincode)
            logger.info("Identified List of cities : {} for pincode: {}".format(cities_list, city_pincode))
            category = None
            for city_name in cities_list:
                tuple_set = self.get_city_category(city_name)
                logger.info("checking city : {} for pincode: {}".format(city_name, city_pincode))
                if(tuple_set is not None):
                    return (tuple_set[0], tuple_set[1])
        else:
            return None

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import pandas as pd
import numpy as np
from rasa_sdk import Action
from rasa_sdk.events import SlotSet
import zomatopy
import cities
from cities import CitiesData
from flask_email_client import EmailClient
import json
import re
import logging

LOG_FILENAME = "actions.log"
# Initialize Actions logger                          
logger = logging.getLogger("Actions")
logger.setLevel(logging.DEBUG)

# Add the log message handler to the logger
handler = logging.handlers.RotatingFileHandler(
              LOG_FILENAME, maxBytes=5*1024*1024, backupCount=5)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
handler.setLevel(logging.DEBUG)

logger.addHandler(handler)

#Use default cusine for fallback option
default_cusine = 'chinese'

# Initilize soundex for cusine
cuisines_dict={'american':1,
                       'chinese':25,
                       'mexican':73,
                       'italian':55,
                       'north indian':50,
                       'south indian':85}
 
cusine_soundex_data = dict()

# Fill cusine soundex data
for cussnd in cuisines_dict.keys():
   cusine_soundex_data[cities.get_soundex(cussnd)] = cussnd
   
class ActionSearchRestaurants(Action):
    
    def name(self):
        return 'action_search_restaurants'
    
    def run(self, dispatcher, tracker, domain):
        config={ "user_key":"bc5f75f74ab805a051b1fde8b8c6970e"}
        zomato = zomatopy.initialize_app(config)
        budget = tracker.get_slot('budget')
        loc = tracker.get_slot('location')
        cuislot = tracker.get_slot('cuisine')
        cuisine = None
        # calculate soundex for user provided cusine and get value from cusine_soundex_data 
        try:
            cuisine = cusine_soundex_data[cities.get_soundex(cuislot)]
        except:
            cuisine=None
        # In case user provided cusine is not available fallback to default option
        if(cuisine is None):
            dispatcher.utter_message("I am sorry, can't find any results for "+cuislot + " - please try again.")
            return [SlotSet('location',loc), SlotSet('cuisine', None), SlotSet('result', None)]

        if(budget not in ["low","med","high"]):
            logger.info("Prompting for budget again.")
            dispatcher.utter_message("I am sorry, I can only search in 3 price ranges - please select one")
            return [SlotSet('location',loc), SlotSet('budget', None), SlotSet('result', None)]

            
        logger.info("Searching for "+cuisine+" in "+loc+" for "+budget+" price range")
        location_detail=zomato.get_location(loc, 1)
        d1 = json.loads(location_detail)
        lat=d1["location_suggestions"][0]["latitude"]
        lon=d1["location_suggestions"][0]["longitude"]
        results=zomato.restaurant_search("", lat, lon, 
                               str(cuisines_dict.get(cuisine)), 20)
        d = json.loads(results)
        response=""
        rest_cntr = 0
        rest_list = list()
        if d['results_found'] > 0:
            price_hi = 0
            price_lo = 0
            if budget == "low":
                price_hi = 300
            elif budget == "med":
                price_lo = 300
                price_hi = 700
            elif budget == "high":
                price_lo = 700
 
            logger.info("Got " + str(len(d['restaurants'])) + "results from zomato")
            for restaurant in d['restaurants']:
                if price_hi > 0:
                    if restaurant['restaurant']['average_cost_for_two'] > price_hi:
                        continue

                if price_lo > 0:
                    if restaurant['restaurant']['average_cost_for_two'] < price_lo:
                        continue
 
                rest_list.append( \
                          [restaurant['restaurant']['name'], \
                          restaurant['restaurant']['location']['address'], \
                          str(restaurant['restaurant']['average_cost_for_two']), \
                          restaurant['restaurant']['user_rating']['aggregate_rating']])
                rest_cntr += 1
                # Pick top 10 resturaunt list from response if available
                if rest_cntr > 10:
                    break
                    
        if len(rest_list) > 0:
            #response = "City : " + loc + "\nCuisine : " + cuisine + "\nPrice range:" + budget + "\n"
            top5_responses = ""
            for index, restr in enumerate(rest_list):
                response = response + restr[0] + " in " + restr[1] + " has been rated " + str(restr[3]) + "\n"
                #response = response + "rating [" + restr[3] + "] - Avg cost for 2 [Rs. " + restr[2] + \
                            #"] -- " + restr[0] + ", " + restr[1] + "\n" 
                if(index < 5):
                    top5_responses = top5_responses + restr[0] + " in " + restr[1] + " has been rated " + str(restr[3]) + "\n"
                    
        logger.info("Response result : {}".format(response))
        if response == "" :
            msg = "Sorry, No results found within budget :{} for cuisine: {} in location: {}, Consider revising them.".format(budget, cuisine, loc)
            dispatcher.utter_message(msg)
            msg = "How about a different cuisine?"
            dispatcher.utter_message(msg)
            response = None
            return [SlotSet('location',loc), SlotSet('cuisine',None), SlotSet('budget',None)]
        else:     
            dispatcher.utter_message(top5_responses)
        return [SlotSet('location',loc), SlotSet('result', response)]

class ActionCheckBudget(Action):

    def name(self):
        return 'check_budget'
        
    def run(self, dispatcher, tracker, domain):
        logger.info("Start Action check budget")
        bud = tracker.get_slot('budget')
        if bud in ["low","med","high"]:
            return [SlotSet('budget', bud)]
        else:
            dispatcher.utter_message("My apologies, I can support only limited options for price range. Please select one of the options when asked.\n\n")
            return [SlotSet('budget', None)]
            
# Action to validate locations
class ActionCheckLocation(Action):
    
    def name(self):
        return "action_check_location"
    
    # Check whether location is string or pincode. If pincode we try to fill location using pincode
    def is_loc_value_is_pincode(self, loc):
        match_found = re.search('^\d{6}$', loc)
        if match_found:
           return True
        else:
           return False
           
    def run(self, dispatcher, tracker, domain):
        logger.info("Start ActionCheckLocation")
        loc = tracker.get_slot('location')
        cities = CitiesData()
        loc_data = None
        if(self.is_loc_value_is_pincode(loc)):
            loc_data = cities.get_city_from_pincode(loc)
        else:
            loc_data = cities.get_city_category(loc)
        logger.info("Checking location for : {}".format(loc_data if (loc_data is not None) else ""))
        if (loc_data == None):
            logger.info("location: {} doesn't exist at all".format(loc))
            return [SlotSet('location', None), SlotSet('location_found', 'notfound')]
        elif(loc_data[1] != 'tier1_tier2'):
            return [SlotSet('location', None), SlotSet('location_found', loc_data[1])]
        else:
            return [SlotSet('location', loc_data[0]), SlotSet('location_found', loc_data[1])]
            
# Send Email Action
class ActionEmailRestuarauntDetails(Action):
    def name(self):
        return 'email_restaurant_details'

    def run(self, dispatcher, tracker, domain):
        logger.info("Inside ActionEmailRestuarauntDetails")
        loc = tracker.get_slot('location')
        price_q = tracker.get_slot('budget')
        email = tracker.get_slot('email')
        email_body = tracker.get_slot('result')

        try:
            cuisine = cusine_soundex_data[cities.get_soundex(tracker.get_slot('cuisine'))]
        except:
            cuisine = None

        if email_body is None or cuisine is None or price_q is None or loc is None:
            dispatcher.utter_message("No valid search results to send.")
            return []        
            

        subject = "{}-{}-{}".format(loc, cuisine, price_q)
        logger.info("Sending mail to :{} with subject: {}".format(email, subject))
        # Initialize email client
        email_client = EmailClient()
        status = email_client.send_email(email, subject, email_body)
        
        if(status):
            logger.info("Sent Restaurant details to : {} successfully.".format(email))
            dispatcher.utter_message("Mail Sent successfully to "+email+ ".")
            dispatcher.utter_message(template="utter_final_bye")
        else:
            logger.info("Failed to send email to recepient: {}".format(email))
            dispatcher.utter_message("Failed to sent email due to technical issues.")
            dispatcher.utter_message(template="utter_final_bye")
        return []        

import json
import boto3
import requests
import clearbit
from fuzzywuzzy import fuzz
from fuzzywuzzy import process 


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']



def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }

def lambda_handler(event, context):
    
    invocationSource = event['invocationSource']
    my_app_id =  '243526475847' + '-' +event["userId"]
    
    if invocationSource == "DialogCodeHook":
        return dispatch(event)
    
    elif invocationSource == "FulfillmentCodeHook":
        final_thing = 'Welcome ' + get_slots(event)["name"]
        dynamo_resource = boto3.resource('dynamodb')            
        dynamo_meetup_table = dynamo_resource.Table("myMeetupTable")
        dynamo_people_table = dynamo_resource.Table("myPeopleData")
        
        print('App Id - ',my_app_id)
        response = dynamo_meetup_table.get_item(Key = {'app-id':my_app_id})
        
        ###################################################################
        s3 = boto3.client('s3')
        bucket = 'collegeipedsdict'  
        key = 'app.json'    ## Json File with University names and Corresponding Ipeds Code.
        data = s3.get_object(Bucket=bucket, Key=key)
        json_data = json.loads(data['Body'].read()) ## Dictionary with University Names and Their IPEDS Code. 
        query = get_slots(intent_request)['university']
        
        if(query in json_data.keys()):
            ipeds_code = json_data[query]
            college_api_key = 'BbKTEOvgkFbtPSyJjs1P7L5rX6Zes8F7B3eI09s4'
            url = 'https://api.data.gov/ed/collegescorecard/v1/schools?api_key=' + college_api_key + '&id=' + str(int(ipeds_code))
            college_response = requests.get(url)
                                
            if college_response:
                rj = college_response.json()
                college_state = rj['results'][0]['school']['state']
                average_earnings = rj['results'][0]['latest']['earnings']['6_yrs_after_entry']['mean_earnings']['middle_tercile']

        else:
            college_state = 'Other'
            average_earnings = 'Other'
                
        
        
        ###################################################################
        clearbit.key = 'sk_d6b743adedc8369a8400fe0116d1856c'
        response_clearbit = clearbit.NameToDomain.find(name = get_slots(intent_request)['organisation'])  ## name would come from lex
                            
        if response_clearbit!=None:
            company = clearbit.Company.find(domain = response_clearbit['domain'], stream=True)
                                
            if('category' in company.keys()):
                                    
                if('industry' in company['category'].keys()):
                    sector = company['category']['industry'] ##sector of the company
                                            
                elif('subIndustry' in company['category'].keys()):
                    sector = company['category']['industry']  ##If the industry sector is not present 
            
                else:
                    sector = 'Other'
                                            
            if('metrics' in company.keys()):
                if('alexaGlobalRank' in company['metrics'].keys()):
                    alexa_rank = company['metrics']['alexaGlobalRank'] ##alexa rank of the company
                
                elif('alexaUsRank' in company['category'].keys()):
                    alexa_rank = (company['category']['metrics']['alexaUsRank'])  ##If the global rank is not present
                
                else:
                    alexa_rank = 0
        
        else:
            sector = 'Other'
            alexa_rank = 0
        #####################################################################

              
            
        meetupDynamoDict = response['Item']
        meetupDynamoDict['email'] = get_slots(intent_request)["email"]
        meetupDynamoDict['name'] = get_slots(intent_request)["name"]
        meetupDynamoDict['industry'] = sector
        meetupDynamoDict['uniState'] = college_state 
        meetupDynamoDict['work'] = get_slots(intent_request)["organisation"]
        meetupDynamoDict['alexaScore'] = str(alexa_rank)
        meetupDynamoDict['university'] = get_slots(intent_request)["university"]
        meetupDynamoDict['averageEarning'] = str(average_earnings)
        
        
            
        dynamo_meetup_table.put_item(Item=meetupDynamoDict)  
        
        people_response = dynamo_people_table.get_item(Key = {'faceid':event["userId"]})
        print(people_response)
        peopleDynamoDict= people_response['Item']
            
        peopleDynamoDict['email'] = get_slots(intent_request)["email"]
        peopleDynamoDict['name'] = get_slots(intent_request)["name"]
        peopleDynamoDict['industry'] = sector
        peopleDynamoDict['uniState'] = college_state 
        peopleDynamoDict['work'] = get_slots(intent_request)["organisation"]
        peopleDynamoDict['alexaScore'] = str(alexa_rank)
        peopleDynamoDict['university'] = get_slots(intent_request)["university"]
        peopleDynamoDict['averageEarning'] = str(average_earnings)
        
        
        dynamo_people_table.put_item(Item=peopleDynamoDict)

        return close(event['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': final_thing})

def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """
    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'information':
        return fetchinfo(intent_request)
        
    raise Exception('Intent with name ' + intent_name + ' not supported')
    
def fetchinfo(intent_request):
    """
    Performs dialog management and validation for soliciting dinner suggestions.
    The implementation of this intent demonstrates the use of the elicitSlot dialog action
    in slot validation and re-prompting.
    """
    
    email_address = get_slots(intent_request)["email"]
    university_name = get_slots(intent_request)["university"]
    company_name = get_slots(intent_request)["organisation"]
    name_input = get_slots(intent_request)["name"]
    
    source = intent_request['invocationSource']
    
    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        
        slots = get_slots(intent_request)
        
        validation_result = validate_people_data(email_address,university_name,company_name,name_input,intent_request)
        if(validation_result ==  True):
            final_thing = 'Welcome ' + get_slots(intent_request)["name"]
            dynamo_resource = boto3.resource('dynamodb')            
            dynamo_meetup_table = dynamo_resource.Table("myMeetupTable")
            dynamo_people_table = dynamo_resource.Table("myPeopleData")
            my_app_id =  '243526475847' + '-' +intent_request["userId"]
            print('App Id - ',my_app_id)
            response = dynamo_meetup_table.get_item(Key = {'app-id':my_app_id})
            
            ###################################################################
            s3 = boto3.client('s3')
            bucket = 'collegeipedsdict'  
            key = 'app.json'    ## Json File with University names and Corresponding Ipeds Code.
            data = s3.get_object(Bucket=bucket, Key=key)
            json_data = json.loads(data['Body'].read()) ## Dictionary with University Names and Their IPEDS Code. 
            query = get_slots(intent_request)['university']
            
            if(query in json_data.keys()):
                ipeds_code = json_data[query]
                college_api_key = 'BbKTEOvgkFbtPSyJjs1P7L5rX6Zes8F7B3eI09s4'
                url = 'https://api.data.gov/ed/collegescorecard/v1/schools?api_key=' + college_api_key + '&id=' + str(int(ipeds_code))
                college_response = requests.get(url)
                                    
                if college_response:
                    rj = college_response.json()
                    college_state = rj['results'][0]['school']['state']
                    average_earnings = rj['results'][0]['latest']['earnings']['6_yrs_after_entry']['mean_earnings']['middle_tercile']
    
            else:
                college_state = 'Other'
                average_earnings = 'Other'
                    
            
            
            ###################################################################
            clearbit.key = 'sk_d6b743adedc8369a8400fe0116d1856c'
            response_clearbit = clearbit.NameToDomain.find(name = get_slots(intent_request)['organisation'])  ## name would come from lex
                                
            if response_clearbit!=None:
                company = clearbit.Company.find(domain = response_clearbit['domain'], stream=True)
                                    
                if('category' in company.keys()):
                                        
                    if('industry' in company['category'].keys()):
                        sector = company['category']['industry'] ##sector of the company
                                                
                    elif('subIndustry' in company['category'].keys()):
                        sector = company['category']['industry']  ##If the industry sector is not present 
                
                    else:
                        sector = 'Other'
                                                
                if('metrics' in company.keys()):
                    if('alexaGlobalRank' in company['metrics'].keys()):
                        alexa_rank = company['metrics']['alexaGlobalRank'] ##alexa rank of the company
                    
                    elif('alexaUsRank' in company['category'].keys()):
                        alexa_rank = (company['category']['metrics']['alexaUsRank'])  ##If the global rank is not present
                    
                    else:
                        alexa_rank = 0
            
            else:
                sector = 'Other'
                alexa_rank = 0
            #####################################################################
                
            meetupDynamoDict = response['Item']
            meetupDynamoDict['email'] = get_slots(intent_request)["email"]
            meetupDynamoDict['name'] = get_slots(intent_request)["name"]
            meetupDynamoDict['industry'] = sector
            meetupDynamoDict['uniState'] = college_state 
            meetupDynamoDict['work'] = get_slots(intent_request)["organisation"]
            meetupDynamoDict['alexaScore'] = str(alexa_rank)
            meetupDynamoDict['university'] = get_slots(intent_request)["university"]
            meetupDynamoDict['averageEarning'] = str(average_earnings)
                
            dynamo_meetup_table.put_item(Item=meetupDynamoDict)  
            
            people_response = dynamo_people_table.get_item(Key = {'faceid':intent_request["userId"]})
            
            peopleDynamoDict= people_response['Item']
                
            peopleDynamoDict['email'] = get_slots(intent_request)["email"]
            peopleDynamoDict['name'] = get_slots(intent_request)["name"]
            peopleDynamoDict['industry'] = sector
            peopleDynamoDict['uniState'] = college_state 
            peopleDynamoDict['work'] = get_slots(intent_request)["organisation"]
            peopleDynamoDict['alexaScore'] = str(alexa_rank)
            peopleDynamoDict['university'] = get_slots(intent_request)["university"]
            peopleDynamoDict['averageEarning'] = str(average_earnings)
            
            dynamo_people_table.put_item(Item=peopleDynamoDict)

            
            
            return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': final_thing})
        
        return delegate(intent_request['sessionAttributes'],get_slots(intent_request))
    
def validate_people_data(email_address,university_name,company_name,name_input,intent_request):
    s3 = boto3.client('s3')
    bucket = 'collegeipedsdict'  
    key = 'app.json'    ## Json File with University names and Corresponding Ipeds Code.
    data = s3.get_object(Bucket=bucket, Key=key)
    json_data = json.loads(data['Body'].read()) ## Dictionary with University Names and Their IPEDS Code. 
            
    if email_address is not None:
        bad_chars = [';', ':', '!', "*","?", "-", ".","'"] ## removing useless characters, if any in the user input.
        
        ###People Data Labs###
        
        pdl_url = "https://api.peopledatalabs.com/v4/person"
    
        params = {
        "api_key":'05283552531957a6e7cbf542a3ec39e27b378f06ef95610a5e02d02498d9d3be',
        "email": [email_address]   
        }
    
        json_response_people_data = requests.get(pdl_url,  params=params).json()
    
        if(json_response_people_data['status'] == 200):
            
            if('names' in json_response_people_data['data'].keys() and len(json_response_people_data['data']['names']) >= 1):
                user_name = json_response_people_data['data']['names'][0]['clean']
                get_slots(intent_request)['name'] = user_name
            
            
            if('experience' in json_response_people_data['data'].keys()):
            
                for i in json_response_people_data['data']['experience']:
                    if('company' in i.keys() and i['company'] is not None):
                        if('name' in i['company'].keys()):
                            clearbit_company = i['company']['name'].lower() 
        
                            for i in bad_chars : 
                                clearbit_company = clearbit_company.replace(i, '')
                            
                            ### Clear Bit ###
                            
                            clearbit.key = 'sk_d6b743adedc8369a8400fe0116d1856c'
                            response_clearbit = clearbit.NameToDomain.find(name = clearbit_company)  ## name would come from lex
                            
                            if response_clearbit!=None:
                                company = clearbit.Company.find(domain = response_clearbit['domain'], stream=True)
                                get_slots(intent_request)['organisation'] = clearbit_company
                                
                              #  if('category' in company.keys()):
                                    
                              #      if('industry' in company['category'].keys()):
                             #           sector = company['category']['industry'] ##sector of the company
                             #           print('Sector',sector)
                                            
                             #       else:
                             #           if('subIndustry' in company['category'].keys()):
                             #               sector = company['category']['industry']  ##If the industry sector is not present 
                                            
                             #   if('metrics' in company.keys()):
                                        
                             #       if('alexaGlobalRank' in company['metrics'].keys()):
                             #               alexa_rank = company['metrics']['alexaGlobalRank'] ##alexa rank of the company
                             #               print('Alexa rank',alexa_rank)    
                             #       else:
                             #           if('alexaUsRank' in company['category'].keys()):
                             #               alexa_rank = (company['category']['metrics']['alexaUsRank'])  ##If the global rank is not present
                             #               print('Alexa rank',alexa_rank)
                                        
                            
            if('education' in json_response_people_data['data'].keys()):    
                for i in json_response_people_data['data']['education']:
                    if('school' in i.keys()):
                        if('name' in i['school'].keys()):
                            school_name = i['school']['name']
                            
                            for i in bad_chars: 
                                school_name = school_name.replace(i,'')
            
                            ## matching user input with the university dictionary we have. Partial string matching to account for unorthodox user inputs.
                            fuzz_list = process.extract(school_name.lower(),json_data.keys(),scorer=fuzz.token_sort_ratio,limit=1)
                                                    
                            ## only considering the name if the match ratio is equal or above 90%.
                            if(fuzz_list[0][1] >= 90):
                                ipeds_code = json_data[fuzz_list[0][0]]
                                get_slots(intent_request)['university'] = fuzz_list[0][0]
                                    
            for i in (intent_request['currentIntent']['slots']):
                if(intent_request['currentIntent']['slots'][i] == None):
                    return False
                
                    

        if university_name is not None:
            
            for i in bad_chars: 
                university_name = university_name.replace(i,'')
                            
            ## matching user input with the university dictionary we have. Partial string matching to account for unorthodox user inputs.
            fuzz_list = process.extract(university_name.lower(),json_data.keys(),scorer=fuzz.token_sort_ratio,limit=1)
                            
            ## only considering the name if the match ratio is equal or above 90%.
            if(fuzz_list[0][1] >= 90):
                ipeds_code = json_data[fuzz_list[0][0]]
                get_slots(intent_request)['university'] = fuzz_list[0][0]
                #print('Data From College Score card found for - ',fuzz_list[0][0])
            
                
            for i in (intent_request['currentIntent']['slots']):
                if(intent_request['currentIntent']['slots'][i] == None):
                    return False
                
            return True        
                

        if company_name is not None:
            
            for i in bad_chars : 
                company_name = company_name.replace(i, '')
                            
            ### Clear Bit ###
                            
            clearbit.key = 'sk_d6b743adedc8369a8400fe0116d1856c'
            response_clearbit = clearbit.NameToDomain.find(name=company_name)  ## name would come from lex
                            
            if response_clearbit!=None:
                company = clearbit.Company.find(domain = response_clearbit['domain'], stream=True)
                get_slots(intent_request)['organisation'] = clearbit_company
                
                for i in (intent_request['currentIntent']['slots']):
                    if(intent_request['currentIntent']['slots'][i] == None):
                        return False
                
                return True        

        if name_input is not None:
            return True
        
        return False
    
    return False
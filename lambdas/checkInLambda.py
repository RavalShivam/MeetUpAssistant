import json
from boto3 import resource
from boto3.dynamodb.conditions import Key,And,Attr


dynamodb_resource = resource('dynamodb')



def lambda_handler(event, context):
    # TODO implement
    
    table_name = 'myPeopleData' 
    
    people_table = dynamodb_resource.Table(table_name)
    meetup_table = dynamodb_resource.Table('myMeetupTable')
    
    faceId = event['faceid']
    
    
    
    meetupId = "243526475847"
    
    response = people_table.scan(
        FilterExpression=Attr("faceid").eq(faceId) 
    )
    
    # response = people_table.scan()
    returnString = dict()
    table_items = []
    
    for i in response['Items']:
        myCurrentData = response['Items'][0]
        faceId = i['faceid']
        app_id = meetupId + '-' + faceId
        myCurrentData["app-id"] = app_id
        myCurrentData["meetupid"] = meetupId
        returnString['name'] = i['name']
        table_items.append(myCurrentData)
        meetup_table.put_item(Item= myCurrentData)
    
    
    returnString = json.dumps(returnString)
    
    
    return returnString
    
    
    
    
    
   

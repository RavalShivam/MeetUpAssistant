import re
import json
import traceback
from boto3 import resource
import boto3
import botocore
from boto3.dynamodb.conditions import Key,And,Attr

s3_resource = resource('s3')
s3_client = boto3.client('s3')

dynamodb_resource = resource('dynamodb')

def lambda_handler(event, context):
    
    table_name = 'myMeetupTable' 
    
    table = dynamodb_resource.Table(table_name)
    
    
    
    meetupId = "243526475847"
    
    response = table.scan(
        FilterExpression=Attr("meetupid").eq(meetupId) 
    )
    
    
    
    table_items = []
    for i in response['Items']:
        myCurrentData = dict()
        
        if(len(i['university']) > 0):
            myCurrentData['university'] = i['university']
            myCurrentData['uniState'] = i['uniState']
            myCurrentData['averageEarning'] = i['averageEarning']
            myCurrentData['work'] = i['work']
            myCurrentData['industry'] = i['industry']
            myCurrentData['alexaScore'] = i['alexaScore']
            
            table_items.append(myCurrentData)
       
    
    table_json = json.dumps(table_items)
    
    print((table_json))
    
    dynamo_bucket = 'my-dynamo-data'
    dynamo_lambda_path = '/tmp/dynamodb_data.json'
    dynamo_file_name = 'dynamodb_data.json'
    
    
    try:
        s3_resource.Bucket(dynamo_bucket).download_file(dynamo_file_name, dynamo_lambda_path)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise
        
    
    
    dynamo_s3_path = dynamo_file_name
    
    encoded_string = table_json.encode("utf-8")
    
    s3_resource.Bucket(dynamo_bucket).put_object(Key=dynamo_s3_path, Body=encoded_string)
    
    s3_url = 'https://' + dynamo_bucket + '.s3.amazonaws.com/' + dynamo_file_name
    
    quicksight_bucket = 'project-quicksight-data'
    quicksight_lambda_path = '/tmp/{my_manifest.json}'
    quicksight_file_name = 'my_manifest.json'
    
    try:
        s3_resource.Bucket(quicksight_bucket).download_file(quicksight_file_name, quicksight_lambda_path)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise
    
    
    
    manifest_str = '{"fileLocations": [{"URIs": []}],"globalUploadSettings": {"format": "JSON" , "textqualifier": "\\""}}'
    manifest_json = json.loads(manifest_str)
    updated_manifest_json = manifest_json['fileLocations'][0]['URIs']
    updated_manifest_json.append(s3_url)
    
    print(manifest_json)
    
    quicksight_encoded_string = str(manifest_json).encode("utf-8")
    quicksight_s3_path = quicksight_file_name
    
    s3_resource.Bucket(quicksight_bucket).put_object(Key=quicksight_s3_path, Body=quicksight_encoded_string)
    
    
    
    
    
    
    
    
#university - name, state and average earnings
#company - name, sector and alexa score
import json
import boto3

def lambda_handler(event, context):
    # TODO implement
    
    userId = event['faceid']
    faceId = event['faceid']
    print("Face Id:  ", faceId)
    print(userId)
    
    # TODO implement
    message = event['message']
    
    client = boto3.client('lex-runtime')
    
    response = client.post_text(
    botName = 'MeetUpAnalyzer',
    botAlias = 'initial',
    userId = userId,
    inputText = message)
    
    print("Response::: ",response)

    return response
import boto3
import logging
import base64
import json
import cv2
import os
import random as r
import time
from decimal import Decimal 

s3_client = boto3.client('s3')
s3_resource = boto3.resource('s3')

smsClient = boto3.client('sns')

dynamo_resource = boto3.resource('dynamodb')

dynamo_meetup_table = dynamo_resource.Table("myMeetupTable")
dynamo_people_table = dynamo_resource.Table("myPeopleData")


def lambda_handler(event, context):
    # TODO implement
    logging.info("API CALLED. EVENT IS:{}".format(event))
    meetupId= 243526475847
    print("Data streaming")
    data = event['Records'][0]['kinesis']['data']
    print(base64.b64decode(data))
    json_data = json.loads(base64.b64decode(data).decode('utf-8'))
    stream_name="smart-door-stream"
    print('JSON DATA',json_data)
    
    smsClient = boto3.client('sns')
    mobile = "6466230205"
    
    faceId='123'
    face_search_response = json_data['FaceSearchResponse']
    fileName=''
    if face_search_response is None or len(face_search_response)==0:
        return ("No one at the door")
    else:
        matched_face = json_data['FaceSearchResponse'][0]['MatchedFaces']
        print("Matched: ", matched_face)
    
    if (face_search_response is not None and len(face_search_response) > 0) and ( matched_face is None or len(matched_face)==0):
        fragmentNumber= json_data['InputInformation']['KinesisVideo']['FragmentNumber']
        fileName,faceId=store_image(stream_name,fragmentNumber, None)
        print("Face Id: ",faceId)
    else:
        image_id = json_data['FaceSearchResponse'][0]['MatchedFaces'][0]['Face']['ImageId']
        print('IMAGEID',image_id)
        faceId = json_data['FaceSearchResponse'][0]['MatchedFaces'][0]['Face']['FaceId']
        print('FACEID',faceId)
        fragmentNumber=image_id
    print("Face id to search: ", faceId)
    appid=str(meetupId)+'-'+str(faceId)
    key = {'app-id' : appid}   # here the actual faceId has to be added
    key1 = {'faceid' : faceId}
    meetupdata = dynamo_meetup_table.get_item(Key=key)
    peopledata = dynamo_people_table.get_item(Key=key1)
    
    keys_list = list(peopledata.keys())
    meetup_keys_list=list(meetupdata.keys())
    
    otp=""
    for i in range(4):
        otp+=str(r.randint(1,9))
    sqs_queue_url = 'https://sqs.us-east-1.amazonaws.com/463589813520/meetup'
    print("SQS: ", sqs_queue_url)
    
    if('Item' in meetup_keys_list):
        print("Checked in user")
        return
    else:
        if('Item' in keys_list):
            
            face_id_visitor = peopledata['Item']['faceid']
            msg_body = "checkin:"+ face_id_visitor
            msg = send_sqs_message(sqs_queue_url, msg_body)
            if msg is not None:
                print("Sent SQS message ID: ",msg["MessageId"])
        else:
            link_visitor_image = 'https://smart-door-trr.s3.amazonaws.com/' + fileName
            msg_body = "unknown:"+ str(faceId)
            msg = send_sqs_message(sqs_queue_url, msg_body)
            if msg is not None:
                print("Sent SQS message ID:",msg["MessageId"])
            
            informHost(link_visitor_image)
            
            peopleDynamoDict = dict()
            peopleDynamoDict['faceid'] = faceId
            peopleDynamoDict['photo'] = link_visitor_image
            
            peopleDynamoJson = json.dumps(peopleDynamoDict)
            dynamo_people_table.put_item(Item=peopleDynamoDict)
            
            meetupDynamoDict = dict()
            meetupDynamoDict['app-id'] = str(meetupId) + '-' + (faceId)
            meetupDynamoDict['meetupid'] = str(meetupId)
            meetupDynamoDict['faceid'] = faceId
            meetupDynamoDict['photo'] = link_visitor_image
            
            meetupDynamoJson = json.dumps(meetupDynamoDict)
            dynamo_meetup_table.put_item(Item=meetupDynamoDict)
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
    
def informHost(link_visitor_image):
    message_owner = "Hi! There is a new person at your gathering: "
    message_owner += str(link_visitor_image)
    # smsClient.publish(PhoneNumber="+1"+phone_number,Message=message_owner)
    SENDER = "saqib.i.patel@gmail.com"
    RECIPIENT = "rao.tirupal@gmail.com"
    AWS_REGION = "us-east-1"
    SUBJECT = " New Person at your gathering! "
    BODY_TEXT = message_owner
    BODY_HTML = "<html><head></head><body><h1><font color='red'>New Person at your Gathering</font></h1><p>Hi! There is a new person at your gathering: {}<p></body></html>".format(str(link_visitor_image))
    CHARSET = "UTF-8"
    client = boto3.client('ses',region_name=AWS_REGION)
    response = client.send_email(
        Destination={
            'ToAddresses': [
                RECIPIENT,
            ],
        },
        Message={
            'Body': {
                'Html': {
                    'Charset': CHARSET,
                    'Data': BODY_HTML,
                },
                'Text': {
                    'Charset': CHARSET,
                    'Data': BODY_TEXT,
                },
            },
            'Subject': {
                'Charset': CHARSET,
                'Data': SUBJECT,
            },
        },
        Source=SENDER
    )
    print("Email sent: ",response)

def store_image(stream_name, fragmentNumber,faceId):
    # kvs_client = boto3.client('kinesis-video-archived-media')
    s3_client = boto3.client('s3')
    rekClient=boto3.client('rekognition')
    
    kvs_client = boto3.client('kinesisvideo')
    kvs_data_pt = kvs_client.get_data_endpoint(
        StreamARN='arn:aws:kinesisvideo:us-east-1:463589813520:stream/smart-door-stream/1576448499596',
        APIName='GET_MEDIA'
    )
    print("Kinesis data endpoint",kvs_data_pt)
    end_pt = kvs_data_pt['DataEndpoint']
    kvs_video_client = boto3.client('kinesis-video-media', endpoint_url=end_pt, region_name='us-east-1') # provide your region
    kvs_stream = kvs_video_client.get_media(
        StreamARN='arn:aws:kinesisvideo:us-east-1:463589813520:stream/smart-door-stream/1576448499596', # kinesis stream arn
        StartSelector={'StartSelectorType': 'NOW'}
    )
    print(kvs_stream)
    
    collectionId="meetup"
    print("KVS Stream: ",kvs_stream)
    
    with open('/tmp/stream1.mkv', 'wb') as f:
        print("Processing stream...")
        streamBody = kvs_stream['Payload'].read(2048*16384) # reads min(16MB of payload, payload size)
        # print("Stream:  ", streamBody)
        f.write(streamBody)
        s3_client.upload_file(
            '/tmp/stream1.mkv',
            'smart-door-trr', # replace with your bucket name
            'stream1.mkv'
        )
        print("Stream Stored in S3")
        # use openCV to get a frame
        cap = cv2.VideoCapture('/tmp/stream1.mkv')
        
        # total=int(count_frames_manual(cap)/2)
        # cap.set(2,total)
        ret, frame = cap.read() 
        # print("Image: ",frame)
        print("Ret ", ret)
        cv2.imwrite('/tmp/frame.jpg', frame)
        
        if(faceId is None):
            print("Indexing image")
            faceId=index_image(frame, collectionId,fragmentNumber)
        print("This is the face id: ",faceId,", FragmentNumber: ",fragmentNumber)
        fileName= faceId+'-'+fragmentNumber+'.jpg'
        s3_client.upload_file(
            '/tmp/frame.jpg',
            'smart-door-trr', # replace with your bucket name
            fileName
        )
        cap.release()
        print('Image uploaded')
    return fileName, faceId

def index_image(frame, collectionId, fragmentNumber):
    faceId=''
    try:
        print("Size of Image: ", len(frame))
        rekClient=boto3.client('rekognition')
        retval, buffer = cv2.imencode('.jpg', frame)
        response=rekClient.index_faces(CollectionId=collectionId,
        Image={
        'Bytes': buffer.tobytes(),
        },
        ExternalImageId=fragmentNumber,
        DetectionAttributes=['ALL'])
        print("Ret val: ", retval)
        
        print('Rek Index Response',response)
        
        for faceRecord in response['FaceRecords']:
            faceId = faceRecord['Face']['FaceId']
        print("Face Id after indexing: ", faceId)
    except:
        print("Something went wrong with indexing!")
    return faceId

def count_frames_manual(video):
	total = 0
	while True:
		(grabbed, frame) = video.read()
		if not grabbed:
			break
		total += 1
	return total
def send_sqs_message(sqs_queue_url, msg_body):
    """
    :param sqs_queue_url: String URL of existing SQS queue
    :param msg_body: String message body
    :return: Dictionary containing information about the sent message. If
        error, returns None.
    """
    print("Sending Message to queue")

    # Send the SQS message
    sqs_client = boto3.client('sqs')
    try:
        msg = sqs_client.send_message(QueueUrl=sqs_queue_url,
                                      MessageBody=msg_body)
    except:
        print("Something went wrong with SQS")
        return None
    return msg
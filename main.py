import json
import boto3
import os
import random
from PIL import Image
from itertools import chain
from io import BytesIO, StringIO
from pathlib import Path
import time
import urllib3

attributes = []
layerDict = {}
metadata = {}
images_path = []  

inputWeights = ()

s3 = boto3.Session(aws_access_key_id=os.environ["aws_access_key_id"],aws_secret_access_key=os.environ["aws_secret_access_key"]).resource('s3')
s3_client = boto3.Session(aws_access_key_id=os.environ["aws_access_key_id"],aws_secret_access_key=os.environ["aws_secret_access_key"]).client('s3',region_name='us-east-1')


bucket_name = 'createdatacollections'
image_prefix = '/image/'
json_prefix = '/json/'

bucket = s3.Bucket(bucket_name)


output_image_bucket_name = "output-collections"
output_json_bucket_name = "metadata-collections"

generate_images = []

http = urllib3.PoolManager()


def lambda_handler(event, context):
    data = {
            "collectionID": event['collectionID'],
            "secret": "",
            "newStatus": "in progress"
        }
    encoded_data = json.dumps(data).encode('utf-8')
    if(event['env'] == 'prod'):
        r = http.request('POST', 'LINKgeneration',
        body=encoded_data,
        headers={'Content-Type': 'application/json'})
        print(r.data.decode('utf-8'))
    else:
        r = http.request('POST', 'LINKupdate/generation',
        body=encoded_data,
        headers={'Content-Type': 'application/json'})
        print(r.data.decode('utf-8'))

        
    a = event['numberOfNFT']
    output_image_path = event['output_path']
    output_json_path = event['output_path']
    _prefix = event['input_path']
    
    # print(type(a))
    
    '''numImage is how many image to create'''
    # url = "https://github.com"
    i = 0
    while len(generate_images) < a:
        imageSeq = generateSeqOfImages( tuple(event['weights']) , _prefix)
        image = renderImages(imageSeq, event['width'], event['height'])
        if(image):
            imageName = saveImageFile(image, i, output_image_path) 
            # print(imageName)

            metadata['attributes'] = []
            for val in imageSeq:
                trait_type = {}
                trait_type['trait_type'] = Path(val).parts[1]
                trait_type['value'] =Path(val).stem
                metadata['attributes'].append(trait_type)
            s3object = s3.Object(output_image_bucket_name,  f"{output_json_path+json_prefix+str(imageName[:-4])}.json")
            s3object.put(Body=(bytes(json.dumps(metadata).encode('UTF-8'))))
            i = i + 1
    print(generate_images)
    print(event['collectionID'])
    if(event['collectionID']):
        data = {
            "collectionID": event['collectionID'],
            "secret": "",
            "newStatus": "done"
        }
        encoded_data = json.dumps(data).encode('utf-8')
        if(event['env'] == 'prod'):
            r = http.request('POST', 'LINKgeneration',
            body=encoded_data,
            headers={'Content-Type': 'application/json'})
        else:
            r = http.request('POST', 'hLINKgeneration',
            body=encoded_data,
            headers={'Content-Type': 'application/json'})
    return {
        'statusCode': 200,
        'completed': True
        # 'headers': {
        #     'Access-Control-Allow-Origin': '*'
        # },
        # 'body': {'completed': True}
    }


def generateSeqOfImages(weights, prefix):
    layers = set()
    image_file_name = []
    path_file_name = []
    path_image_name = set()
    
    dirNames = []
    fileNames = []

    result = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix + "/", Delimiter='/')
    for count, val in enumerate(result.get('CommonPrefixes')):
        image_path = pickRandom(val['Prefix'], weights[count])
        dirNames.append(image_path)
        
    return list(chain(*dirNames))

def pickRandom(layer, weights):
    '''randmoly pick an image from each path layers/dir'''
    a = []
    
    inDirs = list(bucket.objects.filter(Prefix=layer))
    
    for fileName in range(0, len(inDirs)):
        a.append(inDirs[fileName].key)
    random_image_file_name = random.choices(a, weights=weights, k=1)
        
    return random_image_file_name

def renderImages(imageSeq, width, height):
    # print("composite Images start")
    if imageSeq in generate_images:
        print('dulplicate')
       
    else:
        print('no dulplicate')
        generate_images.append(imageSeq)
        print(width, height)
        image = Image.new("RGBA", (width, height)) 
        for img in imageSeq:
            file_stream = BytesIO()
            object = bucket.Object(img)
            object.download_fileobj(file_stream)
            img = Image.open(file_stream)
            image = Image.alpha_composite(image, img)
        return image


def saveImageFile(image, i, output_image_path):
    '''save images and put it on S3'''
    image_index = str(i)
    imageName = f"{image_index}.png"
    in_mem_file = BytesIO()
    try:
        image.save(in_mem_file, format='png')
        in_mem_file.seek(0)
        # print("saved..")
        s3_client.put_object(
            Bucket=output_image_bucket_name,
            Key=output_image_path+image_prefix+imageName,
            Body=in_mem_file,
            ContentType='image/png',)
    except :
        # raise e
        print(f"couldn't save {imageName}")
    return imageName

import os
from datetime import datetime
import glob
import io
import base64
from flask import Flask, redirect, render_template, request
from docx import Document 
from tika import parser

from google.cloud import datastore
from google.cloud import storage
from google.cloud import vision
from google.cloud import texttospeech
from google.cloud import translate_v2 as translate


CLOUD_STORAGE_BUCKET = "indigo-skyline-270422" 


app = Flask(__name__)
counter = 0
@app.route('/')
def home():
    return render_template('home_scan.html')
@app.route('/home_scan.html', methods=['GET'])
def home2():
    return render_template('home_scan.html')
@app.route('/img_scan.html', methods=['GET'])
def show():
    global counter
    counter+=1
    # Create a Cloud Datastore client.
    datastore_client = datastore.Client()

    # Use the Cloud Datastore client to fetch information from Datastore about
    # each photo.
    
    query = datastore_client.query(kind='Faces')
    image_entities = list(query.fetch())
    if(counter==1):
        image_entities.clear()

    # Return a Jinja2 HTML template and pass in image_entities as a parameter.
    return render_template('img_scan.html', image_entities=image_entities)

@app.route('/docx_scan.html', methods=['GET'])
def doc_page():
    datastore_client = datastore.Client()

    query = datastore_client.query(kind='DOCS')
    image_entities = list(query.fetch())
    
    return render_template('docx_scan.html', image_entities=image_entities)

@app.route('/upload_photo_docx', methods=['GET', 'POST'])
def upload_photo_docx():
    
    photo = request.files['file']

    doc = Document(photo.filename)

    text = ''
    for paragraph in doc.paragraphs:
        text += paragraph.text
        text += '\n'
    
    
    # Create a Cloud Datastore client.
    translate_client = translate.Client()
    result = translate_client.translate(
    text, target_language="en")
    datastore_client = datastore.Client()

    synthesize_text(result['translatedText'], "doc")


    return redirect('/docx_scan.html')

@app.route('/pdf_scan.html', methods=['GET'])
def pdf_page():
    datastore_client = datastore.Client()
    query=datastore_client.query(kind='PDFs')
    image_entities = list(query.fetch())

    return render_template('pdf_scan.html', image_entities=image_entities)

@app.route('/upload_photo_pdf', methods=['GET', 'POST'])
def upload_photo_pdf():

    storage_client = storage.Client()

    # Get the bucket that the file will be uploaded to.
    bucket = storage_client.get_bucket(CLOUD_STORAGE_BUCKET)


    photo = request.files['file']
    rawText = parser.from_file(photo.filename)
    rawList = rawText['content']

    blob = bucket.blob(photo.filename)
    blob.upload_from_string(
            photo.read(), content_type=photo.content_type)
    # Make the blob publicly viewable.
    blob.make_public()
    
    kind = 'PDFs'

    datastore_client = datastore.Client()

    key = datastore_client.key(kind, blob.name)
    
    rawList = rawList.replace('\n\n', '\n').strip()

    entity = datastore.Entity(key)
    print(entity)
    entity['blob_name'] = "test" 
    print(rawList)

    translate_client = translate.Client()
    result = translate_client.translate(
    rawList, target_language="en")

    synthesize_text(result['translatedText'], "pdf")

    return redirect('/pdf_scan.html')

@app.route('/upload_photo_img', methods=['GET', 'POST'])
def upload_photo_img():
    global counter
    counter+=1
    photo = request.files['file']

    # Create a Cloud Storage client.
    storage_client = storage.Client()

    # Get the bucket that the file will be uploaded to.
    bucket = storage_client.get_bucket(CLOUD_STORAGE_BUCKET)

    # Create a new blob and upload the file's content.
    blob = bucket.blob(photo.filename)
    blob.upload_from_string(
            photo.read(), content_type=photo.content_type)
    # Make the blob publicly viewable.
    blob.make_public()

    # Create a Cloud Vision client.
    vision_client = vision.ImageAnnotatorClient()

    # Use the Cloud Vision client to detect a face for our image.
    source_uri = 'gs://{}/{}'.format(CLOUD_STORAGE_BUCKET, blob.name)
    image = vision.types.Image(
        source=vision.types.ImageSource(gcs_image_uri=source_uri))
    texts = vision_client.text_detection(image).text_annotations
    s=texts[0].description
    # Create a Cloud Datastore client.
    translate_client = translate.Client()
    result = translate_client.translate(
    s, target_language="en")
    datastore_client = datastore.Client()

    synthesize_text(result['translatedText'], "img")

    if(counter==1):
        datastore_client.delete(datastore_client.key(kind, name))
    # Fetch the current date / time.
    current_datetime = datetime.now()

    # The kind for the new entity.
    kind = 'Faces'

    # The name/ID for the new entity.
    name = blob.name
    #if(counter==1):
        #datastore_client.delete_multi(datastore_client.key(kind,name))

    # Create the Cloud Datastore key for the new entity.
    key = datastore_client.key(kind, name)
    
    face_joy = "un"
    # Construct the new entity using the key. Set dictionary values for entity
    # keys blob_name, storage_public_url, timestamp, and joy.
    entity = datastore.Entity(key)
    result = result['translatedText']
    entity['blob_name'] = result 
    entity['timestamp'] = current_datetime
    entity['image_public_url'] = blob.public_url
    entity['joy'] = face_joy
    #entity['audio'] = audio_encode 

    # Save the new entity to Datastore.
    datastore_client.put(entity)

    # Redirect to the home page.
    return redirect('/img_scan.html')

def synthesize_text(text, doc):
    """Synthesizes speech from the input string of text."""
    client = texttospeech.TextToSpeechClient()

    input_text = texttospeech.types.SynthesisInput(text=text)

    # Note: the voice can also be specified by name.
    # Names of voices can be retrieved with client.list_voices().
    voice = texttospeech.types.VoiceSelectionParams(
        language_code='en-US',
        name='en-US-Standard-C',
        ssml_gender=texttospeech.enums.SsmlVoiceGender.FEMALE)

    audio_config = texttospeech.types.AudioConfig(
        audio_encoding=texttospeech.enums.AudioEncoding.MP3)

    response = client.synthesize_speech(input_text, voice, audio_config)
    if(doc=="img"):
        with open('output.mp3', 'wb') as out:
            out.write(response.audio_content)
    if(doc=="pdf"):
        with open('output2.mp3', 'wb') as out:
            out.write(response.audio_content)
    if(doc=="doc"):
        with open('output3.mp3', 'wb') as out:
            out.write(response.audio_content)

@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)

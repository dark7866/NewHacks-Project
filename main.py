import os
from datetime import datetime
import glob
from tika import parser
import io
from flask import Flask, redirect, render_template, request

from google.cloud import datastore
from google.cloud import storage
from google.cloud import vision
from google.cloud import texttospeech
from google.cloud import translate_v2 as translate


CLOUD_STORAGE_BUCKET = os.environ.get('CLOUD_STORAGE_BUCKET')


app = Flask(__name__)
counter = 0
@app.route('/')
def homepage():
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
    return render_template('homepage.html', image_entities=image_entities)


@app.route('/upload_photo', methods=['GET', 'POST'])
def upload_photo():
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
    entity['blob_name'] = result['translatedText'] 
    entity['timestamp'] = current_datetime
    entity['image_public_url'] = blob.public_url
    entity['joy'] = face_joy

    # Save the new entity to Datastore.
    datastore_client.put(entity)

    # Redirect to the home page.
    return redirect('/')

def pdf_to_text(name):

    rawText = parser.from_file(name)

    rawList = rawText['content']

    rawList = rawList.replace('\n\n', '\n')

    rawList=rawList.strip()

    return rawList

@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)

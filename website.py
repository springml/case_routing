from flask import Flask, request, render_template, jsonify
app = Flask(__name__, static_url_path='')
import os
import time
import argparse, datetime, re
import cPickle as pickle
from google.cloud import language, spanner, bigquery
import json
import googleapiclient.discovery
import collections
import predict

import random
# export GOOGLE_APPLICATION_CREDENTIALS=emailinsight-7f04f034fa9b.json
# export API_KEY=AIzaSyAY9T1IVheKFOCI9vdTp6-J77Rzk2XUiW0
# gcloud auth activate-service-account  --key-file emailinsight-7f04f034fa9b.json
# gcloud beta ml language analyze-entities --content="Michelangelo Caravaggio, Italian painter, is known for 'The Calling of Saint Matthew'."

GROUP_NAMES = ['Legal', 'Information', 'Emergencies', 'TechSupport', 'Utilities', 'Sales']
DATA_PATH = '/Users/Edrich/programming/CaseRoutingDemo/'
BAG_OF_WORDS_PATH = DATA_PATH + 'full_bags_3.pk'

spanner_client = spanner.Client()

instance = spanner_client.instance("caseroutingdemo")
database = instance.database("caserouting")

@app.route('/static/<path:path>')
def root():
	return app.send_static_file('index.html')

@app.route('/')
def index():
	'''
	Home page
	'''

	return render_template('index.html')

@app.route('/getCasesVSCategory', methods=['GET' , 'POST'])
def update_category():
	update_value('Category', new_category)
	return 

@app.route('/getCasesVSCategory', methods=['POST'])
def get_cat_data():
	data = {}
	dimensions, measures  = run_query("SELECT Category, count(*) FROM cases Group By Category;")
	data["categories"] = [dimensions, measures]
	return jsonify(data)

@app.route('/getCasesVSAssignee', methods=['POST'])
def get_assignee_data():
	data = {}
	dimensions, measures  = run_query("SELECT Assignee, count(*) FROM cases Group By Assignee;")
	data["assignees"] = [dimensions, measures]
	return jsonify(data)

@app.route('/getCasesVSRegion', methods=['POST'])
def get_region_data():
	data = {}
	dimensions, measures  = run_query("SELECT Region, count(*) FROM cases Group By Region;")
	data["regions"] = [dimensions, measures]
	return jsonify(data)

@app.route('/getCasesVSTime', methods=['POST'])
def get_time_data():
	data = {}
	dimensions, measures  = run_query("SELECT FORMAT_TIMESTAMP('%F', Timestamp) as Date, count(*) FROM cases Group By Date HAVING Date is not null Order By Date;")
	data["time"] = [dimensions, measures]
	return jsonify(data)

@app.route('/getAllData', methods=['POST'])
def get_all_data():
	data = {}
	results = run_table_query("SELECT * FROM cases;")
	data["allColumns"] = results
	return jsonify(data)


@app.route('/request')
def show_request():
	return render_template('request.html')

@app.route('/submit', methods=['POST'])
def run_pipeline():

	print "we made it"
	#retreiving results from UI
	regions = ["West", "South", "Midwest", "Northeast"]
	Case_Assignments = {"Legal": ["Charles Anderson", "Robert Heller", "Jane Jackson"],
						"Information": ["Ann Gitlin", "Harrison Davis", "Raj Kumar"],
						"Emergancies": ["Eduardo Sanchez", "Jack Lee", "Sarah Jefferson"],
						"TechSupport": ["Kris Hauser", "Sheryl Thomas", "Yash Patel"],
						"Utilities": ["Mike Camica", "Jose Lopez", "Greg Guniski"],
						"Sales": ["Taylor Traver", "Sam Goldberg", "Jen Kuecks"],
						"Region": ["West", "South", "Midwest", "Northeast"]
	}

	sample_request_subject = request.get_json().get('subject', '')
	sample_request_content = request.get_json().get('content', '')
	# Hemanth this is new: It's for the priority
	sample_request_priority = request.get_json().get('priority', '')

	sample_request_timestamp = datetime.datetime.now()

	sample_request_subject, sample_request_content = clean_text(sample_request_subject, sample_request_content)
	word_bags = unpack_word_bags(word_bags_path = BAG_OF_WORDS_PATH)
	words_groups = get_bag_of_word_counts(sample_request_subject, sample_request_content, word_bags, GROUP_NAMES)
	entity_count_person, entity_count_location, entity_count_organization, entity_count_event, entity_count_work_of_art, entity_count_consumer_good, sentiment_score = get_entity_counts_sentiment_score(sample_request_subject, sample_request_content)
	subject_length, subject_word_count, content_length, content_word_count, is_am, is_weekday = get_basic_quantitative_features(sample_request_subject, sample_request_content, sample_request_timestamp)

	#with open('instances.json') as f:
	#	JSON = json.load(f)
	json_to_submit = {'content_length':content_length,
					'content_word_count':content_word_count,
					'group1':words_groups[0][0],
					'group2':words_groups[1][0],
					'group3':words_groups[2][0],
					'group4':words_groups[3][0],
					'group5':words_groups[4][0],
					'group6':words_groups[5][0],
					'is_am':is_am,
					'is_weekday':is_weekday,
					'subject_length':subject_length,
					'subject_word_count':subject_word_count,
					'nlp_consumer_goods':entity_count_consumer_good,
					'nlp_events':entity_count_event,
					'nlp_locations':entity_count_location,
					'nlp_organizations':entity_count_organization,
					'nlp_persons':entity_count_person,
					'nlp_work_of_arts':entity_count_work_of_art,
					'sentiment_scores':sentiment_score
	}

	service = googleapiclient.discovery.build('ml', 'v1')
	PROJECT = 'emailinsight-1'
	MODEL = 'case_routing_model_v5'
	name = 'projects/{}/models/{}'.format(PROJECT, MODEL)
	response = service.projects().predict(
    	name=name,
    	body={'instances': [json_to_submit]}
	).execute()
	'''
	bigquery_client = bigquery.Client()
	dataset = bigquery_client.dataset('CaseRouting')
	table = dataset.table('Tickets')
	table.reload()
	'''




	sample_request_timestamp = sample_request_timestamp.strftime('%Y-%m-%d %H:%M:%S')
	ticket_id = ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for i in xrange(6))
	category = GROUP_NAMES[response['predictions'][0]['classes']]

	assignee = random.choice(Case_Assignments[category])
	region = random.choice(regions)


	with database.batch() as batch:
		batch.insert(
		table='cases',
		columns=('CaseID', 'Subject', 'Body', 'Category', 'Assignee', 'Region', 'Timestamp'),
		values=[
			(ticket_id, sample_request_subject, sample_request_content, category, assignee, region, datetime.datetime.now())])


	return "Thank you for your submission"

def run_query(query):
	data = database.execute_sql(query)
	dimensions = []
	measures = []
	for row in data:
		dimensions.append(row[0])
		measures.append(row[1])
	return dimensions, measures

def run_table_query(query):
	data = database.execute_sql(query)

	return [row for row in data]

def update_value(CaseID, Column, value):
	with database.batch() as batch:
    	batch.update(
        	table='cases',
        	columns=(
                'CaseID', Column),
        	values=[
            	(CaseID, value)])
    return 
def run_all_query(query):
	data = database.execute_sql(query)
	return data


def clean_text(message_subject, message_content):
	message_subject = re.sub('[^A-Za-z0-9.?!; ]+', ' ', message_subject)
	message_content = re.sub('[^A-Za-z0-9.?!; ]+', ' ', message_content)

	return message_subject, message_content

def insert_data(instance_id, database_id):
    """Inserts sample data into the given database.

    The database and table must already exist and can be created using
    `create_database`.
    """
    spanner_client = spanner.Client()
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)

    with database.batch() as batch:
        batch.insert(
            table='',
            columns=('SingerId', 'FirstName', 'LastName',),
            values=[
                (1, u'Marc', u'Richards'),
                (2, u'Catalina', u'Smith'),
                (3, u'Alice', u'Trentor'),
                (4, u'Lea', u'Martin'),
                (5, u'David', u'Lomond')])

        batch.insert(
            table='Albums',
            columns=('SingerId', 'AlbumId', 'AlbumTitle',),
            values=[
                (1, 1, u'Go, Go, Go'),
                (1, 2, u'Total Junk'),
                (2, 1, u'Green'),
                (2, 2, u'Forever Hold Your Peace'),
                (2, 3, u'Terrified')])

    print('Inserted data.')

def get_entity_counts_sentiment_score(message_subject, message_content):
	"""Extract entities using google NLP API

	Sentiment analysis inspects the given text and identifies the
	prevailing emotional opinion within the text, especially to
	determine a writer's attitude as positive, negative, or neutral.

	Entity analysis inspects the given text for known entities (Proper
	nouns such as public figures, landmarks, and so on. Common nouns
	such as restaurant, stadium, and so on.) and returns information
	about those entities.

	Args
	text: content of text to feed into API

	Returns:
	entity_count_person, entity_count_location, entity_count_organization,
	entity_count_event, entity_count_work_of_art, entity_count_consumer_good,
	sentiment_score
	"""

	text = message_subject + message_content

	client = language.Client()
	document = client.document_from_text(text)


	# Detects sentiment in the document.
	annotations = document.annotate_text(include_sentiment=True,
											include_syntax=False,
											include_entities=True)

	# get overal text sentiment score
	sentiment_score = annotations.sentiment.score

	# get total counts for each entity found in text
	PERSON = []
	LOCATION = []
	ORGANIZATION = []
	EVENT = []
	WORK_OF_ART = []
	CONSUMER_GOOD = []

	entities_found = []
	for e in annotations.entities:
		entities_found.append(e.entity_type)

	entity_count_person = len([i for i in entities_found if i == 'PERSON'])
	entity_count_location = len([i for i in entities_found if i == 'LOCATION'])
	entity_count_organization = len([i for i in entities_found if i == 'ORGANIZATION'])
	entity_count_event = len([i for i in entities_found if i == 'EVENT'])
	entity_count_work_of_art = len([i for i in entities_found if i == 'WORK_OF_ART'])
	entity_count_consumer_good = len([i for i in entities_found if i == 'CONSUMER_GOOD'])

	return entity_count_person, entity_count_location, entity_count_organization, entity_count_event, entity_count_work_of_art, entity_count_consumer_good, sentiment_score

def get_basic_quantitative_features(message_subject, message_content, message_time):
	"""


	Args


	Returns:

	"""
	subject_length = len(message_subject)
	subject_word_count = len(message_subject.split())
	content_length = len(message_content)
	content_word_count = len(message_content.split())
	dt = message_time
	is_am = 'no'
	if (dt.time() < datetime.time(12)): is_am = 'yes'
	is_weekday = 'no'
	if (dt.weekday() < 6): is_weekday = 'yes'
	return subject_length, subject_word_count, content_length, content_word_count, is_am, is_weekday

def get_bag_of_word_counts(message_subject, message_content, word_bags, departments):
	text = message_subject + message_content
	text = text.lower()
	# loop through all emails and count group words in each raw text
	words_groups = []
	for group_id in range(len(departments)):
		work_group = []
		top_words = word_bags[group_id]
		work_group.append(len([w for w in text.split() if w in set(top_words)]))
		words_groups.append(work_group)
	return words_groups

def unpack_word_bags(word_bags_path):
	"""

	Args:
	word_bags_path: full path and file name to pickle file holding words representing
	each routing groups


	Returns:

	"""

	with open(word_bags_path, 'rb') as handle:
		groups = pickle.load(handle)

	return groups

if __name__ == '__main__':
	port = int(os.environ.get("PORT", 8000))
	app.run(debug=True, host='0.0.0.0', port=port)

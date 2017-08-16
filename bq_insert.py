from google.cloud import bigquery, spanner, storage
import uuid
import datetime
import time, json
import argparse


def push_spanner_data(instance, database, spanner_bucket):
	'''
	Connects to Spanner and creates a csv file with all the data in Spanner. CSV file is then uploaded to a bucket in 
	Google Cloud storage.
	'''
	spanner_client = spanner.Client()

	instance = spanner_client.instance("caseroutingdemo")
	database = instance.database("caserouting")

	data = database.execute_sql("SELECT CaseID, Subject, Body, Category, Assignee, Region, Created_Date, Priority, Close_Date, CSAT, Channel, Sentiment, Status FROM CaseDetails;")
	columns = ['CaseID', 'Subject', 'Body', 'Category', 'Assignee', 'Region', 'Created_Date', 'Priority', 'Close_Date', 'CSAT', 'Channel', 'Sentiment', 'Status']

	with open('SpannerCaseDetails.json', 'w') as fp: 
		for row in data:
			results = dict(zip(columns, row))
			results["TimeToClose"] = (results["Close_Date"] - results["Created_Date"]).days
			results["Close_Date"] = results["Close_Date"].strftime('%Y-%m-%d %H:%M:%S')
			results["Created_Date"] = results["Created_Date"].strftime('%Y-%m-%d %H:%M:%S')
			json.dump(results, fp)
			fp.write('\n')
	upload_file(spanner_bucket, 'SpannerCaseDetails.json', 'SpannerCaseDetails.json')

def upload_file(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

def create_table(dataset, table_name):


	#Delete Old Table
	dataset.table(table_name).delete()
	
	table = dataset.table(table_name)
	table.schema = (
	bigquery.SchemaField('CaseID', 'STRING'),
	bigquery.SchemaField('Assignee', 'STRING'),
	bigquery.SchemaField('Body', 'STRING'),
	bigquery.SchemaField('Category', 'STRING'),
	bigquery.SchemaField('Channel', 'STRING'),
	bigquery.SchemaField('Close_Date', 'TIMESTAMP'),
	bigquery.SchemaField('Created_Date', 'TIMESTAMP'),
	bigquery.SchemaField('CSAT', 'FLOAT'),
	bigquery.SchemaField('Priority', 'STRING'),
	bigquery.SchemaField('Region', 'STRING'),
	bigquery.SchemaField('Sentiment', 'FLOAT'),
	bigquery.SchemaField('Status', 'STRING'),
	bigquery.SchemaField('Subject', 'STRING'),
	bigquery.SchemaField('TimeToClose', 'INTEGER'),
	)

	table.create()

def load_data_from_gcs(dataset_name, table_name, source):
	'''
	Loads data of Spanner Data files from google cloud storage and loads it into Big Query
	'''
	bigquery_client = bigquery.Client()
	dataset = bigquery_client.dataset(dataset_name)
	
	create_table(dataset, table_name)
	
	table = dataset.table(table_name)
	
	job_name = str(uuid.uuid4())

	job = bigquery_client.load_table_from_storage(
		job_name, table, source)

	job.source_format="NEWLINE_DELIMITED_JSON"

	job.begin()

	wait_for_job(job)

	print('Loaded {} rows into {}:{}.'.format(
		job.output_rows, dataset_name, table_name))

def wait_for_job(job):
	while True:
		job.reload()
		if job.state == 'DONE':
			if job.error_result:
				raise RuntimeError(job.errors)
			return
		time.sleep(.1)

if __name__ == '__main__':
	
	parser = argparse.ArgumentParser(
        description='Arguments for running web server')
    parser.add_argument(
        '--Spanner_Bucket', required=True, help='gcs bucket with spanner files')
    args = parser.parse_args()

	push_spanner_data('caseroutingdemo', 'caserouting', args.Spanner_Bucket)
	load_data_from_gcs('CaseRouting', 'CaseDetails', 'gs://' +  args.Spanner_Bucket + '/SpannerCaseDetails.json')



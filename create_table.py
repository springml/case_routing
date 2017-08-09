from google.cloud import bigquery



def create_table_dataset(dataset_name, table_name, project=None):
	bigquery_client = bigquery.Client(project=project)

	dataset = bigquery_client.dataset(dataset_name)

	#Delete Old Table
	#dataset.table(table_name).delete()
	
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
	
if __name__ == '__main__':
	create_table_dataset('CaseRouting', 'CaseDetails', 'emailinsight-1')
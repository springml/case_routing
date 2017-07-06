from google.cloud import bigquery

def create_table_dataset(dataset_name, table_name, project=None):
	bigquery_client = bigquery.Client(project=project)

	# Prepares the new dataset
	dataset = bigquery_client.dataset(dataset_name)
	# Creates the new dataset
	dataset.create()
	
	table = dataset.table(table_name)
	table.schema = (
	bigquery.SchemaField('TicketID', 'STRING'),
	bigquery.SchemaField('TicketSubject', 'STRING'),
	bigquery.SchemaField('TicketBody', 'STRING'),
	bigquery.SchemaField('Category', 'STRING'),
	bigquery.SchemaField('Date', 'DATETIME')
	)

	table.create()
	
if __name__ == '__main__':
	create_table_dataset('CaseRouting', 'Tickets', 'emailinsight-1')
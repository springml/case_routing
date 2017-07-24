
def clean_text(message_subject, message_content):
    message_subject = re.sub('[^A-Za-z0-9.?!; ]+', ' ', message_subject)
    message_content = re.sub('[^A-Za-z0-9.?!; ]+', ' ', message_content)

    return message_subject, message_content

def get_bag_of_word_counts(message_subject, message_content, word_bags, departments):
 
    text = message_subject + message_content
    text = text.lower()
    # loop through all emails and count group words in each raw text
    words_groups = []
    for group_id in range(len(departments)):
        work_group = []
        print('Working bag number:', departments[group_id])
        top_words = word_bags[group_id]
        # work_group.append(len(set(top_words) & text.split()))
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
    import cPickle as pickle
    with open(word_bags_path, 'rb') as handle:
        groups = pickle.load(handle)
 
    return groups
 

# load csv's 
import os
os.chdir("/Users/manuel/Documents/SpringML/case-routing/final_scripts")

import pandas as pd
case_traffic = pd.read_csv('simulated_case_traffic.csv')

import argparse, datetime, re
from google.cloud import language # pip install --upgrade google-cloud-language

GROUP_NAMES = ['legal', 'communications', 'security', 'support', 'energy_desk', 'sales']
DATA_PATH = '/Users/manuel/Documents/SpringML/case-routing/final_scripts/data/'
BAG_OF_WORDS_PATH = DATA_PATH + 'full_bags_3.pk'


from sklearn.utils import shuffle
case_traffic = shuffle(case_traffic)

SEND_CASE_EVERY_X_SECONDS = 2 # email sent every x seconds
import time
for index, row in case_traffic.iterrows():
	sample_request_subject = row['subject']
	sample_request_content = row['content']
	sample_request_subject, sample_request_content = clean_text(sample_request_subject, sample_request_content)
	word_bags = unpack_word_bags(word_bags_path = BAG_OF_WORDS_PATH)
	words_groups = get_bag_of_word_counts(sample_request_subject, sample_request_content, word_bags, GROUP_NAMES)
	...
	time.sleep(SEND_CASE_EVERY_X_SECONDS)
	    
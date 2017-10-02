from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf
import collections
import os
import random
import numpy as np
from tqdm import tqdm
import sys, email
import pandas as pd 
import math

#########################################################
# Load Enron dataset
#########################################################

# source https://www.kaggle.com/zichen/explore-enron
ENRON_EMAIL_DATASET_PATH = 'enron-dataset/emails.csv'

# load enron dataset
import pandas as pd 
emails_df = pd.read_csv(ENRON_EMAIL_DATASET_PATH)
print(emails_df.shape)
emails_df.head()


#########################################################
# Sort out required email features: date, subject, content
#########################################################


## Helper functions
def get_text_from_email(msg):
    '''To get the content from email objects'''
    parts = []
    for part in msg.walk():
        if part.get_content_type() == 'text/plain':
            parts.append( part.get_payload() )
    return ''.join(parts)

import email
# Parse the emails into a list email objects
messages = list(map(email.message_from_string, emails_df['message']))
emails_df.drop('message', axis=1, inplace=True)
# Get fields from parsed email objects
keys = messages[0].keys()
for key in keys:
    emails_df[key] = [doc[key] for doc in messages]
# Parse content from emails
emails_df['Content'] = list(map(get_text_from_email, messages))

# keep only Subject and Content for this exercise
emails_df = emails_df[['Date','Subject','Content']]

#########################################################
# change wor2vec model to work with Enron emails
#########################################################

 
# point it to our Enron data set
emails_sample_df = emails_df.copy()

import string, re
# clean up subject line
emails_sample_df['Subject'] = emails_sample_df['Subject'].str.lower()
emails_sample_df['Subject'] = emails_sample_df['Subject'].str.replace(r'[^a-z]', ' ')  
emails_sample_df['Subject'] = emails_sample_df['Subject'].str.replace(r'\s+', ' ')  

# clean up content line
emails_sample_df['Content'] = emails_sample_df['Content'].str.lower()
emails_sample_df['Content'] = emails_sample_df['Content'].str.replace(r'[^a-z]', ' ')  
emails_sample_df['Content'] = emails_sample_df['Content'].str.replace(r'\s+', ' ')  

# create sentence list 
emails_text = (emails_sample_df["Subject"] + ". " + emails_sample_df["Content"]).tolist()

sentences = ' '.join(emails_text)
words = sentences.split()

print('Data size', len(words))
 

# get unique words and map to glove set
print('Unique word count', len(set(words))) 
 

# drop rare words
vocabulary_size = 50000

def build_dataset(words):
  count = [['UNK', -1]]
  count.extend(collections.Counter(words).most_common(vocabulary_size - 1))
  dictionary = dict()
  for word, _ in count:
    dictionary[word] = len(dictionary)
  data = list()
  unk_count = 0
  for word in tqdm(words):
    if word in dictionary:
      index = dictionary[word]
    else:
      index = 0  # dictionary['UNK']
      unk_count += 1
    data.append(index)
  count[0][1] = unk_count
  reverse_dictionary = dict(zip(dictionary.values(), dictionary.keys()))
  return data, count, dictionary, reverse_dictionary

data, count, dictionary, reverse_dictionary = build_dataset(words)

del words  
print('Most common words (+UNK)', count[:5])
print('Sample data', data[:10], [reverse_dictionary[i] for i in data[:10]])


####################################################################
# find matches with glove 
####################################################################
# http://nlp.stanford.edu/data/glove.840B.300d.zip
GLOVE_DATASET_PATH = 'glove-dataset/glove.840B.300d.txt'

from tqdm import tqdm
import string
embeddings_index = {}
f = open(GLOVE_DATASET_PATH)
word_counter = 0
for line in tqdm(f):
  values = line.split()
  word = values[0]
  if word in dictionary:
    coefs = np.asarray(values[1:], dtype='float32')
    embeddings_index[word] = coefs
  word_counter += 1
f.close()

print('Found %s word vectors matching enron data set.' % len(embeddings_index))
print('Total words in GloVe data set: %s' % word_counter)



#########################################################
# Check out some clusters
#########################################################

# create a dataframe using the embedded vectors and attach the key word as row header
import pandas as pd
enrond_dataframe = pd.DataFrame(embeddings_index)
enrond_dataframe = pd.DataFrame.transpose(enrond_dataframe)
 
# See what it learns and look at clusters to pull out major themes in the data
CLUSTER_SIZE = 300 
# cluster vector and investigate top groups
from sklearn.cluster import KMeans
kmeans = KMeans(n_clusters=CLUSTER_SIZE)
cluster_make = kmeans.fit_predict(enrond_dataframe)

labels = kmeans.predict(enrond_dataframe)
import collections
cluster_frequency = collections.Counter(labels)
print(cluster_frequency)
cluster_frequency.most_common()

clusters = {}
n = 0
for item in labels:
    if item in clusters:
        clusters[item].append(list(enrond_dataframe.index)[n])
    else:
        clusters[item] = [list(enrond_dataframe.index)[n]]
    n +=1

for k,v in cluster_frequency.most_common(100):
  print('\n\n')
  print('Cluster:', k)
  print (' '.join(clusters[k]))


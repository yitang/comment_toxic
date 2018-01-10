# encoding=utf-8
import math
from collections import defaultdict
from nltk.corpus import stopwords
import nltk
import pandas as pd
import pickle

import config

maxlen = config.MAX_TEXT_LENGTH # max number of words in a comment to use

porter = nltk.PorterStemmer()
wnl= nltk.WordNetLemmatizer()
toxic_list = ['toxic', 'severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate']
word_dict={}
i = 0
badwords = config.badwords
stop_words = config.stop_words
print(len(badwords))

N = 0
all_word = 0
all_class = 0
outf = open("./train_corps.txt",'w',encoding='utf-8')
train = pd.read_csv(config.TRAIN_VALID_FILE)
train_len=0
for index, row in train.iterrows():
    line = row['comment_text']
    tokens = nltk.word_tokenize(line)
    len=0
    for t in tokens:
        word=t
        # word = wnl.lemmatize(t)
        # word = porter.stem(word)
        word = word.lower()
        word = word.replace('\t', '')
        word = word.replace('\n', '')
        if word in stop_words:
            continue
        if word in badwords:
            word = badwords[word]
        if  word not in word_dict:
            word_dict[word]=i
            i+=1
        outf.write(word)
        outf.write(' ')
        len+=1
        if len> maxlen :
            break
    outf.write("\n")
    train_len+=1
outf.close()
print('train_len',train_len)


outf = open("./test_corps.txt",'w',encoding='utf-8')
train = pd.read_csv(config.TEST_DATA_FILE)
train=train["comment_text"].fillna("MISSINGVALUE").values
test_len=0
for line in train:
    tokens = nltk.word_tokenize(line)
    for t in tokens:
        word = t
        # word=wnl.lemmatize(t)
        # word = porter.stem(word)
        word = word.lower()
        word = word.replace('\t', '')
        word = word.replace('\n', '')
        if word in stop_words:
            continue
        if word in badwords:
            word = badwords[word]
        if  word not in word_dict:
            word_dict[word]=i
            i+=1
        outf.write(word)
        outf.write(' ')
    outf.write("\n")
    test_len+=1
outf.close()
print('test_len',test_len)
#
# with open('word_dict.pkl3', 'wb') as f:
#      pickle.dump(word_dict, f)
'''
The code is tested on Keras 2.0.0 using Theano backend, and Python 3.5
referrence Code:https://github.com/keras-team/keras/blob/master/examples/imdb_cnn_lstm.py
'''

import re
import h5py
import numpy as np
import pandas as pd
# from keras import initializations
from keras.callbacks import EarlyStopping, ModelCheckpoint
from keras.layers import Dense, Input, Embedding, Dropout, RepeatVector, Bidirectional, LSTM, Masking
from keras.layers import recurrent
from keras.models import Model
from keras.preprocessing.sequence import pad_sequences
from keras.preprocessing.text import Tokenizer
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer
import os
import config

path = '../data/'
EMBEDDING_FILE = config.GLOVE_EMBEDDING_FILE
TRAIN_DATA_FILE = config.TRAIN_VALID_FILE
TEST_DATA_FILE = config.TEST_DATA_FILE

MAX_SEQUENCE_LENGTH = 150
MAX_NB_WORDS = 100000
EMBEDDING_DIM = 300
VALIDATION_SPLIT = 0.1
SPLIT=config.SPLIT
num_lstm = 300
num_dense = 256
rate_drop_lstm = 0.25
rate_drop_dense = 0.25

act = 'relu'

# Regex to remove all Non-Alpha Numeric and space
special_character_removal = re.compile(r'[^a-z\d ]', re.IGNORECASE)
# regex to replace all numerics
replace_numbers = re.compile(r'\d+', re.IGNORECASE)

########################################
## index word vectors
########################################

kernel_name="blstm_seq1.0"
perm_path=kernel_name+"perm.npz"
embedding_matrix_path=kernel_name+"_embedding_layer.npz"

########################################
## process texts in datasets
########################################
TRAIN_HDF5='./train_hdf5.h5'
def dump_X_Y_train_test(train,test,y):
    outh5file = h5py.File(TRAIN_HDF5, 'w')
    test_token = outh5file.create_dataset('test_token', data=test)
    train_token = outh5file.create_dataset('train_token', data=train)
    train_label = outh5file.create_dataset(name='train_label', data=y)
    outh5file.close()
def load_tran_test_y():
    outh5file = h5py.File(TRAIN_HDF5, 'r')
    train=outh5file['train_token']
    test=outh5file['test_token']
    y=outh5file['train_label']
    return train,test,y

def get_X_train_X_test(train_df, test_df):
    print('Processing text dataset')
    list_sentences_train = train_df["comment_text"].fillna("NA").values
    list_classes = ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]
    y = train_df[list_classes].values
    list_sentences_test = test_df["comment_text"].fillna("NA").values
    comments = []
    for text in list_sentences_train:
        comments.append(text_to_wordlist(text))
    test_comments = []
    for text in list_sentences_test:
        test_comments.append(text_to_wordlist(text))

    tokenizer = Tokenizer(num_words=MAX_NB_WORDS)
    tokenizer.fit_on_texts(comments + test_comments)

    sequences = tokenizer.texts_to_sequences(comments)
    test_sequences = tokenizer.texts_to_sequences(test_comments)

    word_index = tokenizer.word_index
    print('Found %s unique tokens' % len(word_index))

    data = pad_sequences(sequences, maxlen=MAX_SEQUENCE_LENGTH)
    print('Shape of data tensor:', data.shape)
    print('Shape of label tensor:', y.shape)

    test_data = pad_sequences(test_sequences, maxlen=MAX_SEQUENCE_LENGTH)
    print('Shape of test_data tensor:', test_data.shape)
    return data,test_data,tokenizer.word_index

def text_to_wordlist(text, remove_stopwords=False, stem_words=False):
    # Clean the text, with the option to remove stopwords and to stem words.

    # Convert words to lower case and split them


    text = text.lower().split()

    # Optionally, remove stop words
    if remove_stopwords:
        stops = set(stopwords.words("english"))
        text = [w for w in text if not w in stops]

    text = " ".join(text)

    # Remove Special Characters
    text = special_character_removal.sub('', text)

    # Replace Numbers
    text = replace_numbers.sub('n', text)

    # Optionally, shorten words to their stems
    if stem_words:
        text = text.split()
        stemmer = SnowballStemmer('english')
        stemmed_words = [stemmer.stem(word) for word in text]
        text = " ".join(stemmed_words)

    # Return a list of words
    return (text)

"""
prepare embeddings
"""
def get_embedding_matrix(word_index):
    #    Glove Vectors
    print('Indexing word vectors')
    embeddings_index = {}
    f = open(EMBEDDING_FILE)
    for line in f:
        values = line.split()
        word = ' '.join(values[:-300])
        coefs = np.asarray(values[-300:], dtype='float32')
        embeddings_index[word] = coefs
    f.close()

    print('Total %s word vectors.' % len(embeddings_index))
    print('Preparing embedding matrix')
    all_embs = np.stack(embeddings_index.values())
    print(all_embs.shape)
    emb_mean, emb_std = all_embs.mean(), all_embs.std()
    nb_words = min(MAX_NB_WORDS, len(word_index))
    embedding_matrix = np.random.normal(loc=emb_mean, scale=emb_std, size=(nb_words, EMBEDDING_DIM))
    # embedding_matrix = np.zeros((nb_words, EMBEDDING_DIM))
    for word, i in word_index.items():
        if i >= MAX_NB_WORDS:
            continue
        embedding_vector = embeddings_index.get(word)
        if embedding_vector is not None:
            # words not found in embedding index will be all-zeros.
            embedding_matrix[i] = embedding_vector

    print('Null word embeddings: %d' % np.sum(np.sum(embedding_matrix, axis=1) == 0))
    return embedding_matrix

"""
 define the model structure

 """
# Convolution
kernel_size = 5
filters = 64
pool_size = 4

# LSTM
lstm_output_size = 70

def get_model(word_index):
    nb_words = min(MAX_NB_WORDS, len(word_index))
    if os.path.exists(embedding_matrix_path):
        embedding_matrix = np.load(embedding_matrix_path)["arr_0"]
    else:
        embedding_matrix = get_embedding_matrix(word_index)
    # embedding_matrix,nb_words=get_embedding_matrix(word_index)
    nb_words = min(MAX_NB_WORDS, len(word_index))
    input1 = Input(shape=(MAX_SEQUENCE_LENGTH,), dtype='int32')
    embedding_layer = Embedding(nb_words,
                                EMBEDDING_DIM,
                                input_length=MAX_SEQUENCE_LENGTH,
                                weights=[embedding_matrix],
                                trainable=True)
    x=embedding_layer(input1)
    x = Masking(mask_value=0.)(x)
    x = Bidirectional(LSTM(64, return_sequences=True), merge_mode='sum')(x)
    x = Bidirectional(LSTM(32), merge_mode='sum')(x)
    x = Dropout(rate_drop_dense)(x)
    out = Dense(6, activation='sigmoid')(x)
    model = Model(inputs=input1, outputs=out)
    model.compile(loss='binary_crossentropy', optimizer='rmsprop', metrics=['mse'])
    model.summary()
    return model
"""
train the model
"""
def train_fit_predict(model, data, test_data, y):
    ########################################
    ## sample train/validation data
    ########################################
    #np.random.seed(1234)
    # perm = np.random.permutation(len(data))
    # np.savez(perm_path, perm)
    # idx_train = perm[:int(len(data) * (1 - VALIDATION_SPLIT))]
    # idx_val = perm[int(len(data) * (1 - VALIDATION_SPLIT)):]
    #
    # data_train = data[idx_train]
    # labels_train = y[idx_train]
    # print(data_train.shape, labels_train.shape)
    #
    # data_val = data[idx_val]
    # labels_val = y[idx_val]
    # print(data_val.shape, labels_val.shape)
    data_val = X_train[0:SPLIT]
    labels_val = y[0:SPLIT]
    data_train = X_train[SPLIT:]
    labels_train = y[SPLIT:]
    STAMP = kernel_name+'_%.2f_%.2f' % (rate_drop_lstm, rate_drop_dense)
    print(STAMP)
    early_stopping = EarlyStopping(monitor='val_loss', patience=5)
    bst_model_path = STAMP + '.h5'
    model_checkpoint = ModelCheckpoint(bst_model_path, save_best_only=True,verbose=1,  save_weights_only=True)

    hist = model.fit(data_train, labels_train,
                     validation_data=(data_val, labels_val),
                     epochs=50, batch_size=256, shuffle=True,
                     callbacks=[early_stopping, model_checkpoint])

    model.load_weights(bst_model_path)
    bst_val_score = min(hist.history['val_loss'])
    print("bst_val_score",bst_val_score)
    ## make the submission
    print('Start making the submission before fine-tuning')
    y_test = model.predict(test_data, batch_size=1024, verbose=1)
    return  y_test,bst_val_score,STAMP

def submit(y_test,bst_val_score,STAMP):
    sample_submission = pd.read_csv(config.path+"sample_submission.csv")
    sample_submission[config.CLASSES_LIST] = y_test
    sample_submission.to_csv('%.4f_' % (bst_val_score) + STAMP + '.csv', index=False)

def get_Y(train):
    return train[config.CLASSES_LIST].values

train = pd.read_csv(TRAIN_DATA_FILE)
train=train[:95851]
test = pd.read_csv(TEST_DATA_FILE)
X_train, X_test,word_index = get_X_train_X_test(train, test)
y=get_Y(train)
# dump_X_Y_train_test(X_train.X_test,y)
model=get_model(word_index)
y_test,bst_val_score,STAMP = train_fit_predict(model, X_train, X_test, y)
submit(y_test,bst_val_score,STAMP)
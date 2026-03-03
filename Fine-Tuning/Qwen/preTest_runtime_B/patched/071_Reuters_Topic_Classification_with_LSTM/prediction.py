
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import pandas as pd
from keras.models import Sequential
from keras.layers import Embedding, LSTM, Dense
from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences

# Load the Reuters dataset
df = pd.read_csv('reuters.csv')

# Preprocess the data
tokenizer = Tokenizer(num_words=5000)
tokenizer.fit_on_texts(df['text'])
sequences = tokenizer.texts_to_sequences(df['text'])
word_index = tokenizer.word_index
data = pad_sequences(sequences, maxlen=100)

# Split the data into training and testing sets
train_data = data[:8000]
train_labels = df['topic'][:8000]
test_data = data[8000:]
test_labels = df['topic'][8000:]

# Define the model architecture
model = Sequential()
model.add(Embedding(input_dim=5000, output_dim=100, input_length=100))
model.add(LSTM(units=100, return_sequences=True))
model.add(LSTM(units=100))
model.add(Dense(units=46, activation='softmax'))

# Compile the model
model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

# Train the model
model.fit(train_data, train_labels, epochs=5, batch_size=32)

# Evaluate the model on the test set
test_loss, test_acc = model.evaluate(test_data, test_labels)
print('Test accuracy:', test_acc)
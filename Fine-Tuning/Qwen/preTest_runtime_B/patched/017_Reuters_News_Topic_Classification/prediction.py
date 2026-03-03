
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from keras.models import Sequential
from keras.layers import Dense, Embedding, LSTM
from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences

# Load the Reuters dataset
df = pd.read_csv('reuters.csv')

# Preprocess the data
X = df['text'].values
y = df['topic'].values

# Encode the labels
le = LabelEncoder()
y = le.fit_transform(y)

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Tokenize the text data
tokenizer = Tokenizer(num_words=5000)
tokenizer.fit_on_texts(X_train)
X_train = tokenizer.texts_to_sequences(X_train)
X_test = tokenizer.texts_to_sequences(X_test)

# Pad the sequences to a fixed length
max_length = 100
X_train = pad_sequences(X_train, maxlen=max_length)
X_test = pad_sequences(X_test, maxlen=max_length)

# Define the model architecture
model = Sequential()
model.add(Embedding(input_dim=5000, output_dim=128, input_length=max_length))
model.add(LSTM(128))
model.add(Dense(64, activation='relu'))
model.add(Dense(46, activation='softmax'))

# Compile the model
model.compile(loss='sparse_categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

# Train the model
model.fit(X_train, y_train, epochs=5, batch_size=32, validation_data=(X_test, y_test))

# Evaluate the model
loss, accuracy = model.evaluate(X_test, y_test)
print('Test loss:', loss)
print('Test accuracy:', accuracy)

# Make predictions on new data
new_data = ['This is a sample news article about politics.', 'This is a sample news article about sports.']
new_data = tokenizer.texts_to_sequences(new_data)
new_data = pad_sequences(new_data, maxlen=max_length)
predictions = model.predict(new_data)
predicted_labels = le.inverse_transform(np.argmax(predictions, axis=1))
print('Predicted labels:', predicted_labels)
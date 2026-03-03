import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import VotingClassifier
from sklearn.metrics import accuracy_score

# Load the MNIST dataset
mnist_data = pd.read_csv('mnist.csv')

# Split the data into features and labels
X = mnist_data.drop('label', axis=1)
y = mnist_data['label']

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Scale the data
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# Create the individual classifiers
lr = LogisticRegression(max_iter=1000)
svm = SVC(kernel='linear', C=1)
dt = DecisionTreeClassifier()

# Create the ensemble classifier
ensemble = VotingClassifier(estimators=[('lr', lr), ('svm', svm), ('dt', dt)], voting='hard')

# Train the ensemble classifier
ensemble.fit(X_train, y_train)

# Make predictions on the test set
ensemble_pred = ensemble.predict(X_test)

# Calculate the accuracy of the ensemble classifier
ensemble_accuracy = accuracy_score(y_test, ensemble_pred)
print('Ensemble accuracy:', ensemble_accuracy)

# Make predictions on the test set using the individual classifiers
lr_pred = lr.predict(X_test)
svm_pred = svm.predict(X_test)
dt_pred = dt.predict(X_test)

# Calculate the accuracy of the individual classifiers
lr_accuracy = accuracy_score(y_test, lr_pred)
svm_accuracy = accuracy_score(y_test, svm_pred)
dt_accuracy = accuracy_score(y_test, dt_pred)
print('LR accuracy:', lr_accuracy)
print('SVM accuracy:', svm_accuracy)
print('DT accuracy:', dt_accuracy)

# Make predictions on the test set using the CNN
cnn_pred = cnn.predict(X_test)

# Calculate the accuracy of the CNN
cnn_accuracy = accuracy_score(y_test, cnn_pred)
print('CNN accuracy:', cnn_accuracy)
import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA

# Load the data
data = pd.read_csv('penguins.csv')

# Convert the 'date' column to datetime format
data['date'] = pd.to_datetime(data['date'])

# Set the 'date' column as the index
data.set_index('date', inplace=True)

# Resample the data to monthly frequency
data = data.resample('M').mean()

# Fit an ARIMA model to the data
model = ARIMA(data['penguin_count'], order=(1, 1, 1))
model_fit = model.fit()

# Make predictions for the next 12 months
n_months = 12
time_index = pd.date_range(start='2019-01-01', periods=n_months, freq='ME')
predictions = model_fit.predict(start=len(data), end=len(data) + n_months - 1, dynamic=False)

# Print the predictions
print(predictions)
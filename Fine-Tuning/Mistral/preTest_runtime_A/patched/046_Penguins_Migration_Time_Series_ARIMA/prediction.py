
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.arima.model import ARIMA
import warnings
warnings.filterwarnings('ignore')

# Set random seed for reproducibility
np.random.seed(42)

# Generate synthetic monthly penguin sighting counts
# Create a time series with trend, seasonality, and noise
n_months = 60  # 5 years of monthly data
time_index = pd.date_range(start='2019-01-01', periods=n_months, freq='M')

# Create trend component
trend = np.linspace(100, 150, n_months)

# Create seasonal component (annual cycle with 12-month period)
seasonality = 30 * np.sin(2 * np.pi * np.arange(n_months) / 12)

# Add random noise
noise = np.random.normal(0, 10, n_months)

# Combine components to create synthetic penguin sighting counts
penguin_counts = trend + seasonality + noise
penguin_counts = np.maximum(penguin_counts, 0)  # Ensure non-negative counts

# Create pandas Series
ts_data = pd.Series(penguin_counts, index=time_index, name='Penguin Sightings')

print("Synthetic Penguin Sighting Time Series (first 12 months):")
print(ts_data.head(12))
print(f"\nTotal observations: {len(ts_data)}")

# Fit ARIMA model
# Using ARIMA(1,1,1) as a reasonable starting point for this synthetic data
# p=1 (autoregressive order), d=1 (differencing order), q=1 (moving average order)
model = ARIMA(ts_data, order=(1, 1, 1))
model_fit = model.fit()

print("\nARIMA Model Summary:")
print(model_fit.summary())

# Forecast the next 6 months
forecast_steps = 6
forecast_result = model_fit.forecast(steps=forecast_steps)

# Get forecast with confidence intervals
forecast_df = model_fit.get_forecast(steps=forecast_steps)
forecast_mean = forecast_df.predicted_mean
forecast_ci = forecast_df.conf_int()  # Corrected: alpha=0.05 is default for 95% CI

# Create forecast index
forecast_index = pd.date_range(start=ts_data.index[-1] + pd.DateOffset(months=1),
                            periods=forecast_steps, freq='M')

print("\nForecast for next 6 months:")
for i, date in enumerate(forecast_index):
    print(f"{date.strftime('%Y-%m')}: {forecast_mean.iloc[i]:.2f} "
          f"(95% CI: [{forecast_ci.iloc[i, 0]:.2f}, {forecast_ci.iloc[i, 1]:.2f}])")

# Plot observed versus forecasted values with confidence intervals
plt.figure(figsize=(14, 6))

# Plot observed data
plt.plot(ts_data.index, ts_data.values, label='Observed', color='blue', linewidth=2)

# Plot forecasted values
plt.plot(forecast_index, forecast_mean.values, label='Forecast',
         color='red', linewidth=2, linestyle='--')

# Plot confidence intervals
plt.fill_between(forecast_index,
                 forecast_ci.iloc[:, 0].values,
                 forecast_ci.iloc[:, 1].values,
                 color='red', alpha=0.2, label='95% Confidence Interval')

# Add vertical line to separate observed and forecast
plt.axvline(x=ts_data.index[-1], color='gray', linestyle=':',
            linewidth=1.5, label='Forecast Start')

plt.xlabel('Date', fontsize=12)
plt.ylabel('Penguin Sightings', fontsize=12)
plt.title('Penguin Migration Time Series: ARIMA Forecast', fontsize=14, fontweight='bold')
plt.legend(loc='best', fontsize=10)
plt.grid(True, alpha=0.3)
plt.tight_layout()
print('[FAST_EVAL] plt.show() skipped')

# Additional plot: Residuals diagnostics
fig, axes = plt.subplots(2, 2, figsize=(12, 8))

# Residuals over time
residuals = model_fit.resid
axes[0, 0].plot(ts_data.index, residuals)
axes[0, 0].axhline(y=0, color='r', linestyle='--')
axes[0, 0].set_title('Residuals over Time')
axes[0, 0].set_xlabel('Date')
axes[0, 0].set_ylabel('Residuals')
axes[0, 0].grid(True, alpha=0.3)

# Histogram of residuals
axes[0, 1].hist(residuals, bins=20, edgecolor='black', alpha=0.7)
axes[0, 1].set_title('Histogram of Residuals')
axes[0, 1].set_xlabel('Residuals')
axes[0, 1].set_ylabel('Frequency')
axes[0, 1].grid(True, alpha=0.3)

# ACF of residuals
from statsmodels.graphics.tsaplots import plot_acf
plot_acf(residuals, lags=20, ax=axes[1, 0])
axes[1, 0].set_title('ACF of Residuals')

# Q-Q plot
from scipy import stats
stats.probplot(residuals, dist="norm", plot=axes[1, 1])
axes[1, 1].set_title('Q-Q Plot')
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
print('[FAST_EVAL] plt.show() skipped')

print("\nModel diagnostics completed.")
print(f"Mean Absolute Error (in-sample): {np.mean(np.abs(residuals)):.2f}")
print(f"Root Mean Squared Error (in-sample): {np.sqrt(np.mean(residuals**2)):.2f}")
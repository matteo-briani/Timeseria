# Setup logging
from timeseria import logger
logger.setup(level='INFO')

# Load storages
from timeseria import storages

# Set sataset path to Timeria test CSV data
DATASET_PATH = '/'.join(storages.__file__.split('/')[0:-1]) + '/tests/test_data/csv/'

# Create a CSV storage pointing to out dataset
csv_storage = storages.CSVFileStorage(DATASET_PATH + 'temperature_winter.csv')

print('Loading data...')
# Get the time series out from the CSV file storage 
temperature_timeseries = csv_storage.get()
print('Done, now resampling...')
resampled_temperature_timeseries = temperature_timeseries.resample('10m')

print('Done.')
print(resampled_temperature_timeseries)

from timeseria.models.forecasters import PeriodicAverageForecaster
pavg_forecaster = PeriodicAverageForecaster()

print('Cross validating...')
from timeseria import time
start_t = time.now_s()
results = pavg_forecaster.cross_validate(resampled_temperature_timeseries[0:1000], rounds=3)
end_t = time.now_s()

print(results)

print('CROSS VALIDATION TIME: {}'.format(end_t-start_t))
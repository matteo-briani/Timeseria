# -*- coding: utf-8 -*-
"""Data reconstructions models."""

import copy
import statistics
from ..utilities import detect_periodicity, _get_periodicity_index, _set_from_t_and_to_t, _item_is_in_range, mean_absolute_percentage_error
from ..time import dt_from_s
from sklearn.metrics import mean_absolute_error, mean_squared_error
from ..units import TimeUnit
from pandas import DataFrame
from math import sqrt
from ..datastructures import TimeSeries
from .base import Model, _ProphetModel
from datetime import datetime

# Setup logging
import logging
logger = logging.getLogger(__name__)

# Suppress TensorFlow warnings as default behavior
try:
    import tensorflow as tf
    tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)
except (ImportError,AttributeError):
    pass


#=====================================
#  Generic Reconstructor
#=====================================

class Reconstructor(Model):
    """A generic series reconstruction model. This class of models work on reconstructing missing data,
    or in other words to fill gaps. Gaps need a “next” element after their end to be defined, which
    can bring much more information to the model with respect to a forecasting task.
    
    Args:
        path (str): a path from which to load a saved model. Will override all other init settings.
    """
    
    def predict(self, series, *args, **kwargs):
        """Disabled. Reconstructors can be used only with the ``apply()`` method."""
        raise NotImplementedError('Reconstructors can be used only with the apply() method') from None
 
    def _predict(self, series, *args, **kwargs):
        raise NotImplementedError('Reconstructors can be used only with the apply() method.') from None

    def _apply(self, series, remove_data_loss=False, data_loss_threshold=1, inplace=False):

        logger.debug('Using data_loss_threshold="%s"', data_loss_threshold)

        # TODO: understand if we want the apply from/to behavior. For now it is disabled
        # (add from_t=None, to_t=None, from_dt=None, to_dt=None in the function call above)
        # from_t, to_t = _set_from_t_and_to_t(from_dt, to_dt, from_t, to_t)
        # Maybe also add a series.mark=[from_dt, to_dt]
         
        from_t = None
        to_t   = None
        
        if not inplace:
            series = series.duplicate()

        if len(series.data_labels()) > 1:
            raise NotImplementedError('Multivariate time series are not yet supported')

        for data_label in series.data_labels():
            
            gap_started = None
            
            for i, item in enumerate(series):
                
                # Skip if before from_t/dt of after to_t/dt
                if from_t is not None and series[i].t < from_t:
                    continue
                try:
                    # Handle slots
                    if to_t is not None and series[i].end.t > to_t:
                        break
                except AttributeError:
                    # Handle points
                    if to_t is not None and series[i].t > to_t:
                        break                

                if item.data_loss is not None and item.data_loss >= data_loss_threshold:
                    # This is the beginning of an area we want to reconstruct according to the data_loss_threshold
                    if gap_started is None:
                        gap_started = i
                else:
                    
                    if gap_started is not None:
                    
                        # Reconstruct for this gap
                        self._reconstruct(series, from_index=gap_started, to_index=i, data_label=data_label)
                        gap_started = None
                    
                    item.data_indexes['data_reconstructed'] = 0
                    
                if remove_data_loss:
                    item.data_indexes.pop('data_loss', None)
            
            # Reconstruct the last gap as well if left "open"
            if gap_started is not None:
                self._reconstruct(series, from_index=gap_started, to_index=i+1, data_label=data_label)

        if not inplace:
            return series
        else:
            return None

    def evaluate(self, series, steps='auto', limit=None, data_loss_threshold=1, metrics=['RMSE', 'MAE'], details=False, start=None, end=None, **kwargs):
        """Evaluate the reconstructor on a series.

        Args:
            steps (int, list): a single value or a list of values for how many steps (intended as missing data points or slots) 
                               to reconstruct in the evaluation. Default to automatic detection based on the model.
            limit(int): set a limit for the time data elements to use for the evaluation.
            data_loss_threshold(float): the data_loss index threshold required for the reconstructor to kick-in.
            metrics(list): the error metrics to use for the evaluation.
                Supported values are:
                ``RMSE`` (Root Mean Square Error), 
                ``MAE``  (Mean Absolute Error), and 
                ``MAPE``  (Mean Absolute percentage Error).
            details(bool): if to add intermediate steps details to the evaluation results.
            start(float, datetime): evaluation start (epoch timestamp or datetime).
            end(float, datetim): evaluation end (epoch timestamp or datetime).
        """
        return super(Reconstructor, self).evaluate(series, steps, limit, data_loss_threshold, metrics, details, start, end, **kwargs)

    def _evaluate(self, series, steps='auto', limit=None, data_loss_threshold=1, metrics=['RMSE', 'MAE'], details=False, start=None, end=None, **kwargs):

        # Set evaluation_score steps if we have to
        if steps == 'auto':
            # TODO: move the "auto" concept as a function that can be overwritten by child classes
            try:
                steps = [1, self.data['periodicity']]
            except KeyError:
                steps = [1, 2, 3]
        elif isinstance(steps, list):
            pass
        else:
            steps = list(range(1, steps+1))

        # Handle start/end
        from_t = kwargs.get('from_t', None)
        to_t = kwargs.get('to_t', None)
        from_dt = kwargs.get('from_dt', None)
        to_dt = kwargs.get('to_dt', None)        
        if from_t or to_t or from_dt or to_dt:
            logger.warning('The from_t, to_t, from_dt and to_d arguments are deprecated, please use start and end instead')
        from_t, to_t = _set_from_t_and_to_t(from_dt, to_dt, from_t, to_t)

        if start is not None:       
            if isinstance(start, datetime):
                from_dt = start
            else:
                try:
                    from_t = float(start)
                except:
                    raise ValueError('Cannot use "{}" as start value, not a datetime nor an epoch timestamp'.format(start))
        if end is not None:       
            if isinstance(end, datetime):
                to_dt = end
            else:
                try:
                    to_t = float(end)
                except:
                    raise ValueError('Cannot use "{}" as end value, not a datetime nor an epoch timestamp'.format(end))

        # Support vars
        evaluation_score = {}
        warned = False
        
        # Log
        logger.info('Will evaluate model for %s steps with metrics %s', steps, metrics)
        
        # Find areas where to evaluate the model
        for data_label in series.data_labels():
             
            for steps_round in steps:
                
                # Support vars
                real_values = []
                reconstructed_values = []
                processed_samples = 0

                # Here we will have steps=1, steps=2 .. steps=n          
                logger.debug('Evaluating model for %s steps', steps_round)
                
                for i in range(len(series)):

                    # Skip if needed
                    try:
                        if not _item_is_in_range(series[i], from_t, to_t):
                            continue
                    except StopIteration:
                        break                  
                
                    # Skip the first and the last ones, otherwise reconstruct the ones in the middle
                    if (i == 0) or (i >= len(series)-steps_round):
                        continue

                    # Is this a "good area" where to test or do we have to stop?
                    stop = False
                    if series[i-1].data_loss is not None and series[i-1].data_loss >= data_loss_threshold:
                        stop = True
                    for j in range(steps_round):
                        if series[i+j].data_loss is not None and series[i+j].data_loss >= data_loss_threshold:
                            stop = True
                            break
                    if series[i+steps_round].data_loss is not None and series[i+steps_round].data_loss >= data_loss_threshold:
                        stop = True
                    if stop:
                        continue
                            
                    # Set prev and next
                    prev_value = series[i-1].data[data_label]
                    next_value = series[i+steps_round].data[data_label]
                    
                    # Compute average value
                    average_value = (prev_value+next_value)/2
                    
                    # Data to be reconstructed
                    series_to_reconstruct = series.__class__()
                    
                    # Append prev
                    #series_to_reconstruct.append(copy.deepcopy(series[i-1]))
                    
                    # Append in the middle and store real values
                    for j in range(steps_round):
                        item = copy.deepcopy(series[i+j])
                        # Set the data_loss to one so the item will be reconstructed
                        item.data_indexes['data_loss'] = 1
                        item.data[data_label] = average_value
                        series_to_reconstruct.append(item)
                        
                        real_values.append(series[i+j].data[data_label])
              
                    # Append next
                    #series_to_reconstruct.append(copy.deepcopy(series[i+steps_round]))
                    
                    # Do we have a 1-point only series? If so, manually set the resolution
                    # as otherwise it would be not defined. # TODO: does it make sense?
                    if len(series_to_reconstruct) == 1:
                        series_to_reconstruct._resolution = series.resolution

                    # Apply model inplace
                    self._apply(series_to_reconstruct, inplace=True)
                    processed_samples += 1

                    # Store reconstructed values
                    for j in range(steps_round):
                        reconstructed_values.append(series_to_reconstruct[j].data[data_label])
                    
                    # Break if we have to
                    if limit is not None and processed_samples >= limit:
                        break
                    
                    # Warn if no limit given and we are over
                    if not limit and not warned and i > 10000:
                        logger.warning('No limit set in the evaluation with a quite long time series, this could take some time.')
                        warned=True
                        
                if limit and processed_samples < limit:
                    logger.warning('The evaluation limit is set to "{}" but I have only "{}" samples for "{}" steps'.format(limit, processed_samples, steps_round))

                if not reconstructed_values:
                    raise Exception('Could not evaluate model, maybe not enough data?')

                # Compute RMSE and ME, and add to the evaluation_score
                if 'RMSE' in metrics:
                    evaluation_score['RMSE_{}_steps'.format(steps_round)] = sqrt(mean_squared_error(real_values, reconstructed_values))
                if 'MAE' in metrics:
                    evaluation_score['MAE_{}_steps'.format(steps_round)] = mean_absolute_error(real_values, reconstructed_values)
                if 'MAPE' in metrics:
                    evaluation_score['MAPE_{}_steps'.format(steps_round)] = mean_absolute_percentage_error(real_values, reconstructed_values)

        # Compute overall RMSE
        if 'RMSE' in metrics:
            sum_rmse = 0
            count = 0
            for data_label in evaluation_score:
                if data_label.startswith('RMSE_'):
                    sum_rmse += evaluation_score[data_label]
                    count += 1
            evaluation_score['RMSE'] = sum_rmse/count

        # Compute overall MAE
        if 'MAE' in metrics:
            sum_me = 0
            count = 0
            for data_label in evaluation_score:
                if data_label.startswith('MAE_'):
                    sum_me += evaluation_score[data_label]
                    count += 1
            evaluation_score['MAE'] = sum_me/count

        # Compute overall MAPE
        if 'MAPE' in metrics:
            sum_me = 0
            count = 0
            for data_label in evaluation_score:
                if data_label.startswith('MAPE_'):
                    sum_me += evaluation_score[data_label]
                    count += 1
            evaluation_score['MAPE'] = sum_me/count
        
        if not details:
            simple_evaluation_score = {}
            if 'RMSE' in metrics:
                simple_evaluation_score['RMSE'] = evaluation_score['RMSE']
            if 'MAE' in metrics:
                simple_evaluation_score['MAE'] = evaluation_score['MAE']
            if 'MAPE' in metrics:
                simple_evaluation_score['MAPE'] = evaluation_score['MAPE']
            evaluation_score = simple_evaluation_score
            
        return evaluation_score

    def _reconstruct(self, *args, **krargs):
        raise NotImplementedError('Reconstruction for this model is not yet implemented')


#=====================================
# Linear Interpolation Reconstructor
#=====================================

class LinearInterpolationReconstructor(Reconstructor):
    """A series reconstruction model based on linear interpolation.
    
    The main difference between an intepolator and a reconstructor is that interpolators are used in the transformations, *before*
    resampling or aggregating and thus must support variable-resolution time series, while reconstructors are applied *after* resampling
    or aggregating, when data has been made already uniform.
    
    In general, in Timeseria a reconstructor modifies (by reconstructing) data which is already present but that cannot be trusted, either
    because it was created with a high data loss from a transformation or because of other domain-specific factors, while an interpolator
    creates the missing samples of the underlying signal which are required for the transformations to work.
    
    Interpolators can be then seen as special case of data reconstruction models, that on one hand implement a simpler logic, but that
    on the other must provide support for time-based math in order or to be able to work on variable-resolution time series.
    
    This reconstructor wraps a linear interpolator in order to perform the data reconstruction, and can be useful for setting a baseline
    when evaluating other, more sophisticated, data reconstruction models.
    """

    def _reconstruct(self, series, data_label, from_index, to_index):
        logger.debug('Reconstructing between "{}" and "{}" (excluded)'.format(from_index, to_index))
        
        try:
            self.interpolator_initialize
        except AttributeError:
            from ..interpolators import LinearInterpolator
            self.interpolator = LinearInterpolator(series)
                
        for i in range(from_index, to_index):

            logger.debug('Processing point=%s', series[i])
            reconstructed_data = self.interpolator.evaluate(at=series[i].t, prev_i=from_index-1, next_i=to_index)

            logger.debug('Reconstructed data=%s', reconstructed_data)
            series[i]._data = reconstructed_data


#=====================================
#  Periodic Average Reconstructor
#=====================================

class PeriodicAverageReconstructor(Reconstructor):
    """A series reconstruction model based on periodic averages.
    
    Args:
        path (str): a path from which to load a saved model. Will override all other init settings.
    """

    def fit(self, data, data_loss_threshold=0.5, periodicity='auto', dst_affected=False,  offset_method='average', start=None, end=None, **kwargs):
        # This is a fit wrapper only to allow correct documentation
        
        # TODO: periodicity, dst_affected, offset_method -> move them in the init?
        """
        Fit the reconstructor on some data.
 
        Args:
            data_loss_threshold(float): the threshold of the data_loss index for discarding an element from the fit.
            periodicity(int): the periodicty of the time series. If set to ``auto`` then it will be automatically detected using a FFT.
            dst_affected(bool): if the model should take into account DST effects.
            offset_method(str): how to offset the reconstructed data in order to align it to the missing data gaps. Valuse are ``avergae``
                                to use the average gap value, or ``extrmes`` to use its extremes.
            start(float, datetime): fit start (epoch timestamp or datetime).
            end(float, datetim): fit end (epoch timestamp or datetime).
        """
        return super(PeriodicAverageReconstructor, self).fit(data, data_loss_threshold, periodicity, dst_affected, offset_method, start, end, **kwargs)

    def _fit(self, series, data_loss_threshold=0.5, periodicity='auto', dst_affected=False, offset_method='average', start=None, end=None, **kwargs):

        if not offset_method in ['average', 'extremes']:
            raise Exception('Unknown offset method "{}"'.format(offset_method))
        self.offset_method = offset_method
    
        if len(series.data_labels()) > 1:
            raise NotImplementedError('Multivariate time series are not yet supported')

        # Handle start/end
        from_t = kwargs.get('from_t', None)
        to_t = kwargs.get('to_t', None)
        from_dt = kwargs.get('from_dt', None)
        to_dt = kwargs.get('to_dt', None)        
        if from_t or to_t or from_dt or to_dt:
            logger.warning('The from_t, to_t, from_dt and to_d arguments are deprecated, please use the slice() operation instead or the square brackets notation.')
        from_t, to_t = _set_from_t_and_to_t(from_dt, to_dt, from_t, to_t)

        if start is not None:       
            if isinstance(start, datetime):
                from_dt = start
            else:
                try:
                    from_t = float(start)
                except:
                    raise ValueError('Cannot use "{}" as start value, not a datetime nor an epoch timestamp'.format(start))
        if end is not None:       
            if isinstance(end, datetime):
                to_dt = end
            else:
                try:
                    to_t = float(end)
                except:
                    raise ValueError('Cannot use "{}" as end value, not a datetime nor an epoch timestamp'.format(end))
                
        # Set or detect periodicity
        if periodicity == 'auto':
            periodicity =  detect_periodicity(series)
            try:
                if isinstance(series.resolution, TimeUnit):
                    logger.info('Detected periodicity: %sx %s', periodicity, series.resolution)
                else:
                    logger.info('Detected periodicity: %sx %ss', periodicity, series.resolution)
            except AttributeError:
                logger.info('Detected periodicity: %sx %ss', periodicity, series.resolution)
                
        self.data['periodicity']  = periodicity
        self.data['dst_affected'] = dst_affected 
                
        for data_label in series.data_labels():
            sums   = {}
            totals = {}
            processed = 0
            for item in series:
                
                # Skip if needed
                try:
                    if not _item_is_in_range(item, from_t, to_t):
                        continue
                except StopIteration:
                    break
                
                # Process. Note: we do fit on data losses = None!
                if item.data_loss is None or item.data_loss < data_loss_threshold:
                    periodicity_index = _get_periodicity_index(item, series.resolution, periodicity, dst_affected=dst_affected)
                    if not periodicity_index in sums:
                        sums[periodicity_index] = item.data[data_label]
                        totals[periodicity_index] = 1
                    else:
                        sums[periodicity_index] += item.data[data_label]
                        totals[periodicity_index] +=1
                processed += 1

        averages={}
        for periodicity_index in sums:
            averages[periodicity_index] = sums[periodicity_index]/totals[periodicity_index]
        self.data['averages'] = averages
        
        logger.debug('Processed "%s" items', processed)

    def _reconstruct(self, series, data_label, from_index, to_index):
             
        logger.debug('Reconstructing between "{}" and "{}"'.format(from_index, to_index-1))

        # Compute offset (old approach)
        if self.offset_method == 'average':
            diffs=0
            for j in range(from_index, to_index):
                real_value = series[j].data[data_label]
                periodicity_index = _get_periodicity_index(series[j], series.resolution, self.data['periodicity'], dst_affected=self.data['dst_affected'])
                reconstructed_value = self.data['averages'][periodicity_index]
                diffs += (real_value - reconstructed_value)
            offset = diffs/(to_index-from_index)
        
        elif self.offset_method == 'extremes':
            # Compute offset (new approach)
            diffs=0
            try:
                for j in [from_index-1, to_index+1]:
                    real_value = series[j].data[data_label]
                    periodicity_index = _get_periodicity_index(series[j], series.resolution, self.data['periodicity'], dst_affected=self.data['dst_affected'])
                    reconstructed_value = self.data['averages'][periodicity_index]
                    diffs += (real_value - reconstructed_value)
                offset = diffs/2
            except IndexError:
                offset=0
        else:
            raise Exception('Unknown offset method "{}"'.format(self.offset_method))

        # Actually reconstruct
        for j in range(from_index, to_index):
            item_to_reconstruct = series[j]
            periodicity_index = _get_periodicity_index(item_to_reconstruct, series.resolution, self.data['periodicity'], dst_affected=self.data['dst_affected'])
            item_to_reconstruct.data[data_label] = self.data['averages'][periodicity_index] + offset
            item_to_reconstruct.data_indexes['data_reconstructed'] = 1

    def _plot_averages(self, series, **kwargs):   
        averages_series = copy.deepcopy(series)
        for item in averages_series:
            value = self.data['averages'][_get_periodicity_index(item, averages_series.resolution, self.data['periodicity'], dst_affected=self.data['dst_affected'])]
            if not value:
                value = 0
            item.data['periodic_average'] = value 
        averages_series.plot(**kwargs)


#=====================================
#  Prophet Reconstructor
#=====================================

class ProphetReconstructor(Reconstructor, _ProphetModel):
    """A series reconstruction model based on Prophet. Prophet (from Facebook) implements a procedure for forecasting time series data based
    on an additive model where non-linear trends are fit with yearly, weekly, and daily seasonality, plus holiday effects. 
    
    Args:
        path (str): a path from which to load a saved model. Will override all other init settings.
    """

    def _fit(self, series, start=None, end=None, **kwargs):
        
        from prophet import Prophet

        # Handle start/end
        from_t = kwargs.get('from_t', None)
        to_t = kwargs.get('to_t', None)
        from_dt = kwargs.get('from_dt', None)
        to_dt = kwargs.get('to_dt', None)        
        if from_t or to_t or from_dt or to_dt:
            logger.warning('The from_t, to_t, from_dt and to_d arguments are deprecated, please use the slice() operation instead or the square brackets notation.')
        from_t, to_t = _set_from_t_and_to_t(from_dt, to_dt, from_t, to_t)

        if start is not None:       
            if isinstance(start, datetime):
                from_dt = start
            else:
                try:
                    from_t = float(start)
                except:
                    raise ValueError('Cannot use "{}" as start value, not a datetime nor an epoch timestamp'.format(start))
        if end is not None:       
            if isinstance(end, datetime):
                to_dt = end
            else:
                try:
                    to_t = float(end)
                except:
                    raise ValueError('Cannot use "{}" as end value, not a datetime nor an epoch timestamp'.format(end))
        
        if len(series.data_labels()) > 1:
            raise NotImplementedError('Multivariate time series are not yet supported')

        data = self._from_timeseria_to_prophet(series, from_t, to_t)

        # Instantiate the Prophet model
        self.prophet_model = Prophet()
        
        # Fit tjhe Prophet model
        self.prophet_model.fit(data)

    def _reconstruct(self, series, data_label, from_index, to_index):
        
        logger.debug('Reconstructing between "{}" and "{}"'.format(from_index, to_index-1))
    
        # Get and prepare data to reconstruct
        items_to_reconstruct = []
        for j in range(from_index, to_index):
            items_to_reconstruct.append(series[j])
        data_to_reconstruct = [self._remove_timezone(dt_from_s(item.t)) for item in items_to_reconstruct]
        dataframe_to_reconstruct = DataFrame(data_to_reconstruct, columns = ['ds'])

        # Apply Prophet fit
        forecast = self.prophet_model.predict(dataframe_to_reconstruct)
        #forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail()

        # Ok, replace the values with the reconsturcted ones
        for i, j in enumerate(range(from_index, to_index)):
            #logger.debug('Reconstructing item #{} with reconstucted item #{}'.format(j,i))
            item_to_reconstruct = series[j]
            item_to_reconstruct.data[data_label] = forecast['yhat'][i]
            item_to_reconstruct.data_indexes['data_reconstructed'] = 1


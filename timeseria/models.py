import os
import json
import uuid
import copy
import statistics
from .datastructures import DataTimeSlotSeries, DataTimeSlot, TimePoint, DataTimePointSeries, DataTimePoint, Slot
from .exceptions import NotFittedError
from .utilities import get_periodicity, is_numerical, set_from_t_and_to_t, item_is_in_range, check_timeseries
from .time import now_t, dt_from_s, s_from_dt
from datetime import timedelta, datetime
from sklearn.metrics import mean_squared_error, mean_absolute_error
from .units import Unit, TimeUnit
from pandas import DataFrame
from math import sqrt
from copy import deepcopy


# Setup logging
import logging
logger = logging.getLogger(__name__)

HARD_DEBUG = False


#======================
#  Utility functions
#======================

#def mean_absolute_error(list1, list2):
#    if len(list1) != len(list2):
#        raise ValueError('Lists have different lengths, cannot continue')
#    error_sum = 0
#    for i in range(len(list1)):
#        error_sum += abs(list1[i] - list2[i])
#    return error_sum/len(list1)

def mean_absolute_percentage_error(list1, list2):
    '''Computes the MAPE, list 1 are true values, list2 arepredicted values'''
    if len(list1) != len(list2):
        raise ValueError('Lists have different lengths, cannot continue')
    p_error_sum = 0
    for i in range(len(list1)):
        p_error_sum += abs((list1[i] - list2[i])/list1[i])
    return p_error_sum/len(list1)


def get_periodicity_index(time_point, resolution, periodicity, dst_affected=False):

    # Handle specific cases
    if isinstance(resolution, TimeUnit):  
        if resolution.type == TimeUnit.LOGICAL:
            raise NotImplementedError('LOGICAL time units are not yet supported')
        elif resolution.type == TimeUnit.PHYSICAL:
            pass
        else:
            raise Exception('Consistency error, got item unit type "{}" which is unknown'.format(resolution.type))

        resolution_s = resolution.duration_s()
    
    elif isinstance(resolution, Unit):  
        if isinstance(resolution.value, list):
            raise NotImplementedError('Sorry, periodicty in multi-dimensional spaces are not defined')
        resolution_s = resolution.value

    else:
        if isinstance(resolution, list):
            raise NotImplementedError('Sorry, periodicty in multi-dimensional spaces are not defined')
        resolution_s = resolution

    # Compute periodicity index
    if not dst_affected:
    
        # Get index based on item start, normalized to unit, modulus periodicity
        t = time_point.t
        periodicity_index =  int(t / resolution_s) % periodicity
    
    else:

        # Get periodicity based on the datetime
        t  = time_point.t
        dt = time_point.dt
        
        # Do we have an active DST?  
        dst_timedelta = dt.dst()
        
        if dst_timedelta.days == 0 and dst_timedelta.seconds == 0:
            # No DST
            periodicity_index = int(t / resolution_s) % periodicity
        
        else:
            # DST
            if dst_timedelta.days != 0:
                raise Exception('Don\'t know how to handle DST with days timedelta = "{}"'.format(dst_timedelta.days))

            if resolution_s > 3600:
                raise Exception('Sorry, this time series has not enough resolution to account for DST effects (resolution_s="{}", must be below 3600 seconds)'.format(resolution_s))
            
            # Get DST offset in seconds 
            dst_offset_s = dst_timedelta.seconds # 3600 usually

            # Compute periodicity in seconds (example: 144 10-minute items) 
            #periodicity_s = periodicity * resolution_s
            
            # Get DST offset "items"
            #dst_offset_items = int(dst_offset_s / resolution_s) # For ten-minutes item is 6               
            #periodicity_index = (int(t / resolution_s) % periodicity) #+ dst_offset_items
            
            periodicity_index = (int((t + dst_offset_s) / resolution_s) % periodicity)

    return periodicity_index



#======================
#  Base classes
#======================

#class EvaluationScore(object):
#    '''Class to incapsulate a model score after an evaluation_score'''
#    pass

class Model(object):
    '''A stateless model, or a white-box model. Exposes only predict(), apply() and evaluate() methods,
    since it is assumed that all the information is coded and nothing is learnt from the data.'''
    
    def __init__(self):
        pass

    
    def predict(self, data, *args, **kwargs):
        try:
            self._predict
        except AttributeError:
            raise NotImplementedError('Predicting from this model is not implemented')

        check_timeseries(data)
        
        return self._predict(data, *args, **kwargs)


    def apply(self, data, *args, **kwargs):
        try:
            self._apply
        except AttributeError:
            raise NotImplementedError('Applying this model is not implemented')

        check_timeseries(data)
        
        return self._apply(data, *args, **kwargs)


    def evaluate(self, data, *args, **kwargs):
        try:
            self._evaluate
        except AttributeError:
            raise NotImplementedError('Evaluating this model is not implemented')

        check_timeseries(data)
        
        return self._evaluate(data, *args, **kwargs)


class ParametricModel(Model):
    '''A stateful model with parameters, or a (partly) black-box model. Parameters can be set manually or learnt (fitted) from data.
On top of the predict(), apply() and evaluate() methods it provides a save() method to store the parameters of the model,
and optionally a fit() method if the parameters are to be learnt form data.'''
    
    def __init__(self, path=None, id=None):
        
        if path:
            with open(path+'/data.json', 'r') as f:
                self.data = json.loads(f.read())         
            self.fitted=True
        else:
            if not id:
                id = str(uuid.uuid4())
            self.fitted = False
            self.data = {'id': id}

        super(ParametricModel, self).__init__()


    def predict(self, data, *args, **kwargs):

        try:
            self._predict
        except AttributeError:
            raise NotImplementedError('Predicting from this model is not implemented')

        if not self.fitted:
            raise NotFittedError()

        check_timeseries(data)
        
        return self._predict(data, *args, **kwargs)


    def apply(self, data, *args, **kwargs):

        try:
            self._apply
        except AttributeError:
            raise NotImplementedError('Applying this model is not implemented')

        if not self.fitted:
            raise NotFittedError()

        check_timeseries(data)
        
        return self._apply(data, *args, **kwargs)


    def evaluate(self, data, *args, **kwargs):

        try:
            self._evaluate
        except AttributeError:
            raise NotImplementedError('Evaluating this model is not implemented')

        if not self.fitted:
            raise NotFittedError()
        
        check_timeseries(data)
        
        return self._evaluate(data, *args, **kwargs)


    def fit(self, data, *args, **kwargs):

        try:
            self._fit
        except AttributeError:
            raise NotImplementedError('Fitting this model is not implemented')

        check_timeseries(data)
        
        fit_output = self._fit(data, *args, **kwargs)

        self.data['fitted_at'] = now_t()
        self.fitted = True
        return fit_output

        
    def save(self, path):
        # TODO: dump and enforce the TimeUnit as well?
        if not self.fitted:
            raise NotFittedError()
        model_dir = '{}/{}'.format(path, self.data['id'])
        os.makedirs(model_dir)
        model_data_file = '{}/data.json'.format(model_dir)
        with open(model_data_file, 'w') as f:
            f.write(json.dumps(self.data))
        logger.info('Saved model with id "%s" in "%s"', self.data['id'], model_dir)
        return model_dir


    def cross_validate(self, data, *args, **kwargs):
        try:
            self._evaluate
        except AttributeError:
            raise NotImplementedError('Evaluating this model is not implemented')

        check_timeseries(data)

        # Decouple fit from validate args
        fit_kwargs = {}
        evaluate_kwargs = {}
        consumed_kwargs = []
        for kwarg in kwargs:
            if kwarg.startswith('fit_'):
                consumed_kwargs.append(kwarg)
                fit_kwargs[kwarg.replace('fit_', '')] = kwargs[kwarg]
            if kwarg.startswith('evaluate_'):
                consumed_kwargs.append(kwarg)
                evaluate_kwargs[kwarg.replace('evaluate_', '')] = kwargs[kwarg]
        for consumed_kwarg in consumed_kwargs:
            kwargs.pop(consumed_kwarg)

        # For readability
        timeseries = data
        
        # How many rounds
        rounds = kwargs.pop('rounds', 10)

        # Do we still have some kwargs?
        if kwargs:
            raise Exception('Got some unknown args: {}'.format(kwargs))
            
        # How many items per round?
        round_items = int(len(timeseries) / rounds)
        logger.debug('Items per round: {}'.format(round_items))
        
        # Start the fit / evaluate loop
        evaluations = []        
        for i in range(rounds):
            from_t = timeseries[(round_items*i)].t
            to_t = timeseries[(round_items*i) + round_items].t
            from_dt = dt_from_s(from_t)
            to_dt   = dt_from_s(to_t)
            logger.info('Cross validation round #{} of {}: validate from {} ({}) to {} ({}), fit on the rest.'.format(i+1, rounds, from_t, from_dt, to_t, to_dt))
            
            # Fit
            if i == 0:            
                logger.debug('Fitting from {} ({})'.format(to_t, to_dt))
                self.fit(data, from_t=to_t, **fit_kwargs)
            else:
                logger.debug('Fitting until {} ({}) and then from {} ({}).'.format(to_t, to_dt, from_t, from_dt))
                self.fit(data, from_t=to_t, to_t=from_t, **fit_kwargs)                
            
            # Evaluate & append
            evaluations.append(self.evaluate(data, from_t=from_t, to_t=to_t, **evaluate_kwargs))
        
        # Regroup evaluations
        evaluation_metrics = list(evaluations[0].keys())
        scores_by_evaluation_metric = {}
        for evaluation in evaluations:
            for evaluation_metric in evaluation_metrics:
                try:
                    scores_by_evaluation_metric[evaluation_metric].append(evaluation[evaluation_metric])
                except KeyError:
                    try:
                        scores_by_evaluation_metric[evaluation_metric] = [evaluation[evaluation_metric]]
                    except KeyError:
                        raise Exception('Error, the model generated different evaluation metrics over the rounds, cannot compute cross validation.') from None
        
        # Prepare and return results
        results = {}
        for evaluation_metric in scores_by_evaluation_metric:
            results[evaluation_metric+'_avg'] = statistics.mean(scores_by_evaluation_metric[evaluation_metric])
            results[evaluation_metric+'_stdev'] = statistics.stdev(scores_by_evaluation_metric[evaluation_metric])         
        return results


    @property
    def id(self):
        return self.data['id']



#======================
# Data Reconstruction
#======================

class Reconstructor(ParametricModel):

    def _apply(self, timeseries, remove_data_loss=False, data_loss_threshold=1, inplace=False):
        logger.debug('Using data_loss_threshold="%s"', data_loss_threshold)

        # TODO: understand if we want the apply from/to behavior. For now it is disabled
        # (add from_t=None, to_t=None, from_dt=None, to_dt=None in the function call above)
        # from_t, to_t = set_from_t_and_to_t(from_dt, to_dt, from_t, to_t)
        # Maybe also add a timeseries.mark=[from_dt, to_dt]
         
        from_t = None
        to_t   = None
        
        if not inplace:
            timeseries = timeseries.duplicate()

        if len(timeseries.data_keys()) > 1:
            raise NotImplementedError('Multivariate time series are not yet supported')

        for key in timeseries.data_keys():
            
            gap_started = None
            
            for i, item in enumerate(timeseries):
                
                # Skip if before from_t/dt of after to_t/dt
                if from_t is not None and timeseries[i].t < from_t:
                    continue
                try:
                    # Handle items
                    if to_t is not None and timeseries[i].end.t > to_t:
                        break
                except AttributeError:
                    # Handle points
                    if to_t is not None and timeseries[i].t > to_t:
                        break                

                if item.data_loss >= data_loss_threshold:
                    # This is the beginning of an area we want to reconstruct according to the data_loss_threshold
                    if gap_started is None:
                        gap_started = i
                else:
                    
                    if gap_started is not None:
                    
                        # Reconstruct for this gap
                        self._reconstruct(from_index=gap_started, to_index=i, timeseries=timeseries, key=key)
                        gap_started = None
                    
                    item._data_reconstructed = 0
                    
                if remove_data_loss:
                    # TOOD: move to None if we allow data_losses (coverages) to None?
                    item._coverage = 1
            
            # Reconstruct the last gap as well if left "open"
            if gap_started is not None:
                self._reconstruct(from_index=gap_started, to_index=i+1, timeseries=timeseries, key=key)

        if not inplace:
            return timeseries
        else:
            return None


    def _evaluate(self, timeseries, steps='auto', samples=1000, data_loss_threshold=1, metrics=['RMSE', 'MAE'], details=False, from_t=None, to_t=None, from_dt=None, to_dt=None):

        # Set evaluation_score steps if we have to
        if steps == 'auto':
            try:
                steps = [1, self.data['periodicity']]
            except KeyError:
                steps = [1, 2, 3]
        elif isinstance(steps, list):
            pass
        else:
            steps = list(range(1, steps+1))
         
        # Support vars
        evaluation_score = {}
        from_t, to_t = set_from_t_and_to_t(from_dt, to_dt, from_t, to_t)

        logger.info('Will evaluate model for %s steps with metrics %s', steps, metrics)

        # Find areas where to evaluate the model
        for key in timeseries.data_keys():
             
            for steps_round in steps:
                
                # Support vars
                real_values = []
                reconstructed_values = []
                processed_samples = 0

                # Here we will have steps=1, steps=2 .. steps=n          
                logger.debug('Evaluating model for %s steps', steps_round)
                
                for i in range(len(timeseries)):

                    # Skip if needed
                    try:
                        if not item_is_in_range(timeseries[i], from_t, to_t):
                            continue
                    except StopIteration:
                        break                  
                
                    # Skip the first and the last ones, otherwise reconstruct the ones in the middle
                    if (i == 0) or (i >= len(timeseries)-steps_round):
                        continue

                    # Is this a "good area" where to test or do we have to stop?
                    stop = False
                    if timeseries[i-1].data_loss >= data_loss_threshold:
                        stop = True
                    for j in range(steps_round):
                        if timeseries[i+j].data_loss >= data_loss_threshold:
                            stop = True
                            break
                    if timeseries[i+steps_round].data_loss >= data_loss_threshold:
                        stop = True
                    if stop:
                        continue
                            
                    # Set prev and next
                    prev_value = timeseries[i-1].data[key]
                    next_value = timeseries[i+steps_round].data[key]
                    
                    # Compute average value
                    average_value = (prev_value+next_value)/2
                    
                    # Data to be reconstructed
                    timeseries_to_reconstruct = timeseries.__class__()
                    
                    # Append prev
                    #timeseries_to_reconstruct.append(copy.deepcopy(timeseries[i-1]))
                    
                    # Append in the middle and store real values
                    for j in range(steps_round):
                        item = copy.deepcopy(timeseries[i+j])
                        # Set the coverage to zero so the item will be reconstructed
                        item._coverage = 0
                        item.data[key] = average_value
                        timeseries_to_reconstruct.append(item)
                        
                        real_values.append(timeseries[i+j].data[key])
              
                    # Append next
                    #timeseries_to_reconstruct.append(copy.deepcopy(timeseries[i+steps_round]))

                    # Apply model inplace
                    self._apply(timeseries_to_reconstruct, inplace=True)
                    processed_samples += 1

                    # Store reconstructed values
                    for j in range(steps_round):
                        reconstructed_values.append(timeseries_to_reconstruct[j].data[key])
                    
                    if samples is not None and processed_samples >= samples:
                        break

                if processed_samples < samples:
                    logger.warning('Could not evaluate "{}" samples for "{}" steps_round, processed "{}" samples only'.format(samples, steps_round, processed_samples))

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
            for key in evaluation_score:
                if key.startswith('RMSE_'):
                    sum_rmse += evaluation_score[key]
                    count += 1
            evaluation_score['RMSE'] = sum_rmse/count

        # Compute overall MAE
        if 'MAE' in metrics:
            sum_me = 0
            count = 0
            for key in evaluation_score:
                if key.startswith('MAE_'):
                    sum_me += evaluation_score[key]
                    count += 1
            evaluation_score['MAE'] = sum_me/count

        # Compute overall MAPE
        if 'MAPE' in metrics:
            sum_me = 0
            count = 0
            for key in evaluation_score:
                if key.startswith('MAPE_'):
                    sum_me += evaluation_score[key]
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



class PeriodicAverageReconstructor(Reconstructor):


    def _fit(self, timeseries, data_loss_threshold=0.5, periodicity=None, dst_affected=False, timezone_affected=False, from_t=None, to_t=None, from_dt=None, to_dt=None, offset_method='average'):

        if not offset_method in ['average', 'extremes']:
            raise Exception('Unknown offset method "{}"'.format(self.offset_method))
        self.offset_method = offset_method
    
        if len(timeseries.data_keys()) > 1:
            raise NotImplementedError('Multivariate time series are not yet supported')

        from_t, to_t = set_from_t_and_to_t(from_dt, to_dt, from_t, to_t)
        
        # Set or detect periodicity
        if periodicity is None:
            periodicity =  get_periodicity(timeseries)
            try:
                if isinstance(timeseries.resolution, TimeUnit):
                    logger.info('Detected periodicity: %sx %s', periodicity, timeseries.resolution)
                else:
                    logger.info('Detected periodicity: %sx %ss', periodicity, timeseries.resolution)
            except AttributeError:
                logger.info('Detected periodicity: %sx %ss', periodicity, timeseries.resolution)
                
        self.data['periodicity']  = periodicity
        self.data['dst_affected'] = dst_affected 
        
        # logger.info('dst_affected: {}'.format(dst_affected))
        
        for key in timeseries.data_keys():
            sums   = {}
            totals = {}
            processed = 0
            for item in timeseries:
                
                # Skip if needed
                try:
                    if not item_is_in_range(item, from_t, to_t):
                        continue
                except StopIteration:
                    break
                
                # Process
                if item.data_loss < data_loss_threshold:
                    periodicity_index = get_periodicity_index(item, timeseries.resolution, periodicity, dst_affected=dst_affected)
                    if not periodicity_index in sums:
                        sums[periodicity_index] = item.data[key]
                        totals[periodicity_index] = 1
                    else:
                        sums[periodicity_index] += item.data[key]
                        totals[periodicity_index] +=1
                processed += 1

        averages={}
        for periodicity_index in sums:
            averages[periodicity_index] = sums[periodicity_index]/totals[periodicity_index]
        self.data['averages'] = averages

        # logger.info('Processed "{}" items'.format(processed))


    def _reconstruct(self, timeseries, key, from_index, to_index):
        logger.debug('Reconstructing between "{}" and "{}"'.format(from_index, to_index-1))

        # Compute offset (old approach)
        if self.offset_method == 'average':
            diffs=0
            for j in range(from_index, to_index):
                real_value = timeseries[j].data[key]
                periodicity_index = get_periodicity_index(timeseries[j], timeseries.resolution, self.data['periodicity'], dst_affected=self.data['dst_affected'])
                reconstructed_value = self.data['averages'][periodicity_index]
                diffs += (real_value - reconstructed_value)
            offset = diffs/(to_index-from_index)
        
        elif self.offset_method == 'extremes':
            # Compute offset (new approach)
            diffs=0
            try:
                for j in [from_index-1, to_index+1]:
                    real_value = timeseries[j].data[key]
                    periodicity_index = get_periodicity_index(timeseries[j], timeseries.resolution, self.data['periodicity'], dst_affected=self.data['dst_affected'])
                    reconstructed_value = self.data['averages'][periodicity_index]
                    diffs += (real_value - reconstructed_value)
                offset = diffs/2
            except IndexError:
                offset=0
        else:
            raise Exception('Unknown offset method "{}"'.format(self.offset_method))

        # Actually reconstruct
        for j in range(from_index, to_index):
            item_to_reconstruct = timeseries[j]
            periodicity_index = get_periodicity_index(item_to_reconstruct, timeseries.resolution, self.data['periodicity'], dst_affected=self.data['dst_affected'])
            item_to_reconstruct.data[key] = self.data['averages'][periodicity_index] + offset
            item_to_reconstruct._data_reconstructed = 1
                        

    def _plot_averages(self, timeseries, **kwargs):   
        averages_timeseries = copy.deepcopy(timeseries)
        for item in averages_timeseries:
            value = self.data['averages'][get_periodicity_index(item, averages_timeseries.resolution, self.data['periodicity'], dst_affected=self.data['dst_affected'])]
            if not value:
                value = 0
            item.data['average'] =value 
        averages_timeseries.plot(**kwargs)



class ProphetModel(ParametricModel):

    @classmethod
    def remove_timezone(cls, dt):
        return dt.replace(tzinfo=None)

    @classmethod
    def from_timeseria_to_prophet(cls, timeseries, from_t=None, to_t=None):

        # Create Python lists with data
        try:
            timeseries[0].data[0]
            data_keys_are_indexes = True
        except KeyError:
            timeseries[0].data.keys()
            data_keys_are_indexes = False
        
        data_as_list=[]
        for item in timeseries:
            
            # Skip if needed
            try:
                if not item_is_in_range(item, from_t, to_t):
                    continue
            except StopIteration:
                break                

            if data_keys_are_indexes:     
                data_as_list.append([cls.remove_timezone(item.dt), item.data[0]])
            else:
                data_as_list.append([cls.remove_timezone(item.dt), item.data[list(item.data.keys())[0]]])

        # Create the pandas DataFrames
        data = DataFrame(data_as_list, columns = ['ds', 'y'])

        return data



class ProphetReconstructor(Reconstructor, ProphetModel):
    
    def _fit(self, timeseries, from_t=None, to_t=None, from_dt=None, to_dt=None):

        from fbprophet import Prophet

        from_t, to_t = set_from_t_and_to_t(from_dt, to_dt, from_t, to_t)

        if len(timeseries.data_keys()) > 1:
            raise NotImplementedError('Multivariate time series are not yet supported')

        data = self.from_timeseria_to_prophet(timeseries, from_t, to_t)

        # Instantiate the Prophet model
        self.prophet_model = Prophet()
        
        # Fit tjhe Prophet model
        self.prophet_model.fit(data)



    def _reconstruct(self, timeseries, key, from_index, to_index):
        logger.debug('Reconstructing between "{}" and "{}"'.format(from_index, to_index-1))
    
        # Get and prepare data to reconstruct
        items_to_reconstruct = []
        for j in range(from_index, to_index):
            items_to_reconstruct.append(timeseries[j])
        data_to_reconstruct = [self.remove_timezone(dt_from_s(item.t)) for item in items_to_reconstruct]
        dataframe_to_reconstruct = DataFrame(data_to_reconstruct, columns = ['ds'])

        # Apply Prophet fit
        forecast = self.prophet_model.predict(dataframe_to_reconstruct)
        #forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail()

        # Ok, replace the values withe the reconsturcted ones
        for i, j in enumerate(range(from_index, to_index)):
            #logger.debug('Reconstructing item #{} with reconstucted item #{}'.format(j,i))
            item_to_reconstruct = timeseries[j]
            item_to_reconstruct.data[key] = forecast['yhat'][i]
            item_to_reconstruct._data_reconstructed = 1
    


#======================
#  Forecast
#======================

class Forecaster(ParametricModel):

    def _evaluate(self, timeseries, steps='auto', samples=1000, plots=False, metrics=['RMSE', 'MAE'], details=False, from_t=None, to_t=None, from_dt=None, to_dt=None):

        # Set evaluation_score steps if we have to
        if steps == 'auto':
            try:
                steps = [1, self.data['periodicity']]
            except KeyError:
                steps = [1, 2, 3]
        elif isinstance(steps, list):
            pass
        else:
            steps = list(range(1, steps+1))
                            
        # Support vars
        evaluation_score = {}
        from_t, to_t = set_from_t_and_to_t(from_dt, to_dt, from_t, to_t)

        logger.info('Will evaluate model for %s steps with metrics %s', steps, metrics)

        for steps_round in steps:
            
            # Support vars
            real_values = []
            model_values = []
            processed_samples = 0
    
            # For each point of the timeseries, after the window, apply the prediction and compare it with the actual value
            for key in timeseries.data_keys():
                for i in range(len(timeseries)):

                    # Skip if needed
                    try:
                        if not item_is_in_range(timeseries[i], from_t, to_t):
                            continue
                    except StopIteration:
                        break  
                
                    # Check that we can get enough data
                    if i < self.data['window']+steps_round:
                        continue
                    if i > (len(timeseries)-steps_round):
                        continue

                    # Compute the various boundaries
                    original_serie_boundaries_start = i - (self.data['window']) - steps_round
                    original_serie_boundaries_end = i
                    
                    original_forecast_serie_boundaries_start = original_serie_boundaries_start
                    original_forecast_serie_boundaries_end = original_serie_boundaries_end-steps_round
                    
                    # Create the time series where to apply the forecast on
                    forecast_timeseries = timeseries.__class__()
                    for j in range(original_forecast_serie_boundaries_start, original_forecast_serie_boundaries_end):
                        forecast_timeseries.append(timeseries[j])
 
                    # Apply the forecasting model
                    self._apply(forecast_timeseries, n=steps_round, inplace=True)

                    # Plot evaluation_score time series?
                    if plots:
                        forecast_timeseries.plot(log_js=False)
                    
                    # Compare each forecast with the original value
                    for step in range(steps_round):
                        original_index = original_serie_boundaries_start + self.data['window'] + step

                        forecast_index = self.data['window'] + step

                        model_value = forecast_timeseries[forecast_index].data[key]
                        model_values.append(model_value)
                        
                        real_value = timeseries[original_index].data[key]
                        real_values.append(real_value)
 
                    processed_samples+=1
                    if samples is not None and processed_samples >= samples:
                        break
                
            if processed_samples < samples:
                logger.warning('Could not evaluate "{}" samples for "{}" steps_round, processed "{}" samples only'.format(samples, steps_round, processed_samples))

            if not model_values:
                raise Exception('Could not evaluate model, maybe not enough data?')

            # Compute RMSE and ME, and add to the evaluation_score
            if 'RMSE' in metrics:
                evaluation_score['RMSE_{}_steps'.format(steps_round)] = sqrt(mean_squared_error(real_values, model_values))
            if 'MAE' in metrics:
                evaluation_score['MAE_{}_steps'.format(steps_round)] = mean_absolute_error(real_values, model_values)
            if 'MAPE' in metrics:
                evaluation_score['MAPE_{}_steps'.format(steps_round)] = mean_absolute_percentage_error(real_values, model_values)

        # Compute overall RMSE
        if 'RMSE' in metrics:
            sum_rmse = 0
            count = 0
            for key in evaluation_score:
                if key.startswith('RMSE_'):
                    sum_rmse += evaluation_score[key]
                    count += 1
            evaluation_score['RMSE'] = sum_rmse/count

        # Compute overall MAE
        if 'MAE' in metrics:
            sum_me = 0
            count = 0
            for key in evaluation_score:
                if key.startswith('MAE_'):
                    sum_me += evaluation_score[key]
                    count += 1
            evaluation_score['MAE'] = sum_me/count

        # Compute overall MAPE
        if 'MAPE' in metrics:
            sum_me = 0
            count = 0
            for key in evaluation_score:
                if key.startswith('MAPE_'):
                    sum_me += evaluation_score[key]
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


    def _apply(self, timeseries, n=1, inplace=False):

        # TODO: refacotr to use the predict below

        if len(timeseries.data_keys()) > 1:
            raise NotImplementedError('Multivariate time series are not yet supported')
 
        if len(timeseries) < self.data['window']:
            raise ValueError('The timeseries length ({}) is shorter than the model window ({}), it must be at least equal.'.format(len(timeseries), self.data['window']))
 
        if inplace:
            forecast_timeseries = timeseries
        else:
            forecast_timeseries = timeseries.duplicate()
        
        for key in forecast_timeseries.data_keys():

            # Support var
            first_call = True

            for _ in range(n):
                
                # Compute start/end for the item to be forecasted
                if isinstance(forecast_timeseries.resolution, TimeUnit):
                    this_item_start_dt = forecast_timeseries[-1].dt + forecast_timeseries.resolution
                    this_item_end_dt   =  this_item_start_dt + forecast_timeseries.resolution
                    this_item_start_t  = s_from_dt(this_item_start_dt) 
                    this_item_end_t    = s_from_dt(this_item_end_dt)
                else:
                    this_item_start_t = forecast_timeseries[-1].t + forecast_timeseries.resolution
                    this_item_end_t   = this_item_start_t + forecast_timeseries.resolution
                    this_item_start_dt = dt_from_s(this_item_start_t, tz=forecast_timeseries.tz)
                    this_item_end_dt = dt_from_s(this_item_end_t, tz=forecast_timeseries.tz )                    

                # Set time zone
                tz = forecast_timeseries[-1].tz
                
                # Define TimePoints
                this_item_start_timePoint = TimePoint(this_item_start_t, tz=tz)
                this_item_end_timePoint = TimePoint(this_item_end_t, tz=tz)

                # Call model forecasting logic
                forecast_model_results = self._forecast(forecast_timeseries, timeseries.resolution, key, this_item_start_timePoint, this_item_end_timePoint, first_call, n=n)

                if isinstance(forecast_model_results, list):
                    for forecasted_item in forecast_model_results:
                    
                        # Add the forecast to the forecasts time series
                        forecast_timeseries.append(forecasted_item)
                    
                    # We are done
                    break
                
                else:
                
                    # Add the forecast to the forecasts time series
                    forecasted_item = forecast_model_results
                    forecast_timeseries.append(forecasted_item)
                    
                # Set fist call to false if this was the first call
                if first_call:
                    first_call = False 

        # Set serie mark for the forecast and return
        try:
            # Handle items
            forecast_timeseries.mark = [forecast_timeseries[-n].dt, forecast_timeseries[-1].end.dt]
        except AttributeError:
            # Handle points TODO: should be dt-(resolution/2) and dt+(resolution/2)
            forecast_timeseries.mark = [forecast_timeseries[-n].dt, forecast_timeseries[-1].dt]
                
        if not inplace:
            return forecast_timeseries
        else:
            return None


    def _predict(self, timeseries, n=1):
        
        # TODO: this is highly inefficient, fix me!
        forecast_timeseries = timeseries.__class__(*self.apply(timeseries, inplace=False, n=n)[len(timeseries):])

        return forecast_timeseries



class PeriodicAverageForecaster(Forecaster):
        
    def _fit(self, timeseries, window=None, periodicity=None, dst_affected=False, from_t=None, to_t=None, from_dt=None, to_dt=None):

        if len(timeseries.data_keys()) > 1:
            raise NotImplementedError('Multivariate time series are not yet supported')

        from_t, to_t = set_from_t_and_to_t(from_dt, to_dt, from_t, to_t)

        # Set or detect periodicity
        if periodicity is None:        
            periodicity =  get_periodicity(timeseries)
            try:
                if isinstance(timeseries.resolution, TimeUnit):
                    logger.info('Detected periodicity: %sx %s', periodicity, timeseries.resolution)
                else:
                    logger.info('Detected periodicity: %sx %ss', periodicity, timeseries.resolution)
            except AttributeError:
                logger.info('Detected periodicity: %sx %ss', periodicity, timeseries.resolution)
                
        self.data['periodicity']  = periodicity
        self.data['dst_affected'] = dst_affected

        # Set or detect window
        if window:
            self.data['window'] = window
        else:
            logger.info('Using a window of "{}"'.format(periodicity))
            self.data['window'] = periodicity

        for key in timeseries.data_keys():
            sums   = {}
            totals = {}
            processed = 0
            for item in timeseries:

                # Skip if needed
                try:
                    if not item_is_in_range(item, from_t, to_t):
                        continue                  
                except StopIteration:
                    break
                
                # Process
                periodicity_index = get_periodicity_index(item, timeseries.resolution, periodicity, dst_affected)
                if not periodicity_index in sums:
                    sums[periodicity_index] = item.data[key]
                    totals[periodicity_index] = 1
                else:
                    sums[periodicity_index] += item.data[key]
                    totals[periodicity_index] +=1
                processed += 1

        averages={}
        for periodicity_index in sums:
            averages[periodicity_index] = sums[periodicity_index]/totals[periodicity_index]
        self.data['averages'] = averages
        
        #logger.info('Processed "{}" items'.format(processed))


    def _forecast(self, forecast_timeseries, resolution, key, this_item_start_timePoint, this_item_end_timePoint, first_call, n, window_start=None, raw=False) : #, timeseries, key, from_index, to_index):

        # Compute the offset (avg diff between the real values and the forecasts on the first window)
        try:
            self.offsets
        except AttributeError:
            self.offsets={}
            
        if key not in self.offsets or first_call:

            diffs  = 0
            
            if window_start is not None:
                for j in range(self.data['window']):
                    serie_index = window_start + j
                    real_value = forecast_timeseries[serie_index].data[key]
                    forecast_value = self.data['averages'][get_periodicity_index(forecast_timeseries[serie_index], forecast_timeseries.resolution, self.data['periodicity'], dst_affected=self.data['dst_affected'])]
                    diffs += (real_value - forecast_value)            
            else:
                for j in range(self.data['window']):
                    serie_index = -(self.data['window']-j)
                    real_value = forecast_timeseries[serie_index].data[key]
                    forecast_value = self.data['averages'][get_periodicity_index(forecast_timeseries[serie_index], forecast_timeseries.resolution, self.data['periodicity'], dst_affected=self.data['dst_affected'])]
                    diffs += (real_value - forecast_value)
       
            # Sum the avg diff between the real and the forecast on the window to the forecast (the offset)
            offset = diffs/j
            self.offsets[key] = offset
        
        else:
            offset = self.offsets[key] 
        
        # Compute and add the real forecast data
        periodicity_index = get_periodicity_index(this_item_start_timePoint, resolution, self.data['periodicity'], dst_affected=self.data['dst_affected'])        
        forecast_data = {key: self.data['averages'][periodicity_index] + (offset*1.0)}
        
        if raw:
            return forecast_data
        else:
            if isinstance(forecast_timeseries[0], Slot):
                forecasted_item = DataTimeSlot(start = this_item_start_timePoint,
                                                         end   = this_item_end_timePoint,
                                                         unit  = forecast_timeseries.resolution,
                                                         coverage = None,
                                                         data  = forecast_data)
            else:
                forecasted_item = DataTimePoint(t = this_item_start_timePoint.t,
                                                          tz = this_item_start_timePoint.tz,
                                                          data  = forecast_data)                

            return forecasted_item
    

    def _plot_averages(self, timeseries, **kwargs):      
        averages_timeseries = copy.deepcopy(timeseries)
        for item in averages_timeseries:
            value = self.data['averages'][get_periodicity_index(item, averages_timeseries.resolution, self.data['periodicity'], dst_affected=self.data['dst_affected'])]
            if not value:
                value = 0
            item.data['average'] =value 
        averages_timeseries.plot(**kwargs)






class ProphetForecaster(Forecaster, ProphetModel):
    '''Prophet (from Facebook) implements a procedure for forecasting time series data based on an additive 
model where non-linear trends are fit with yearly, weekly, and daily seasonality, plus holiday effects.
It works best with time series that have strong seasonal effects and several seasons of historical data.
Prophet is robust to missing data and shifts in the trend, and typically handles outliers well. 
'''


    def _fit(self, timeseries, window=None, periodicity=None, dst_affected=False, from_t=None, to_t=None, from_dt=None, to_dt=None):

        from fbprophet import Prophet

        if len(timeseries.data_keys()) > 1:
            raise NotImplementedError('Multivariate time series are not yet supported')

        from_t, to_t = set_from_t_and_to_t(from_dt, to_dt, from_t, to_t)

        data = self.from_timeseria_to_prophet(timeseries, from_t=from_t, to_t=to_t)

        # Instantiate the Prophet model
        self.prophet_model = Prophet()
        
        # Fit tjhe Prophet model
        self.prophet_model.fit(data)
        
        if not window:
            logger.info('Defaulting to a window of 10 items for forecasting')
            self.data['window'] = 10


    def _forecast(self, forecast_timeseries, resolution, key, this_item_start_timePoint, this_item_end_timePoint, first_call, n, multi=True) : #, timeseries, key, from_index, to_index):

        resolution = forecast_timeseries.resolution

        if not multi:

            if isinstance (resolution, TimeUnit):
                data_to_forecast = [self.remove_timezone( forecast_timeseries[-1].dt + forecast_timeseries[-1].unit)]
            else:
                data_to_forecast = [self.remove_timezone(dt_from_s(forecast_timeseries[-1].t + forecast_timeseries[-1].unit.value))]
            
            dataframe_to_forecast = DataFrame(data_to_forecast, columns = ['ds'])
            
            forecast = self.prophet_model.predict(dataframe_to_forecast)
            #forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail()


            # Compute and add the real forecast data
            if isinstance(forecast_timeseries[0], Slot):
                forecasted_item = DataTimeSlot(start = this_item_start_timePoint,
                                                         unit  = resolution,
                                                         coverage = None,
                                                         data  = {key: float(forecast['yhat'])})
            else:
                forecasted_item = DataTimePoint(dt = this_item_start_timePoint.dt,
                                                          tz = this_item_start_timePoint.tz,
                                                          data  = {key: float(forecast['yhat'])})

            return forecasted_item
        
        else:
            last_item    = forecast_timeseries[-1]
            last_item_t  = last_item.t
            last_item_dt = last_item.dt
            forecast_timestamps = []
            data_to_forecast = []
            
            # Prepare a dataframe wiht all the items to forecast
            for _ in range(n):
                if isinstance (resolution, TimeUnit):
                    new_item_dt = last_item_dt + resolution
                    data_to_forecast.append(self.remove_timezone(new_item_dt))
                    last_item_dt = new_item_dt
                    forecast_timestamps.append(new_item_dt)
                else:
                    new_item_t = last_item_t + resolution.value
                    new_item_dt = dt_from_s(new_item_t, tz=forecast_timeseries.tz)
                    data_to_forecast.append(self.remove_timezone(new_item_dt))
                    last_item_t = new_item_t
                    forecast_timestamps.append(new_item_dt)
                    
            dataframe_to_forecast = DataFrame(data_to_forecast, columns = ['ds'])
                         
            forecast = self.prophet_model.predict(dataframe_to_forecast)
            #forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail()
        
            forecasted_items = []
        
            # Re convert to items
            for i in range(n):

                # Compute and add the real forecast data
                if isinstance(forecast_timeseries[0], Slot):
                    forecasted_item = DataTimeSlot(start = TimePoint(dt=forecast_timestamps[i]),
                                                             unit  = resolution,
                                                             coverage = None,
                                                             data  = {key: float(forecast['yhat'][i])})
                else:
                    forecasted_item = DataTimePoint(dt = forecast_timestamps[i],
                                                              tz = this_item_start_timePoint.tz,
                                                              data  = {key: float(forecast['yhat'][i])})     
                
                
                
                forecasted_items.append(forecasted_item)
                
        
            return forecasted_items      



class AnomalyDetector(ParametricModel):
    pass



class PeriodicAverageAnomalyDetector(AnomalyDetector):


    def __init__(self, *args, **kwargs):

        # Initialize
        super(PeriodicAverageAnomalyDetector, self).__init__()


    def __get_actual_and_predicted(self, timeseries, i, key, forecaster_window):

        # Compute start/end for the item to be forecasted
        if isinstance(timeseries.resolution, TimeUnit):
            this_item_start_dt = timeseries[i-1].dt + timeseries.resolution
            this_item_end_dt   =  this_item_start_dt + timeseries.resolution
            this_item_start_t  = s_from_dt(this_item_start_dt) 
            this_item_end_t    = s_from_dt(this_item_end_dt)
        else:
            this_item_start_t = timeseries[i-1].t + timeseries.resolution
            this_item_end_t   = this_item_start_t + timeseries.resolution
            this_item_start_dt = dt_from_s(this_item_start_t, tz=timeseries.tz)
            this_item_end_dt = dt_from_s(this_item_end_t, tz=timeseries.tz )                    

        # Set time zone
        tz = timeseries[i-1].tz
        
        # Define TimePoints
        this_item_start_timePoint = TimePoint(this_item_start_t, tz=tz)
        this_item_end_timePoint = TimePoint(this_item_end_t, tz=tz)

        # Call model forecasting logic
        actual    = timeseries[i].data[key]
        predicted = self.forecaster._forecast(timeseries,
                                              timeseries.resolution,
                                              key,
                                              this_item_start_timePoint,
                                              this_item_end_timePoint,
                                              first_call=True,
                                              n=1,
                                              window_start = i-forecaster_window-1,
                                              raw=True)[key]
        
        return (actual, predicted)



    def _fit(self, timeseries, *args, stdevs=3, **kwargs):

        if len(timeseries.data_keys()) > 1:
            raise NotImplementedError('Multivariate time series are not yet supported')
        
    
        # Fit a forecaster               
        forecaster = PeriodicAverageForecaster()
        
        # Fit and save
        forecaster.fit(timeseries, *args, **kwargs)
        self.forecaster = forecaster
        
        # Evaluate the forecaster for one step ahead and get AEs
        AEs = []
        for key in timeseries.data_keys():
            
            for i, _ in enumerate(timeseries):
                
                forecaster_window = self.forecaster.data['window']
                
                if i <=  forecaster_window:    
                    continue
                
                actual, predicted = self.__get_actual_and_predicted(timeseries, i, key, forecaster_window)
                
                AEs.append(abs(actual-predicted))

        # Compute distribution for the AEs ans set the threshold
        from scipy.stats import norm
        mean, stdev = norm.fit(AEs)
        logger.info('Using {} standard deviations as anomaly threshold: {}'.format(stdevs, stdev*stdevs))
        
        # Set AE-based threshold
        self.AE_threshold = stdev*stdevs


    def _apply(self, timeseries, inplace=False, details=False, logs=False):
        
        if inplace:
            raise Exception('Anomaly detection cannot be run inplace')

        if len(timeseries.data_keys()) > 1:
            raise NotImplementedError('Multivariate time series are not yet supported')
        
        result_timeseries = timeseries.__class__()

        for key in timeseries.data_keys():
            
            for i, item in enumerate(timeseries):
                forecaster_window = self.forecaster.data['window']
                if i <=  forecaster_window:    
                    continue
                
                actual, predicted = self.__get_actual_and_predicted(timeseries, i, key, forecaster_window)

                AE = abs(actual-predicted)
                
                item = deepcopy(item)
                if AE > self.AE_threshold:
                    if logs:
                        logger.info('Detected anomaly for item starting @ {} ({}) with AE="{:.3f}..."'.format(item.t, item.dt, AE))
                    item.data['anomaly'.format(key)] = 1
                    if details:
                        item.data['AE_{}'.format(key)] = AE
                        item.data['predicted_{}'.format(key)] = predicted
                else:
                    item.data['anomaly'.format(key)] = 0
                    if details:
                        item.data['AE_{}'.format(key)] = AE
                        item.data['predicted_{}'.format(key)] = predicted

                result_timeseries.append(item)
        
        return result_timeseries 






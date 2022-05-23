import random
from timeseria.time import now_s
from timeseria.datastructures import DataTimePoint, DataTimePointSeries
import numpy as np
import pandas as pd
import random
from timeseria.datastructures import TimePoint, DataTimeSlot, DataTimeSlotSeries

# Set what to profile
use_case=5

# Log
print('Start profiling')

if use_case==1:
    dataTimePointSerie = DataTimePointSeries()
    prev_data = 30
    prev_t    = now_s()
    for i in range (1, 1000000):
        data = prev_data + random.randint(-10,10)/10.0
        t    = prev_t + 60
        dataTimePointSerie.append(DataTimePoint(t=t, data=data))
        prev_data = data
        prev_t    = t
        
if use_case==2:

    df = pd.DataFrame(np.random.randint(0,100,size=(1000000, 2)), columns=list('AB'))
    print(df)


if use_case==3:

    cols = ['c1', 'c2']
    df = pd.DataFrame(columns=cols, index=range(100000))
    print('looping...')
    prev_data = 30
    prev_t    = now_s()
    for i in range (1, 100000):
        data = prev_data + random.randint(-10,10)/10.0
        t    = prev_t + 60

        df.loc[i].c1 = t
        df.loc[i].c2 = data

        prev_data = data
        prev_t    = t

    print(df)


if use_case==4:
    time_series = DataTimeSlotSeries()
    #print('Start generating data')
    prev_data = 0
    prev_t    = now_s()
    #for i in range (1, 1000000):
    for i in range (1, 100000):
        data = prev_data + random.randint(-10,10)/10.0
        t    = prev_t + 60
        time_series.append(DataTimeSlot(start=TimePoint(t=t), end=TimePoint(t=t+60), data=[data]))
        prev_data = data
        prev_t    = t
    #print('Done generating data')
    

if use_case==5:
    print('Now generating data')
    start_t = now_s()
    time_series = DataTimePointSeries()
    for i in range (1, 100000):
        data = random.randint(-0,1)
        time_series.append(DataTimePoint(t=i, data=[data]))
    print('Done generating data')
    end_t = now_s()
    print(' -> elapsed: {}'.format(end_t-start_t))


    print('Now resampling at same frequency')
    start_t = now_s()
    time_series.resample(1)
    print('Done resampling')
    end_t = now_s()
    print(' -> elapsed: {}'.format(end_t-start_t))


#     print('Now resampling at x10 frequency')
#     start_t = now_s()
#     time_series.resample(10)
#     print('Done resampling')
#     end_t = now_s()
#     print(' -> elapsed: {}'.format(end_t-start_t))
# 
# 
#     print('Now resampling at /10 frequency')
#     start_t = now_s()
#     time_series.resample(0.1)
#     print('Done resampling')
#     end_t = now_s()
#     print(' -> elapsed: {}'.format(end_t-start_t))

    # Start profiling
    # Now generating data
    # Done generating data
    #  -> elapsed: 2
    # Now resampling at same frequency
    # Done resampling
    #  -> elapsed: 17
    # Now resampling at x10 frequency
    # Done resampling
    #  -> elapsed: 4
    # Now resampling at /10 frequency
    # You are upsampling, which is not well tested yet. Expect potential issues.
    # Done resampling
    #  -> elapsed: 133
    # Done profiling


    # Sat Mar 12 16:59:40 UTC 2022
    # Start profiling
    # Now generating data
    # Done generating data
    #  -> elapsed: 44
    # Now resampling at same frequency
    # Done resampling
    #  -> elapsed: 479
    # Done profiling
    #          48567879 function calls (48557828 primitive calls) in 530.175 seconds
    # 
    #    Ordered by: internal time
    # 
    #    ncalls  tottime  percall  cumtime  percall filename:lineno(function)
    #   4299877   87.457    0.000  150.125    0.000 datastructures.py:105(__getitem__)
    #  10428202   50.614    0.000   50.614    0.000 {built-in method builtins.isinstance}
    #   2299931   30.683    0.000  134.900    0.000 datastructures.py:1494(__next__)
    #   2599935   26.472    0.000   39.964    0.000 __init__.py:1424(debug)
    #         1   22.502   22.502  479.374  479.374 transformations.py:250(process)
    #   4299877   21.061    0.000   21.061    0.000 {function Series.__getitem__ at 0x7fc9683ad160}
    #   3999910   20.135    0.000   20.135    0.000 datastructures.py:391(t)
    #     99997   17.895    0.000  131.834    0.001 operations.py:114(__call__)
    #    599992   16.965    0.000   33.056    0.000 time.py:125(dt_from_s)
    #     99997   14.618    0.000  307.165    0.003 transformations.py:21(_compute_new)
    #   2599937   13.492    0.000   13.492    0.000 __init__.py:1689(isEnabledFor)
    #    299991   12.707    0.000   39.848    0.000 datastructures.py:632(data_keys)
    #    199996   10.553    0.000   46.217    0.000 datastructures.py:532(append)
    #    199996    9.020    0.000   61.193    0.000 datastructures.py:611(append)
    #   1799948    9.018    0.000    9.018    0.000 datastructures.py:459(data)
    #    399990    8.584    0.000   35.336    0.000 datastructures.py:414(dt)
    #         5    8.491    1.698   16.536    3.307 datastructures.py:559(tz)
    #    499981    8.380    0.000   13.946    0.000 units.py:330(__eq__)
    #     99997    8.246    0.000   65.796    0.001 utilities.py:183(compute_coverage)
    #     99997    7.083    0.000  103.106    0.001 utilities.py:248(compute_data_loss)
    #    199996    6.140    0.000   20.322    0.000 datastructures.py:49(append)
    #    899985    5.810    0.000    5.810    0.000 datastructures.py:402(tz)
    # 1146233/1145806    5.703    0.000    5.707    0.000 {built-in method builtins.len}
    #    599998    5.104    0.000    5.104    0.000 {method 'replace' of 'datetime.datetime' objects}
    #    199996    5.020    0.000   14.535    0.000 datastructures.py:433(__init__)
    #    999980    4.991    0.000    4.991    0.000 __init__.py:259(__str__)
    #    100000    4.958    0.000    9.027    0.000 units.py:372(_is_composite)
    #    699991    4.796    0.000    4.796    0.000 time.py:12(timezonize)
    #    816135    4.157    0.000    4.162    0.000 {built-in method builtins.getattr}
    #    199996    4.151    0.000    7.488    0.000 datastructures.py:342(__init__)
    #    599994    3.820    0.000    3.820    0.000 {built-in method utcfromtimestamp}
    #     99998    3.646    0.000   32.045    0.000 units.py:271(__add__)
    #     99998    3.568    0.000   25.654    0.000 units.py:512(shift_dt)
    #     99997    3.470    0.000   26.810    0.000 datastructures.py:1587(__len__)
    #    599982    3.162    0.000    3.162    0.000 datastructures.py:1489(__iter__)
    #    200004    3.148    0.000    8.127    0.000 time.py:141(s_from_dt)
    #    599994    3.106    0.000    3.106    0.000 {method 'astimezone' of 'datetime.datetime' objects}
    #    199994    3.086    0.000    5.066    0.000 datastructures.py:396(__gt__)
    #    600980    3.016    0.000    3.016    0.000 {method 'pop' of 'dict' objects}
    #    200004    2.993    0.000    4.012    0.000 {method 'timestamp' of 'datetime.datetime' objects}
    #    499981    2.615    0.000    2.615    0.000 units.py:378(value)
    #    399990    2.492    0.000    2.492    0.000 datastructures.py:464(data_loss)
    #         1    2.245    2.245    4.211    4.211 utilities.py:118(compute_validity_regions)
    #    199994    2.155    0.000   28.653    0.000 datastructures.py:1601(data_keys)
    #     99999    2.057    0.000    3.552    0.000 random.py:250(_randbelow_with_getrandbits)
    #         1    1.968    1.968  530.191  530.191 profiling.py:1(<module>)
    #    202096    1.802    0.000    1.802    0.000 {method 'format' of 'str' objects}
    #    100007    1.681    0.000    2.748    0.000 units.py:576(duration_s)
    #    300017    1.680    0.000    1.680    0.000 units.py:389(type)
    #    199996    1.619    0.000    1.619    0.000 datastructures.py:294(__init__)
    #    280443    1.395    0.000    1.395    0.000 {method 'append' of 'list' objects}
    #    101935    1.208    0.000    1.766    0.000 <frozen importlib._bootstrap>:389(parent)
    #         1    1.135    1.135    2.190    2.190 utilities.py:525(detect_sampling_interval)
    #     99999    1.113    0.000    4.665    0.000 random.py:200(randrange)
    #     99997    1.085    0.000    1.606    0.000 datastructures.py:1597(resolution)
    #     99998    1.079    0.000   33.124    0.000 units.py:300(__radd__)




# Log
print('Done profiling')

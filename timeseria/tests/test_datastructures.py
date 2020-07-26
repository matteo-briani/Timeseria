import unittest
import datetime
import os

from ..datastructures import Point, TimePoint, DataPoint, DataTimePoint
from ..datastructures import Slot, TimeSlot, DataSlot, DataTimeSlot
from ..datastructures import Series
from ..datastructures import Unit
from ..datastructures import PointSeries, DataPointSeries, TimePointSeries, DataTimePointSeries
from ..datastructures import SlotSeries, DataSlotSeries, TimeSlotSeries, DataTimeSlotSeries
from ..time import UTC, TimeUnit, dt

# Setup logging
import logging
logging.basicConfig(level=os.environ.get('LOGLEVEL') if os.environ.get('LOGLEVEL') else 'CRITICAL')


class TestSeries(unittest.TestCase):

    def test_Series(self):
        
        serie = Series(1,4,5)
        self.assertEqual(serie, [1,4,5])
        self.assertEqual(len(serie), 3)
        
        serie.append(8)
        self.assertEqual(serie, [1,4,5,8])
        self.assertEqual(len(serie), 4)  
        
        # Demo class that implements the __succedes__ operation
        class IntegerNumber(int):
            def __succedes__(self, other):
                if other+1 != self:
                    return False
                else:
                    return True

        one = IntegerNumber(1)
        two = IntegerNumber(2)
        three = IntegerNumber(3)

        self.assertTrue(two.__succedes__(one))
        self.assertFalse(one.__succedes__(two))
        self.assertFalse(three.__succedes__(one))

        with self.assertRaises(ValueError):
            Series(one, three)

        with self.assertRaises(ValueError):
            Series(three, two)

        Series(one, two, three)
        
        # TODO: do we want the following behavior? (cannot mix types  even if they are child classes)
        with self.assertRaises(TypeError):
            Series(one, two, three, 4)

        # Define a Series with fixed type
        class FloatSeries(Series):
            __TYPE__ = float

        with self.assertRaises(TypeError):
            FloatSeries(1,4,5, 'hello', None)

        with self.assertRaises(TypeError):
            FloatSeries(1,4,5)

        with self.assertRaises(TypeError):
            FloatSeries(1.0,4.0,None,5.0)
            
        float_serie = FloatSeries(1.0,4.0,5.0)
        self.assertEqual(float_serie, [1.0,4.0,5.0])
        self.assertEqual(len(float_serie), 3)



class TestPoints(unittest.TestCase):

    def test_Point(self):
        
        point = Point(1, 2)        
        self.assertEqual(point.coordinates[0],1)
        self.assertEqual(point.coordinates[1],2)
        
        # Access by index
        self.assertEqual(point[0],1)
        self.assertEqual(point[1],2)

        point_1 = Point(1, 2)
        point_2 = Point(1, 2)
        point_3 = Point(5, 3)

        self.assertEqual(point_1,point_2)
        self.assertNotEqual(point_1,point_3)


    def test_TimePoint(self):
        
        # Wrong init/casting

        with self.assertRaises(Exception):
            TimePoint()
        
        with self.assertRaises(Exception):
            TimePoint('hi')

        # Standard init (init/float)
        time_point = TimePoint(5)
        self.assertEqual(time_point.coordinates,(5,))
        self.assertEqual(time_point.coordinates[0],5)
        self.assertEqual(time_point.t,5)
        
        # Init using "t"
        time_point_init_t = TimePoint(t=5)
        self.assertEqual(time_point, time_point_init_t)
        
        # Init using naive "dt" (only in case someone uses without using timesera dt utility, i.e. from external timestamps) 
        time_point_init_dt = TimePoint(dt=datetime.datetime(1970,1,1,0,0,5))
        self.assertEqual(time_point_init_dt, time_point)
        self.assertEqual(str(time_point_init_dt.tz), 'UTC')

        # Init using "dt" with UTC timezone (timesera dt utility always add the UTC timezone)
        time_point_init_dt = TimePoint(dt=dt(1970,1,1,0,0,5))
        self.assertEqual(time_point_init_dt, time_point) 
        self.assertEqual(str(time_point_init_dt.tz), 'UTC')

        # Init using "dt" with Europe/Rome timezone (note that we create the dt at 1 AM and not at midnight for this test to pass) 
        time_point_init_dt = TimePoint(dt=dt(1970,1,1,1,0,5, tz='Europe/Rome'))
        self.assertEqual(time_point_init_dt, time_point_init_dt)         
        
        # Test standard with UTC time zone
        self.assertEqual(time_point.tz, UTC)
        self.assertEqual(type(time_point.tz), type(UTC))
        self.assertEqual(str(time_point.dt), '1970-01-01 00:00:05+00:00')

        # Test standard with Europe/Rome time zone
        time_point = TimePoint(t=1569897900, tz='Europe/Rome')
        self.assertEqual(str(time_point.tz), 'Europe/Rome')
        self.assertEqual(str(type(time_point.tz)), "<class 'pytz.tzfile.Europe/Rome'>")
        self.assertEqual(str(time_point.dt), '2019-10-01 04:45:00+02:00')

        # Cast from object extending the TimePoint
        class ExtendedTimePoint(TimePoint):
            pass
        extended_time_point = ExtendedTimePoint(10)
        time_point_catsted = TimePoint(extended_time_point)
        self.assertEqual(time_point_catsted.coordinates,(10,))


    def test_DataPoint(self):
        
        with self.assertRaises(Exception):
            DataPoint(data='hello')
        
        data_point = DataPoint(1, 2, data='hello')

        self.assertEqual(data_point.coordinates, (1,2)) 
        self.assertEqual(data_point.coordinates[0], 1)
        self.assertEqual(data_point.coordinates[1], 2)
        self.assertEqual(data_point.data,'hello')
        
        data_point_1 = DataPoint(1, 2, data='hello')
        data_point_2 = DataPoint(1, 2, data='hello')
        data_point_3 = DataPoint(1, 2, data='hola')
        
        self.assertEqual(data_point_1, data_point_2)
        self.assertNotEqual(data_point_1, data_point_3)


    def test_DataTimePoint(self):
        
        with self.assertRaises(Exception):
            DataTimePoint(x=1)

        with self.assertRaises(Exception):
            DataTimePoint(data='hello')

        with self.assertRaises(Exception):
            DataTimePoint(x=1, data='hello')

        data_time_point = DataTimePoint(t=6, data='hello')

        self.assertEqual(data_time_point.coordinates, (6,)) 
        self.assertEqual(data_time_point.t,6)
        self.assertEqual(data_time_point.data,'hello')
        

    def test_casting(self):
        data_time_point = DataTimePoint(t=6, data='hello')
        casted_data_time_point_1 = TimePoint(data_time_point)
        self.assertEqual(casted_data_time_point_1.t, 6) 
        casted_data_time_point_2 = TimePoint(5)
        self.assertEqual(casted_data_time_point_2.t, 5) 



class TestPointSeries(unittest.TestCase):


    def test_TimePointSeries(self):
        
        time_point_serie = TimePointSeries()
        time_point_serie.append(TimePoint(t=60))
        
        
        # Test for UTC time zone (autodetect)
        time_point_serie = TimePointSeries()
        time_point_serie.append(TimePoint(t=5))         
        self.assertEqual(time_point_serie.tz, UTC)
        self.assertEqual(type(time_point_serie.tz), type(UTC))
        time_point_serie.append(TimePoint(t=10)) 
        self.assertEqual(time_point_serie.tz, UTC)
        self.assertEqual(type(time_point_serie.tz), type(UTC))
        time_point_serie.append(TimePoint(t=15, tz='Europe/Rome'))
        self.assertEqual(time_point_serie.tz, UTC)
        self.assertEqual(type(time_point_serie.tz), type(UTC))

        # Change  tz
        time_point_serie.tz = 'Europe/Rome'
        self.assertEqual(str(time_point_serie.tz), 'Europe/Rome')
        self.assertEqual(str(type(time_point_serie.tz)), "<class 'pytz.tzfile.Europe/Rome'>")
        
        # Test for Europe/Rome time zone (set)
        time_point_serie = TimePointSeries(tz = 'Europe/Rome')
        self.assertEqual(str(time_point_serie.tz), 'Europe/Rome')
        self.assertEqual(str(type(time_point_serie.tz)), "<class 'pytz.tzfile.Europe/Rome'>")
        time_point_serie.append(TimePoint(t=5))
        self.assertEqual(str(time_point_serie.tz), 'Europe/Rome')
        self.assertEqual(str(type(time_point_serie.tz)), "<class 'pytz.tzfile.Europe/Rome'>")        
         
        # Test for Europe/Rome time zone  (autodetect)
        time_point_serie = TimePointSeries()
        time_point_serie.append(TimePoint(t=1569897900, tz='Europe/Rome')) 
        self.assertEqual(str(time_point_serie.tz), 'Europe/Rome')
        self.assertEqual(str(type(time_point_serie.tz)), "<class 'pytz.tzfile.Europe/Rome'>")
        time_point_serie.append(TimePoint(t=1569897910, tz='Europe/Rome')) 
        self.assertEqual(str(time_point_serie.tz), 'Europe/Rome')
        self.assertEqual(str(type(time_point_serie.tz)), "<class 'pytz.tzfile.Europe/Rome'>")
        time_point_serie.append(TimePoint(t=1569897920))
        self.assertEqual(time_point_serie.tz, UTC)
        self.assertEqual(type(time_point_serie.tz), type(UTC))
        time_point_serie.tz = 'Europe/Rome'
        self.assertEqual(str(time_point_serie.tz), 'Europe/Rome')
        self.assertEqual(str(type(time_point_serie.tz)), "<class 'pytz.tzfile.Europe/Rome'>")         


    def test_DataPointSeries(self):
        pass
        # TODO: either implement the "__suceedes__" for unidimensional DataPoints or remove it completely.
        #data_point_serie = DataPointSeries()
        #data_point_serie.append(DataPoint(x=60, data='hello'))
        #data_point_serie.append(DataPoint(x=61, data='hello'))


    def test_DataTimePointSeries(self):
        
        with self.assertRaises(TypeError):
            DataTimePointSeries(DataTimePoint(t=60, data=23.8),
                               DataTimePoint(t=120, data=24.1),
                               DataTimePoint(t=180, data=None))
            
        with self.assertRaises(ValueError):
            DataTimePointSeries(DataTimePoint(t=60, data=23.8),
                               DataTimePoint(t=30, data=24.1))

        with self.assertRaises(ValueError):
            DataTimePointSeries(DataTimePoint(t=60, data=23.8),
                               DataTimePoint(t=60, data=24.1))
        
        data_time_point_series = DataTimePointSeries(DataTimePoint(t=60, data=23.8),
                                                   DataTimePoint(t=120, data=24.1),
                                                   DataTimePoint(t=180, data=23.9),
                                                   DataTimePoint(t=240, data=23.1),
                                                   DataTimePoint(t=300, data=22.7))
                                                
        data_time_point_series.append(DataTimePoint(t=360, data=21.9))
        self.assertTrue(len(data_time_point_series), 6)
   

        data_time_point_series = DataTimePointSeries(DataTimePoint(t=60, data=23.8),
                                                   DataTimePoint(t=120, data=24.1),
                                                   DataTimePoint(t=240, data=23.1),
                                                   DataTimePoint(t=300, data=22.7))
        self.assertTrue(len(data_time_point_series), 5)

      
        # Try to append a different data type
        data_time_point_series = DataTimePointSeries(DataTimePoint(t=60, data=[23.8]))
        with self.assertRaises(TypeError):
            data_time_point_series.append(DataTimePoint(t=120, data={'a':56}))

        # Try to append the same data type but with different cardinality
        data_time_point_series = DataTimePointSeries(DataTimePoint(t=60, data=[23.8]))
        with self.assertRaises(ValueError):
            data_time_point_series.append(DataTimePoint(t=180, data=[23.8,31.3]))

        # Try to append the same data type but with different keys
        data_time_point_series = DataTimePointSeries(DataTimePoint(t=60, data={'a':56, 'b':67}))
        with self.assertRaises(ValueError):
            data_time_point_series.append(DataTimePoint(t=180, data={'a':56, 'c':67}))            



class TestUnit(unittest.TestCase):

    def test_Unit(self):      
        #print(Unit([1,2]))     
        self.assertEqual( (Point(1) + Unit(5)).coordinates[0], 6) 
        self.assertEqual( (TimePoint(1) + Unit(5)).coordinates[0], 6) 


class TestSlots(unittest.TestCase):

    def test_Slot(self):

        # A slot needs a start and an end
        with self.assertRaises(TypeError):
            Slot()
        with self.assertRaises(TypeError):
            Slot(start=Point(x=1))

        # A slot needs a start and and end of Point instance
        with self.assertRaises(TypeError):
            Slot(start=1, end=2) 

        # A slot needs a start and and end with the same dimension
        with self.assertRaises(ValueError):
            Slot(start=Point(1), end=Point(2,4))        

        # No zero-duration allowed:
        with self.assertRaises(ValueError):
            Slot(start=Point(1), end=Point(1))

        #print('\n')
        #print(Slot(start=Point(5), end=Point(7)))
        #print(Slot(start=Point(1,2), end=Point(3,5)).length)
        #print('\n')
        
        slot = Slot(start=Point(1), end=Point(2)) 
        self.assertEqual(slot.start,Point(1))
        self.assertEqual(slot.end,Point(2))
        
        slot_1 = Slot(start=Point(1), end=Point(2))
        slot_2 = Slot(start=Point(1), end=Point(2))
        slot_3 = Slot(start=Point(1), end=Point(3))
        
        self.assertEqual(slot_1,slot_2)
        self.assertNotEqual(slot_1,slot_3)
        
        # Length
        slot = Slot(start=Point(1.5), end=Point(4.7)) 
        self.assertEqual(slot.length, 3.2)

        # Slot using unit
        slot = Slot(start=Point(1.5), unit=Unit(3.2)) 
        self.assertEqual(slot.length, 3.2)


  
    def test_TimeSlot(self):

        # A time_slot needs TimePoints
        with self.assertRaises(TypeError):
            TimeSlot(start=Point(x=1), end=Point(x=2))

        # No zero-duration allowed:
        with self.assertRaises(ValueError):
            TimeSlot(start=TimePoint(t=1), end=TimePoint(t=1))

        time_slot = TimeSlot(start=TimePoint(t=1), end=TimePoint(t=2))
        self.assertEqual(time_slot.start.t,1)
        self.assertEqual(time_slot.end.t,2)

        time_slot_1 = TimeSlot(start=TimePoint(t=1), end=TimePoint(t=2))
        time_slot_2 = TimeSlot(start=TimePoint(t=2), end=TimePoint(t=3))
        time_slot_3 = TimeSlot(start=TimePoint(t=3), end=TimePoint(t=4))

        # Test succession
        self.assertTrue(time_slot_2.__succedes__(time_slot_1))
        self.assertFalse(time_slot_1.__succedes__(time_slot_2))
        self.assertFalse(time_slot_3.__succedes__(time_slot_1))
        
        # Duration
        self.assertEqual(time_slot_1.duration,1)

        # Time zone
        with self.assertRaises(ValueError):
            # ValueError: TimeSlot start and end must have the same time zone (got start.tz="Europe/Rome", end.tz="UTC")
            TimeSlot(start=TimePoint(t=0, tz='Europe/Rome'), end=TimePoint(t=60))
        TimeSlot(start=TimePoint(t=0, tz='Europe/Rome'), end=TimePoint(t=60, tz='Europe/Rome'))

        # Slot using unit
        time_slot = TimeSlot(start=TimePoint(0), unit=Unit(3600)) 
        self.assertEqual(time_slot.length, 3600)      
          

    def test_DataSlot(self):
        
        with self.assertRaises(Exception):
            DataSlot(start=Point(x=1), end=Point(x=2))
 
        with self.assertRaises(TypeError):
            DataSlot(data='hello')

        data_slot = DataSlot(start=Point(1), end=Point(2), data='hello')
        self.assertEqual(data_slot.start.coordinates[0],1)
        self.assertEqual(data_slot.end.coordinates[0],2)
        self.assertEqual(data_slot.data,'hello')

        data_slot_1 = DataSlot(start=Point(1), end=Point(2), data='hello')
        data_slot_2 = DataSlot(start=Point(1), end=Point(2), data='hello')
        data_slot_3 = DataSlot(start=Point(1), end=Point(2), data='hola')

        self.assertEqual(data_slot_1, data_slot_2)
        self.assertNotEqual(data_slot_1, data_slot_3)

        data_slot_with_coverage = DataSlot(start=Point(1), end=Point(2), data='hello', coverage=0.98)
        self.assertEqual(data_slot_with_coverage.coverage, 0.98)
        self.assertEqual(data_slot_with_coverage.coverage + data_slot_with_coverage.data_loss, 1) # Workaround 0.020000000000000018 != 0.2


    def test_DataTimeSlots(self):

        with self.assertRaises(Exception):
            DataTimeSlot(start=Point(x=1), end=Point(x=2))
 
        with self.assertRaises(TypeError):
            DataTimeSlot(data='hello')

        with self.assertRaises(TypeError):
            DataTimeSlot(start=Point(x=1), end=Point(x=2), data='hello')


        data_time_slot_ = DataTimeSlot(start=TimePoint(t=1), end=TimePoint(t=2), data='hello')
        self.assertEqual(data_time_slot_.start.t,1)
        self.assertEqual(data_time_slot_.end.t,2)
        self.assertEqual(data_time_slot_.data,'hello')

        data_time_slot_1 = DataTimeSlot(start=TimePoint(t=1), end=TimePoint(t=2), data='hello')
        data_time_slot_2 = DataTimeSlot(start=TimePoint(t=1), end=TimePoint(t=2), data='hello')
        data_time_slot_3 = DataTimeSlot(start=TimePoint(t=1), end=TimePoint(t=2), data='hola')

        self.assertEqual(data_time_slot_1, data_time_slot_2)
        self.assertNotEqual(data_time_slot_1, data_time_slot_3)



class TestSlotSeries(unittest.TestCase):

    def test_SlotSeries(self):

        with self.assertRaises(ValueError):
            # ValueError: Slot start and end dimensions must have the same dimension
            SlotSeries(Slot(start=Point(0), end=Point(10,20)))
            
        slot_series =  SlotSeries(Slot(start=Point(0), end=Point(10)))
        
        with self.assertRaises(ValueError):
            # Cannot add items with different units (I have "10.0" and you tried to add "11.0")
            slot_series.append(Slot(start=Point(10), end=Point(21)))
        slot_series.append(Slot(start=Point(10), end=Point(20)))
        
        # The unit is more used as a type..
        slot_series =  SlotSeries(Slot(start=Point(0), end=Point(10), unit='10-ish'))
        slot_series.append(Slot(start=Point(10), end=Point(21), unit='10-ish'))


    def test_TimeSlotSeries(self):
         
        time_slot_series = TimeSlotSeries()
        time_slot_series.append(TimeSlot(start=TimePoint(t=0), end=TimePoint(t=60)))
        with self.assertRaises(ValueError):
            time_slot_series.append(TimeSlot(start=TimePoint(t=0), end=TimePoint(t=60)))
        with self.assertRaises(ValueError):
            time_slot_series.append(TimeSlot(start=TimePoint(t=120), end=TimePoint(t=180)))

        time_slot_series.append(TimeSlot(start=TimePoint(t=60), end=TimePoint(t=120)))

        self.assertEqual(len(time_slot_series),2)
        self.assertEqual(time_slot_series[0].start.t,0)
        self.assertEqual(time_slot_series[0].end.t,60)
        self.assertEqual(time_slot_series[1].start.t,60)
        self.assertEqual(time_slot_series[1].end.t,120) 
        
        # Test time zone
        time_slot_series = TimeSlotSeries()
        time_slot_series.append(TimeSlot(start=TimePoint(t=0, tz='Europe/Rome'), end=TimePoint(t=60, tz='Europe/Rome')))
        with self.assertRaises(ValueError):
            time_slot_series.append(TimeSlot(start=TimePoint(t=60), end=TimePoint(t=210)))
        time_slot_series.append(TimeSlot(start=TimePoint(t=60, tz='Europe/Rome'), end=TimePoint(t=120, tz='Europe/Rome')))

        # Test unit
        self.assertEqual(time_slot_series.slot_unit, Unit(60.0))
        
 
    def test_DataSlotSeries(self):
        data_slot_series = DataSlotSeries()
        data_slot_series.append(DataSlot(start=Point(1), end=Point(2), data='hello'))
        data_slot_series.append(DataSlot(start=Point(2), end=Point(3), data='hola'))
        self.assertEqual(data_slot_series[0].start.coordinates[0],1)
        self.assertEqual(data_slot_series[0].end.coordinates[0],2)
        self.assertEqual(data_slot_series[0].data,'hello')

 
    def test_DataTimeSlotSeries(self):
         
        with self.assertRaises(TypeError):
            DataTimeSlotSeries(DataTimeSlot(start=TimePoint(t=60), end=TimePoint(t=120), data=23.8),
                               DataTimeSlot(start=TimePoint(t=120), end=TimePoint(t=180), data=24.1),
                               DataTimeSlot(start=TimePoint(t=180), end=TimePoint(t=240), data=None))

        with self.assertRaises(ValueError):
            DataTimeSlotSeries(DataTimeSlot(start=TimePoint(t=180), end=TimePoint(t=20), data=24.1),
                               DataTimeSlot(start=TimePoint(t=60), end=TimePoint(t=120), data=23.8))
 
             
        with self.assertRaises(ValueError):
            DataTimeSlotSeries(DataTimeSlot(start=TimePoint(t=60), end=TimePoint(t=120), data=23.8),
                               DataTimeSlot(start=TimePoint(t=180), end=TimePoint(t=20), data=24.1))
 
        with self.assertRaises(ValueError):
            DataTimeSlotSeries(DataTimeSlot(start=TimePoint(t=60), end=TimePoint(t=120), data=23.8),
                               DataTimeSlot(start=TimePoint(t=60), end=TimePoint(t=120), data=24.1))

        data_time_slot_series =  DataTimeSlotSeries(DataTimeSlot(start=TimePoint(t=60),  end=TimePoint(t=120), data=23.8),
                                                    DataTimeSlot(start=TimePoint(t=120), end=TimePoint(t=180), data=24.1),
                                                    DataTimeSlot(start=TimePoint(t=180), end=TimePoint(t=240), data=23.1))
                                                                                                 
                                                 
        data_time_slot_series.append(DataTimeSlot(start=TimePoint(t=240), end=TimePoint(t=300), data=22.7))
        self.assertTrue(len(data_time_slot_series), 4)

        # Try to append a different data type
        data_time_slot_series = DataTimeSlotSeries(DataTimeSlot(start=TimePoint(t=60), end=TimePoint(t=120), data=23.8))
        with self.assertRaises(TypeError):
            data_time_slot_series.append(DataTimeSlot(start=TimePoint(t=120), end=TimePoint(t=180), data={'a':56}))

        # Try to append the same data type but with different cardinality
        data_time_slot_series = DataTimeSlotSeries(DataTimeSlot(start=TimePoint(t=60), end=TimePoint(t=120), data=[23.8]))
        with self.assertRaises(ValueError):
            data_time_slot_series.append(DataTimeSlot(start=TimePoint(t=120), end=TimePoint(t=180), data=[23.8,31.3]))

        # Try to append the same data type but with different keys
        data_time_slot_series = DataTimeSlotSeries(DataTimeSlot(start=TimePoint(t=60), end=TimePoint(t=120), data={'a':56, 'b':67}))
        with self.assertRaises(ValueError):
            data_time_slot_series.append(DataTimeSlot(start=TimePoint(t=120), end=TimePoint(t=180), data={'a':56, 'c':67}))            

        # Test slot_unit
        self.assertEqual(data_time_slot_series.slot_unit, Unit(60.0))
        self.assertEqual(DataTimeSlotSeries(DataTimeSlot(start=TimePoint(t=60), end=TimePoint(t=120), data=23.8, unit=TimeUnit('60s'))).slot_unit, TimeUnit('60s'))
        
        
    def test_cannge_timezone_DataTimeSlotSeries(self):
        from ..time import timezonize
        data_time_slot_series_UTC =  DataTimeSlotSeries(DataTimeSlot(start=TimePoint(t=60),  end=TimePoint(t=120), data=23.8),
                                                        DataTimeSlot(start=TimePoint(t=120), end=TimePoint(t=180), data=24.1),
                                                        DataTimeSlot(start=TimePoint(t=180), end=TimePoint(t=240), data=23.1))

        data_time_slot_series_UTC.change_timezone('Europe/Rome')
        self.assertEqual(data_time_slot_series_UTC.tz, timezonize('Europe/Rome'))
        self.assertEqual(data_time_slot_series_UTC[0].tz, timezonize('Europe/Rome'))
        self.assertEqual(data_time_slot_series_UTC[0].start.tz, timezonize('Europe/Rome'))
        self.assertEqual(data_time_slot_series_UTC[0].end.tz, timezonize('Europe/Rome'))
        





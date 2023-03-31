from picosdk.ps2000 import ps2000 as ps
from picosdk.PicoDeviceEnums import picoEnum as enums
from picosdk.functions import adc2mV, assert_pico2000_ok
#from picosdk.PicoDeviceStructs import picoStruct as struct
import numpy as np
import ctypes

from src.utils import invert_dict

class PicoScope():
    def __init__(self, unit, description='', timebase=7, chRange='50MV'):
        self.unit = unit
        self.serial = unit.serial
        self.description = description
        self.chRange = range_dict[chRange]
        self.status = {}
        self.timebase = timebase
        


    
    def open_ps(self):
        self.status["openUnit"] = ps.ps2000_open_unit(self.serial, None)
        self.chandle = ctypes.c_int16(self.status["openUnit"])       
        return self.status["openUnit"]
        
    def setup_channels(self):
        ''' setup channels A and B using the values stored in the class'''
        # handle = chandle
        # channel = PS2000_CHANNEL_A = 0
        # enabled = 1
        # coupling type = PS2000_DC = 1
        # range = PS2000_50MV = 2
        # analogue offset = 0 V
        self.status["setChA"] = ps.ps2000_set_channel(self.chandle, 0, 1, 1, self.chRange)
        assert_pico2000_ok(self.status["setChA"])
        self.status["setChB"] = ps.ps2000_set_channel(self.chandle, 0, 1, 1, self.chRange)
        assert_pico2000_ok(self.status["setChB"])   
        
    def setup_simple_trigger(self, channel=0):
        # handle = chandle
        # source = PS2000_CHANNEL_A = 0
        # threshold = 1024 ADC counts
        # direction = PS2000_RISING = 0
        # delay = 0 s
        # auto Trigger = 1000 ms
        self.status["trigger"] = ps.ps2000_set_trigger(self.chandle, 0, 2**15+0, 0, 0, 0)

    def get_timebase(self, timebase):
        # Set number of pre and post trigger samples to be collected
        preTriggerSamples = 1000
        postTriggerSamples = 1000
        maxSamples = preTriggerSamples + postTriggerSamples
        
        # Get timebase information
        # WARNING: When using this example it may not be possible to access all Timebases as all channels are enabled by default when opening the scope.  
        # To access these Timebases, set any unused analogue channels to off.
        # handle = chandle
        # timebase = 8 = timebase
        # no_of_samples = maxSamples
        # pointer to time_interval = ctypes.byref(timeInterval)
        # pointer to time_units = ctypes.byref(timeUnits)
        # oversample = 1 = oversample
        # pointer to max_samples = ctypes.byref(maxSamplesReturn)
        timebase = timebase
        timeInterval = ctypes.c_int32()
        timeUnits = ctypes.c_int32()
        oversample = ctypes.c_int16(1)
        maxSamplesReturn = ctypes.c_int32()
        self.status["getTimebase"] = ps.ps2000_get_timebase(self.chandle, timebase, maxSamples, ctypes.byref(timeInterval), ctypes.byref(timeUnits), oversample, ctypes.byref(maxSamplesReturn))
        assert_pico2000_ok(self.status["getTimebase"]) 
        return {"maxSamples": maxSamples, "timebase": timebase, "timeInterval_ns": timeInterval, "time_unit_str": time_units_dict[timeUnits.value], "time_unit": timeUnits, "oversample": oversample, "masSample": maxSamplesReturn}

    def find_optimal_timebase(self, delta = 1000):
        # time in ns, 1000ns = 1 microsecond
        timebase = 1
        while True:
            tb_dict = self.get_timebase(timebase)
            if tb_dict['timeInterval_ns'].value > delta:
                break
            timebase += 1
        return timebase - 1

    def block_capture(self):
        # Run block capture
        # handle = chandle
        # no_of_samples = maxSamples
        # timebase = timebase
        # oversample = oversample
        # pointer to time_indisposed_ms = ctypes.byref(timeIndisposedms)
        timebase_dict = self.get_timebase(self.timebase)
        timeIndisposedms = ctypes.c_int32()
        self.status["runBlock"] = ps.ps2000_run_block(self.chandle, timebase_dict['maxSamples'], self.timebase, timebase_dict['oversample'], ctypes.byref(timeIndisposedms))
        assert_pico2000_ok(self.status["runBlock"])

        # Check for data collection to finish using ps5000aIsReady
        ready = ctypes.c_int16(0)
        check = ctypes.c_int16(0)
        while ready.value == check.value:
            self.status["isReady"] = ps.ps2000_ready(self.chandle)
            ready = ctypes.c_int16(self.status["isReady"])

        # Create buffers ready for data
        bufferA = (ctypes.c_int16 * timebase_dict['maxSamples'])()
        bufferB = (ctypes.c_int16 * timebase_dict['maxSamples'])()
        
        # Get data from scope
        # handle = chandle
        # pointer to buffer_a = ctypes.byref(bufferA)
        # pointer to buffer_b = ctypes.byref(bufferB)
        # poiner to overflow = ctypes.byref(oversample)
        # no_of_values = cmaxSamples
        cmaxSamples = ctypes.c_int32(timebase_dict['maxSamples'])
        self.status["getValues"] = ps.ps2000_get_values(self.chandle, ctypes.byref(bufferA), ctypes.byref(bufferB), None, None, ctypes.byref(timebase_dict['oversample']), cmaxSamples)
        assert_pico2000_ok(self.status["getValues"])
        
        # find maximum ADC count value
        maxADC = ctypes.c_int16(32767)
        
        # convert ADC counts data to mV
        adc2mVChA =  adc2mV(bufferA, self.chRange, maxADC)
        adc2mVChB =  adc2mV(bufferB, self.chRange, maxADC)
        
        # Create time data
        time = np.linspace(0, (cmaxSamples.value -1) * timebase_dict['timeInterval_ns'].value, cmaxSamples.value)
        return time, adc2mVChA[:], adc2mVChB[:]
                
    def stop_capture(self):
        self.status["stop"] = ps.ps2000_stop(self.chandle)
        return assert_pico2000_ok(self.status["stop"])
    def close_ps(self):
        self.status["close"] = ps.ps2000_close_unit(self.chandle)
        return assert_pico2000_ok(self.status["close"])
    
    def set_memory_segments(self):
        '''potentially usefull to set a max number of samples to save. See section 3.29'''
        pass
        
        
    

    def get_chRange(self):
        return invert_dict(range_dict)[self.chRange]
    def __repr__(self):
        representation = '''scope: {}
description: {}
channel range: {}'''.format(
            self.serial, 
            self.description,
            self.get_chRange())
        return representation

time_units_dict = {
    0: "fs",
    1: "ps",
    2: "ns",
    3: "mus",
    4: "ms",
    5: "s",
}
range_dict = {
    "20MV": 1,
    "50MV": 2,
    "100MV": 3,
    "200MV": 4,
    "500MV": 5,
    "1V": 6,
    "2V": 7,
    "5V": 8,
    "10V": 9,
    "20V": 10}
#https://www.picotech.com/download/manuals/picoscope-2000-series-programmers-guide.pdf

'''
   def setup_trigger(self):
        'Sets an OR trigger between channel A and B'
        dont_care = ps.PS2000A_TRIGGER_STATE['PS2000A_CONDITION_DONT_CARE']
        trigger_true = ps.PS2000A_TRIGGER_STATE['PS2000A_CONDITION_TRUE']
        nConditions = 2  
        channelA = enums.PICO_CHANNEL["PICO_CHANNEL_A"]
        channelB = enums.PICO_CHANNEL["PICO_CHANNEL_B"]
        conditions = (struct.PICO_CONDITION * 2)()
        conditions[0] = struct.PICO_CONDITION(channelA, enums.PICO_TRIGGER_STATE["PICO_CONDITION_TRUE"])
        conditions[1] = struct.PICO_CONDITION(channelB, enums.PICO_TRIGGER_STATE["PICO_CONDITION_TRUE"])
        self.status["setTriggerChannelConditions"] = ps.ps2000aSetTriggerChannelConditions(
                self.chandle,
                ctypes.byref(conditions),
                nConditions)
        
        
        directions = (struct.PICO_DIRECTION * 2)()
        directions[0]= struct.PICO_DIRECTION(channelA, 
                                             enums.PICO_THRESHOLD_DIRECTION["PICO_RISING"],
                                             enums.PICO_THRESHOLD_MODE["PICO_LEVEL"])
        directions[1]= struct.PICO_DIRECTION(channelB, 
                                             enums.PICO_THRESHOLD_DIRECTION["PICO_RISING"], 
                                             enums.PICO_THRESHOLD_MODE["PICO_LEVEL"])
        nDirections = 2
        print(directions[0])
        self.status["setTriggerChannelDirections"] = ps.ps2000aSetTriggerChannelDirections(chandle,ctypes.byref(directions),nDirections)
        assert_pico2000_ok(status["setTriggerChannelDirections"])

        channelProperties = (struct.PICO_TRIGGER_CHANNEL_PROPERTIES * 2)()
        #channelProperties[0] = struct.PICO_TRIGGER_CHANNEL_PROPERTIES(mV2adc(1000,channelRange,maxADC), 0, 0, 0, channelA)
        #channelProperties[1] = struct.PICO_TRIGGER_CHANNEL_PROPERTIES(mV2adc(1000,channelRange,maxADC), 0, 0, 0, channelB)
        #nChannelProperties = 2
        #autoTriggerMicroSeconds = 1000000
        #self.status["setTriggerChannelProperties"] = ps.ps2000aSetTriggerChannelProperties(chandle, 
        #                                            ctypes.byref(channelProperties),nChannelProperties,0,autoTriggerMicroSeconds)
        #assert_pico2000_ok(status["setTriggerChannelProperties"])
        
'''
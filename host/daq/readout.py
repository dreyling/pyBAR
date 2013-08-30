import logging
import struct
import itertools
import time
from threading import Thread, Event, Timer
from Queue import Queue
#from multiprocessing import Process as Thread
#from multiprocessing import Event
#from multiprocessing import Queue

from utils.utils import get_float_time

from SiLibUSB import SiUSBDevice

logging.basicConfig(level=logging.INFO, format = "%(asctime)s [%(levelname)-8s] (%(threadName)-10s) %(message)s")

class Readout(object):
    def __init__(self, device, data_filter = None):
        if isinstance(device, SiUSBDevice):
            self.device = device
        else:
            raise ValueError('Device object is not compatible')
        if data_filter != None:
            if hasattr(data_filter, '__call__'):
                self.data_filter = data_filter
            else:
                raise ValueError('Filter object is not callable')
        else:
            self.data_filter = self.no_filter
        #self.filtered_data_words = None
        #self.data_words = None
        self.worker_thread = None
        self.data_queue = Queue()
        self.stop_thread_event = Event()
        self.stop_thread_event.set()
        self.readout_interval = 0.05
        self.rx_base_address = dict([(idx, addr) for idx, addr in enumerate(range(0x8600, 0x8200, -0x0100))])
        self.sram_base_address = dict([(idx, addr) for idx, addr in enumerate(range(0x8100, 0x8200, 0x0100))])
    
    def start(self, reset_rx = False, empty_data_queue = True, reset_sram_fifo = True):
        if self.worker_thread != None:
            raise RuntimeError('Thread is not None')
        if reset_rx:
            self.reset_rx()
        if empty_data_queue:
            self.data_queue.empty()
        if reset_sram_fifo:
            self.reset_sram_fifo()
        self.stop_thread_event.clear()
        self.worker_thread = Thread(target=self.worker)
        logging.info('Starting readout')
        self.worker_thread.start()
    
    def stop(self, timeout = 10.0):
        if self.worker_thread == None:
            raise RuntimeError('Thread is None')
        if timeout > 0:
            timeout_event = Event()
            timeout_event.clear()
            
            def set_timeout_event(timeout_event, timeout):
                timer = Timer(timeout, timeout_event.set)
                timer.start()
            
            timeout_thread = Thread(target=set_timeout_event, args=[timeout_event, timeout])
            timeout_thread.start()
            
            fifo_size = self.get_sram_fifo_size()
            old_fifo_size = -1
            while (old_fifo_size != fifo_size or fifo_size != 0) and not timeout_event.wait(1.5*self.readout_interval):
                old_fifo_size = fifo_size
                fifo_size = self.get_sram_fifo_size()
            if timeout_event.is_set():
                logging.warning('Waiting for empty SRAM FIFO: timeout after %.1f second(s)' % timeout)
            else:
                timeout_event.set()
            timeout_thread.join()
        self.stop_thread_event.set()
        self.worker_thread.join()
        self.worker_thread = None
        logging.info('Stopped readout')
    
    def print_readout_status(self):
        logging.info('Data queue size: %d' % self.data_queue.qsize())
        logging.info('SRAM FIFO size: %d' % self.get_sram_fifo_size())
        logging.info('RX FIFO sync status:         %s', " | ".join(["OK".rjust(3) if status == True else "BAD".rjust(3) for status in self.get_rx_sync_status()]))
        logging.info('RX FIFO discard counter:     %s', " | ".join([repr(count).rjust(3) for count in self.get_rx_fifo_discard_count()]))
        logging.info('RX FIFO 8b10b error counter: %s', " | ".join([repr(count).rjust(3) for count in self.get_rx_8b10b_error_count()]))
    
    def worker(self):
        '''Reading thread to continuously reading SRAM
        
        Worker thread function uses read_once()
        ''' 
        while not self.stop_thread_event.wait(self.readout_interval): # TODO: this is probably what you need to reduce processor cycles
            try:
                self.device.lock.acquire()
                #print 'read from thread' 
                filtered_data_words = self.read_once()
                self.device.lock.release()
                #map(self.data_queue.put, filtered_data_words)
                #itertools.imap(self.data_queue.put, filtered_data_words)
                raw_data = list(filtered_data_words)
                if len(raw_data)>0:
                    self.data_queue.put({'timestamp':get_float_time(), 'raw_data':raw_data, 'error':0})
            except Exception:
                self.stop_thread_event.set()
                continue
                        
    def read_once(self):
        '''Read single to read SRAM once
        
        can be used without threading
        '''
        # TODO: check fifo status (overflow) and check rx status (sync) once in a while

        fifo_size = self.get_sram_fifo_size()
        if fifo_size%2 == 1: # sometimes a read happens during writing, but we want to have a multiplicity of 32 bits
            fifo_size-=1
            #print "FIFO size odd"
        if fifo_size > 0:
            fifo_data = self.device.FastBlockRead(4*fifo_size/2)
            #print 'fifo raw data:', fifo_data
            data_words = struct.unpack('>'+fifo_size/2*'I', fifo_data)
            #print 'raw data words:', data_words
            #self.filtered_data_words = [i for i in data_words if self.filter]
            self.filtered_data_words = self.data_filter(data_words)
            for filterd_data_word in self.filtered_data_words: 
                yield filterd_data_word
    
    def set_filter(self, data_filter = None):
        if data_filter == None:
                self.data_filter = self.no_filter
        else:
            if hasattr(data_filter, '__call__'):
                self.data_filter = data_filter
            else:
                raise ValueError('Filter object is not callable')

    def reset_sram_fifo(self):
        logging.info('Resetting SRAM FIFO')
        self.device.WriteExternal(address = self.sram_base_address[0], data = [0])
        if self.get_sram_fifo_size() != 0:
            logging.warning('SRAM FIFO size not zero')
        
    def get_sram_fifo_size(self):
        retfifo = self.device.ReadExternal(address = self.sram_base_address[0]+1, size = 3)
        return struct.unpack('I', retfifo.tostring() + '\x00' )[0] # TODO: optimize, remove tostring() ?
                                                
    def reset_rx(self, index = None):
        logging.info('Resetting RX')
        if index == None:
            index = self.rx_base_address.iterkeys()
        filter(lambda i: self.device.WriteExternal(address = self.rx_base_address[i], data = [0]), index)
    # since WriteExternal returns nothing, filter returns empty list

    def get_rx_sync_status(self, index = None):
        if index == None:
            index = self.rx_base_address.iterkeys()
        return map(lambda i: True if (self.device.ReadExternal(address = self.rx_base_address[i]+1, size = 1)[0])&0x1 == 1 else False, index)

    def get_rx_8b10b_error_count(self, index = None):
        if index == None:
            index = self.rx_base_address.iterkeys()
        return map(lambda i: self.device.ReadExternal(address = self.rx_base_address[i]+4, size = 1)[0], index)

    def get_rx_fifo_discard_count(self, index = None):
        if index == None:
            index = self.rx_base_address.iterkeys()
        return map(lambda i: self.device.ReadExternal(address = self.rx_base_address[i]+5, size = 1)[0], index)

    def no_filter(self, words):
        for word in words:
            yield word
            
    def data_record_filter(self, words):
        for word in words:
            if (word & 0x00FFFFFF) >= 131328 and (word & 0x00FFFFFF) <= 10572030:
                yield word
        
    def data_header_filter(self, words):
        for word in words:
            header = struct.unpack(4*'B', struct.pack('I', word))[2]
            if header == 233:
                yield word
                
    def tlu_data_filter(self, words):
        for word in words:
            if 0x80000000 == (word & 0x80000000):
                yield word
                
    def get_col_row(self, words):
        for item in self.data_record_filter(words):
            yield ((item & 0xFE0000)>>17), ((item & 0x1FF00)>>8)
            
    def get_row_col(self, words):
        for item in self.data_record_filter(words):
            yield ((item & 0x1FF00)>>8), ((item & 0xFE0000)>>17)
            
    def get_col_row_tot(self, words):
        for item in self.data_record_filter(words):
            yield ((item & 0xFE0000)>>17), ((item & 0x1FF00)>>8), ((item & 0x000F0)>>4) # col, row, ToT1
            if (item & 0x0000F) != 15:
                yield ((item & 0xFE0000)>>17), ((item & 0x1FF00)>>8)+1, (item & 0x0000F) # col, row+1, ToT2
                
    def get_tot(self, data):
        for item in self.data_record_filter(data):
            yield ((item & 0x000F0)>>4) # ToT1
            if (item & 0x0000F) != 15:
                yield (item & 0x0000F) # ToT2

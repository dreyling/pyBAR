# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#


cnfg_yaml = """
transfer_layer:
  - name  : ETH
    type  : SiTcp
    init:
        ip : "192.168.22.16"
        udp_port : 4660
        tcp_port : 24
        tcp_connection : True

hw_drivers:
  - name      : gpio_drv
    type      : gpio
    interface : ETH
    base_addr : 0x9000
    size      : 8

  - name      : CMD
    type      : cmd_seq
    interface : ETH
    base_addr : 0x0000

  - name      : CH0
    type      : fei4_rx
    interface : ETH
    base_addr : 0x8600

  - name      : M26_RX1
    type      : m26_rx
    interface : ETH
    base_addr : 0xa000

  - name      : M26_RX2
    type      : m26_rx
    interface : ETH
    base_addr : 0xa010

  - name      : M26_RX3
    type      : m26_rx
    interface : ETH
    base_addr : 0xa020

  - name      : M26_RX4
    type      : m26_rx
    interface : ETH
    base_addr : 0xa030

  - name      : M26_RX5
    type      : m26_rx
    interface : ETH
    base_addr : 0xa040

  - name      : M26_RX6
    type      : m26_rx
    interface : ETH
    base_addr : 0xa050

  - name      : SRAM
    type      : sram_fifo
    interface : ETH
    base_addr : 0x200000000
    base_data_addr : 0x100000000

registers:
  - name        : GPIO_LED
    type        : StdRegister
    hw_driver   : gpio_drv
    size        : 8
    fields:
      - name    : LED
        size    : 8
        offset  : 7
"""

import time
from basil.dut import Dut
import sys

readout_channel = sys.argv[1]

chip = Dut(cnfg_yaml)
chip.init()

#for i in range(8):
#    chip['GPIO_LED']['LED'] = 0x01 << i
#    chip['GPIO_LED'].write()
#    print('LED:', chip['GPIO_LED'].get_data())
#    #time.sleep(1)

print 'START'
chip['M26_RX1'].reset()
chip['M26_RX2'].reset()
chip['M26_RX3'].reset()
chip['M26_RX4'].reset()
chip['M26_RX5'].reset()
chip['M26_RX6'].reset()

print 'get_fifo_size', chip['SRAM'].get_fifo_size()
channels = ['M26_RX1', 'M26_RX2', 'M26_RX3', 'M26_RX4', 'M26_RX5', 'M26_RX6']
if readout_channel == '0':
    chls = [channels[0]]
elif readout_channel == '1':
    chls = [channels[1]]
elif readout_channel == '2':
    chls = [channels[2]]
elif readout_channel == '3':
    chls = [channels[3]]
elif readout_channel == '4':
    chls = [channels[4]]
elif readout_channel == '5':
    chls = [channels[5]]
else:
    chls = channels

print "channels activated:", chls

for ch in chls:
    chip[ch].set_en(True)

time.sleep(0.01)

for ch in chls:
    chip[ch].set_en(False)
    print chip[ch].get_lost_count(), ch

ret = chip['SRAM'].get_fifo_size(), chip['SRAM'].get_fifo_size()/4
print 'XXX', ret
ret = chip['SRAM'].get_data()
for i, r in enumerate(ret):
    if i > 1000 and i < 1100:
        if (r & 0x00010000) >> 16 == 1:
            print "Frame start"
        print i, hex(r), 'id', (r & 0x00F00000) >>20, 'start', (r & 0x00010000) >> 16, 'data', hex(r & 0x000FFFFF)

for i, r in enumerate(ret):
    if (r & 0x00010000) >> 16 == 1:
        print "Frame start"
        for ii in range(4):

            print i+ii, hex(ret[i+ii]), 'id', (ret[i+ii] & 0x00F00000) >>20, 'start', (ret[i+ii] & 0x00010000) >> 16, 'data', hex(ret[i+ii] & 0x000FFFFF)

print "DATA FORMAT"
print "HEADER(2bit=0x20) + PLANEID(4bit) + 3'b000 + FRAME_START(1bit) + DATA(16bit)"


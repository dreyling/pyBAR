# pyBAR firmware for [Mimosa pixel telescope](https://telescopes.desy.de/)

Allows continuous full configuation and data taking for single FE-I4 trigger plane and six MIMOSA26 planes. Includes JTAG, TLU and TDC modules.

The MMC3 board is based on [Enclustra Mercury KX1](http://www.enclustra.com/en/products/fpga-modules/mercury-kx1/) module.
The Firmware make use of [Basil](https://github.com/SiLab-Bonn/basil) framework and free [SiTcp](http://sitcp.bbtech.co.jp/) Ethernet module (v08).

![MMC3 board](m26_mmc3.jpg "MMC3 Board")


## Hardware

* Enclustra Mercury KX1 plus MMC3 carrier board
* powering via USB or 5V power supply due to jumper configuration
* Jumpers for RJ45 ports on the carrier board, see pictures
* Bonn cables: The original firmware is written to use the Mimosa pin assignment on the AUX board side and the standard Ethernet pin assignment on the MMC3 side. Thus, modified cables has to be used: Swap pin 4 and 6 only at the Mimosa side.
* attached heatsink to FPGA chip (all temperatures +- 1°C due to environment)
    * temperature w/o heatsink: 39.0 °C (stand-by), 59.0 °C (programmed)
    * temperature with heatsink: 39.0 °C (stand-by), 52.5 °C (programmed)

## Firmware

* basil (v2.4.6) and pyBAR (development)
* SiTCP v08
* generated bitfiles in ```bitfiles/```
    * ```170904_mmc3_m26_ip22subnet.bit```
    * ```170931_mmc3_m26_eth_default.bit```
    * ```170911_mmc3_m26_ip22subnet.prm``` (for memory boot)
    * ```170911_mmc3_m26_ip22subnet.mcs``` (for memory boot)
* setting up the memory for automatic boot
    * generate bootable memory file(s) from a bitfile by using the Tcl command: ```write_cfgmem -format mcs -interface spix1 -size 64 -loadbit "up 0x0 /opt/silab/pyBAR/firmware/mmc3_m26_desy/vivado/mmc3_m26_eth.runs/impl_1/mmc3_m26_eth.bit" -file mmc3_m26_eth.mcs```
        * option ```-interface spix1``` has to match the [design constraints](https://github.com/dreyling/pyBAR/blob/7ca2a5f46e5062f5f9b9d21f015741e44e7f3138/firmware/mmc3_m26_desy/src/mmc3.xdc#L238)
        * option ```-size 64``` is given in bytes and has to match the size of the memory, here 512 Mbit
    * add flash memory in Vivado Hardware Manager: QSPI Flash Type is S25FL512S
    * uploading mcs- and prm-files to flash memory (right-click on memory device in Hardware manger) using the options ```Pull-Up``` for ```State of non-config mem I/O pins``` which matches the [design constraints](https://github.com/dreyling/pyBAR/blob/7ca2a5f46e5062f5f9b9d21f015741e44e7f3138/firmware/mmc3_m26_desy/src/mmc3.xdc#L102)
    * set the jumper on the MMC3 board ```FPGA_MODE```
    * after powering the MMC, it takes ~25 sec until the FPGA is programmed

## Software

* Hardware Layers: Basil
    * fixed bug in ```basil/TL/SiTcp.py```, line 96: ```logging.warning("SiTcp:write - Invalid address %d" % hex(addr))``` has to be string wildcard ```%s```
* DAQ: pyBAR
* Interpretation: ```pyBAR_mimosa26_interpreter```
* read-out of Agilent power:
    * connect Agilent to pybar-PC using a USB to serial adapter (9pin, RS232)
    * adjusting the configuration ```dut_mmc3_m26_eth.yaml``` 

## Example

* upload bitfile (Vivado plus JTAG module)
* adjust configuration yaml-files
* running scan: ```python scan_telescope_m26.py```

## ToDo and to test:

- [ ] using QSPI flash for autoamtic bitfile-upload (incl. possible resistor modification of FPGA carrier board)
- [ ] JTAGging of Mimosa26 (incl. only for one sensor w/o JTAG distr. board)
- [ ] understanding: Basil hardware layer, yaml configuration and pybar software usage
- [ ] testing ```testbeam_analysis``` 

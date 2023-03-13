import board

import busio
import digitalio
import supervisor
import json

class E220LoRa:

    BAUDRATE = {
        1200: "000",
        2400: "001",
        4800: "010",
        9600: "011",
        19200: "100",
        38400: "101",
        57600: "110",
        115200: "111",
    }
    BAUDRATEINV = {v: k for k, v in BAUDRATE.items()}
    SERPARBIT = {"8N1": "00", "8O1": "01", "8E1": "10", "00": "11"}
    SERPARBITINV = {v: k for k, v in SERPARBIT.items()}
    AIRDATARATE = {
        "0.3k": "000", # 2.4k
        "1.2k": "001", # 2.4k
        "2.4k": "010",
        "4.8k": "011",
        "9.6k": "100",
        "19.2k": "101",
        "38.4k": "110",
        "62.5k": "111",
    }
    AIRDATARATEINV = {v: k for k, v in AIRDATARATE.items()}

    SUBPACKSETING = {"200b": "00", "128b": "01", "64b": "10", "32b": "11"}
    SUBPACKSETINGINV = {v: k for k, v in SUBPACKSETING.items()}
    RSSIAMBIENT = {"OFF": "0", "ON": "1"}
    RSSIAMBIENTINV = {v: k for k, v in RSSIAMBIENT.items()}
    TRANSMITTINGPOWER = {"22dBm": "00", "17dBm": "01", "13dBm": "10", "10dBm": "11"}
    TRANSMITTINGPOWERINV = {v: k for k, v in TRANSMITTINGPOWER.items()}

    ENABLERSSI = {"OFF": "0", "ON": "1"}
    ENABLERSSIINV = {v: k for k, v in ENABLERSSI.items()}
    TRANSMISSIONMETHOD = {"Transparent": "0", "Fixed": "1"}
    TRANSMISSIONMETHODINV = {v: k for k, v in TRANSMISSIONMETHOD.items()}
    LBTENABLE = {"OFF": "0", "ON": "1"}
    LBTENABLEINV = {v: k for k, v in LBTENABLE.items()}
    WORCYCLE = {
        500: "000",
        1000: "001",
        1500: "010",
        2000: "011",
        2500: "100",
        3000: "101",
        3500: "110",
        4000: "111",
    }
    WORCYCLEINV = {v: k for k, v in WORCYCLE.items()}

    def __init__(self, auxPin, txE220pin, rxE220pin, m1pin, m0pin, bpsRate=9600):
        self.uart = busio.UART(rxE220pin, txE220pin, baudrate=bpsRate)
        self.bRate = bpsRate

        self.auxPin = digitalio.DigitalInOut(auxPin)
        self.auxPin.direction = digitalio.Direction.INPUT
        self.auxPin.pull = digitalio.Pull.UP

        self.m0pin = digitalio.DigitalInOut(m0pin)
        self.m0pin.direction = digitalio.Direction.OUTPUT

        self.m1pin = digitalio.DigitalInOut(m1pin)
        self.m1pin.direction = digitalio.Direction.OUTPUT

    def listenUART(self,size):
        data = self.uart.read(size)
        if data is not None:
            return data
        return 0

    def wait(self, wt):
        t = supervisor.ticks_ms()  # нужна ли проверка на переполнениее?
        while supervisor.ticks_ms() - t < wt:
            pass

    def sendCMD(self, cmd):
        self.uart.write(cmd)
        if self.waitAux():
            msg = self.listenUART(16)
            if msg == 0:
                print("module not response")
                return None
        return msg

    def sendMSG(self,mesg):
        self.uart.write(mesg)
        if self.waitAux():
            print("MSG send!")

    def waitAux(self):
        t = supervisor.ticks_ms()
        while not self.auxPin.value:
            if supervisor.ticks_ms() - t > 5000:
                print("time out error AUX pin")
                return False
        self.wait(20)
        return True

    def setConfigMode(self):
        if (self.m0pin.value != True) or (self.m1pin.value != True):
            self.m0pin.value = True
            self.m1pin.value = True
            self.wait(30)
            if self.waitAux():
                print("set configuration mode!")

    def setNormalMode(self):
        if (self.m0pin.value != False) or (self.m1pin.value != False):
            self.m0pin.value = False
            self.m1pin.value = False
            self.wait(30)
            if self.waitAux():
                print("set normal mode!")

    def setWOR_SendMode(self):
        if (self.m0pin.value != True) or (self.m1pin.value != False):
            self.m0pin.value = True
            self.m1pin.value = False
            self.wait(30)
            if self.waitAux():
                print("set WOR sending mode")

    def setWOR_ReceivMode(self):
        if (self.m0pin.value != False) or (self.m1pin.value != True):
            self.m0pin.value = False
            self.m1pin.value = True
            self.wait(30)
            if self.waitAux():
                print("set WOR receiving mode")

    def setChan(self, ch):
        self.setConfigMode()
        cmd = bytes([0xC0, 0x04, 0x01])
        cmd = cmd + ch.to_bytes(1, "big")
        rsp = self.sendCMD(cmd)
        if rsp is not None:
            if rsp[0] == 193:  # 193 = 0xC1 DATASHEET INFO
                if (rsp[1] == cmd[1]) and (rsp[2] == cmd[2]) and (rsp[3] == cmd[3]):
                    print("Chan set to", rsp[3])

    def readChan(
        self,
    ):  # не уверен что необходим функционал получения конкретного парамтера, из-за малого количесва параметров проверку можно осуществлять получением всем параметров
        self.setConfigMode()
        cmd = bytes([0xC1, 0x04, 0x01])
        rsp = self.sendCMD(cmd)
        if rsp is not None:
            if rsp[0] == 193:
                if (rsp[1] == cmd[1]) and (rsp[2] == cmd[2]):
                    print("Channel:", rsp[3])

    def setAdress(self, Hbyt, Lbyt):  # high and low adress 0-255 , 0- 255
        self.setConfigMode()
        cmd = bytes([0xC0, 0x00, 0x02])
        hAdress = Hbyt.to_bytes(1, "big")
        lAdress = Lbyt.to_bytes(1, "big")
        cmd = cmd + hAdress + lAdress
        rsp = self.sendCMD(cmd)
        if rsp is not None:
            if rsp[0] == 193:  # 193 = 0xC1 DATASHEET INFO
                if (
                    (rsp[1] == cmd[1])
                    and (rsp[2] == cmd[2])
                    and (rsp[3] == cmd[3])
                    and (rsp[4] == cmd[4])
                ):
                    print("High Adress set to", rsp[3])
                    print("Low Adress set to ", rsp[4])

    def getModulParam(self):
        self.setConfigMode()
        cmd = bytes([0xC1, 0x00, 0x06])
        rsp = self.sendCMD(cmd)
        if rsp is not None:
            if rsp[0] == 193:
                if (rsp[1] == cmd[1]) and (rsp[2] == cmd[2]):
                    print("High Module Adress    :", rsp[3])
                    print("Low Module Adress     :", rsp[4])
                    reg0 = "{0:08b}".format(rsp[5])
                    uartbps = self.BAUDRATEINV.get(reg0[0:3])
                    paritybit = self.SERPARBITINV.get(reg0[3:5])
                    airDataRait = self.AIRDATARATEINV.get(reg0[5:])
                    print("Uart Serial Port Rate :", uartbps)
                    print("Serial Parity Bit     :", paritybit)
                    print("Air Data Rate         :", airDataRait)
                    reg1 = "{0:08b}".format(rsp[6])
                    subPackSetting = self.SUBPACKSETINGINV.get(reg1[0:2])
                    RSSI_nois = self.RSSIAMBIENTINV.get(reg1[2:3])
                    txPower = self.TRANSMITTINGPOWERINV.get(reg1[6:])
                    print("Sub-Packet Setting    :", subPackSetting)
                    print("RSSI Ambient Noise    :", RSSI_nois)
                    print("Transmitting Power    :", txPower)
                    print("Channel               :", rsp[7])
                    reg3 = "{0:08b}".format(rsp[8])
                    rssiEnable = self.ENABLERSSIINV.get(reg3[0:1])
                    transMeth = self.TRANSMISSIONMETHODINV.get(reg3[1:2])
                    lbtEnable = self.LBTENABLEINV.get(reg3[3:4])
                    worCycl = self.WORCYCLEINV.get(reg3[5:])
                    print("Enable RSSI           :", rssiEnable)
                    print("Transmission Method   :", transMeth)
                    print("LBT Enable            :", lbtEnable)
                    print("WOR Cycle             :", worCycl)
            else:
                print("module not response")

    def setModulSpeedParam(self, uartSpeed, SerialParBit, AirDataRate):
        self.setConfigMode()
        cmd = bytes([0xC0, 0x02, 0x01])
        uspeed = self.BAUDRATE.get(uartSpeed)
        SPB = self.SERPARBIT.get(SerialParBit)
        ADrate = self.AIRDATARATE.get(AirDataRate)
        arg = int("0b" + uspeed + SPB + ADrate).to_bytes(1, "big")
        cmd = cmd + arg
        print("setModulSpeedParam Command:", cmd)
        rsp = self.sendCMD(cmd)
        if rsp is not None:
            if rsp[0] == 193:  # 193 = 0xC1 DATASHEET INFO
                if (rsp[1] == cmd[1]) and (rsp[2] == cmd[2]) and (rsp[3] == cmd[3]):
                    print("set modul SPEED param done!")

    def setModulTxParam(self, SubPackSet, RSSIAmbi_nois, txPower):
        self.setConfigMode()
        cmd = bytes([0xC0, 0x03, 0x01])
        subPack = self.SUBPACKSETING.get(SubPackSet)
        rssiAmb = self.RSSIAMBIENT.get(RSSIAmbi_nois)
        txP = self.TRANSMITTINGPOWER.get(txPower)
        arg = int("0b" + subPack + rssiAmb + "000" + txP).to_bytes(1, "big")
        cmd = cmd + arg
        print("setModulTxParam Command:", cmd)
        rsp = self.sendCMD(cmd)
        if rsp is not None:
            if rsp[0] == 193:  # 193 = 0xC1 DATASHEET INFO
                if (rsp[1] == cmd[1]) and (rsp[2] == cmd[2]) and (rsp[3] == cmd[3]):
                    print("set modul TX param done!")

    def setModulConfigParam(self, RSSI, TransMetod, LBT, WOR_cycle):
        self.setConfigMode()
        cmd = bytes([0xC0, 0x05, 0x01])
        rsi = self.ENABLERSSI.get(RSSI)
        trnsmtd = self.TRANSMISSIONMETHOD.get(TransMetod)
        lbte = self.LBTENABLE.get(LBT)
        wor = self.WORCYCLE.get(WOR_cycle)
        arg = int("0b" + rsi + trnsmtd + "0" + lbte + "0" + wor).to_bytes(1, "big")
        cmd +=  arg
        rsp = self.sendCMD(cmd)
        if rsp is not None:
            if rsp[0] == 193:  # 193 = 0xC1 DATASHEET INFO
                if (rsp[1] == cmd[1]) and (rsp[2] == cmd[2]) and (rsp[3] == cmd[3]):
                    print("set modul CONFIG param done!")

    def sendP2P(self,targetAdressHigh, targetAdressLow , targetChan , msg ):
        self.setNormalMode()
        cmd = []
        cmd.append(targetAdressHigh)
        cmd.append(targetAdressLow)
        cmd.append(targetChan)
        message = json.dumps(msg)
        print(message)
        for i in range(len(message)):
            cmd.append(ord(message[i]))
        self.sendMSG(bytes(cmd))
        self.wait(200)

    def sendBroadcast(self , targetChan , msg ):
        self.setNormalMode()
        cmd = []
        cmd.append(255)
        cmd.append(255)
        cmd.append(targetChan)
        spec_msg = [len(msg) + 5,msg]
        print("specmsg =",spec_msg)
        message = json.dumps(spec_msg)
        for i in range(0,len(message)):
            if i == 1:
                cmd.append(spec_msg[0])
            elif i == 2:
                continue
            else:
                cmd.append(ord(message[i]))
        self.sendMSG(bytes(cmd))
        print(cmd)
        self.wait(1500)

    def listening(self):
        self.setNormalMode()
        sta = self.listenUART(1)
        if sta == b'[':
            msg_size = self.listenUART(1)
            msg = sta + self.listenUART(msg_size[0])

            rssi = self.listenUART(1)
            rssi_correct = -(256 - rssi[0])
           # print("rssi", rssi_correct)
            newmsg = ''
            for i in range(len(msg)):
                newmsg += chr(msg[i])

          #  print("msg =",msg)
           # print("Newmsg =",newmsg)
            decode_msg = json.loads(msg)
            
          #  print("decode_msg =",decode_msg)
          #  print(decode_msg[0])
            self.wait(200)
            return decode_msg
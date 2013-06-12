#! /usr/bin/env python
''' Copyright (c) 2013 Potential Ventures Ltd
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. '''

# Set log level to benefit from Scapy warnings
from scapy.all import *
from packet_util import *

message_types = {
    'T' : "Timestamp",
    'S' : "System Event",
    'R' : "Stock Delivery",
    'H' : "Stock Trading Action",
    'Y' : "Reg SHO Short Sale Price Test",
    'L' : "Maktet Participant Position",
    'A' : "Add order without MPID",
    'F' : "Add order with MPID",
    'E' : "Order Executed",
    'C' : "Order Executed with Price",
    'X' : "Order Cancel",
    'D' : "Order Delete",
    'U' : "Order Replace",
    'P' : "Trade Message",
    'Q' : "Cross Trade Message",
    'B' : "Broken Trade",
    'I' : "Net Order Imbalance",
    'N' : "Retail Price Improvement Indicator"
}

event_codes = {
    'O' : "Start of Message",
    'S' : "Start of System Hours",
    'Q' : "Start of Market Hours",
    'M' : "End of Market Hours",
    'E' : "End of System Hours",
    'C' : "End of Message",
    'A' : "Emergency Market Condition - HALT",
    'R' : "Emergency Market Condition - Quote Only Period",
    'B' : "Emergency Market Condition - Resumption",
}

market_catagories = {
    'N' : "New York Stock Exchange (NYSE)",
    'A' : "NYSE Amex",
    'P' : "NYSE Arca",
    'Q' : "NASDAQ Global Select Market",
    'R' : "NASDAQ Global Market",
    'S' : "NASDAQ Capital Market",
    'Z' : "BATS BZX Exchange"
}

status_indicators = {
    'D' : "Deficient",
    'E' : "Delinquent",
    'Q' : "Bankrupt",
    'S' : "Suspended",
    'G' : "Deficient and Bankrupt",
    'H' : "Deficient and Delinquent",
    'J' : "Delinquent and Bankrupt",
    'K' : "Deficient, Delinquent and Bankrupt",
    ' ' : "Compliant"
}

trading_state = {
    'H' : "Halted Across all U.S",
    'P' : "Paused Across all U.S",
    'Q' : "Quotation only period",
    'T' : "Trading on NASDAQ"
}

market_mode = {
    'N' : "Normal",
    'P' : "Passive",
    'S' : "Syndicate",
    'R' : "Pre-Syndicate",
    'L' : "Penalty"
}

market_state = {
    'A' : "Active",
    'E' : "Excused/Withdrawn",
    'W' : "Withdrawn",
    'S' : "Suspended",
    'D' : "Deleted"
}

buy_sell = {
    'B' : "Buy",
    'S' : "Sell"
}

cross_type = {
    'O' : "NASDAQ Opening Cross",
    'C' : "NASDAQ Closing Cross",
    'H' : "Cross for IPO halted/pause securities",
    'I' : "NASDAQ Cross Network: Intrdat/Postclose"
}

imbalance_dir = {
    'B' : "Buy Imbalance",
    'S' : "Sell Imbalance",
    'N' : "No Imbalance",
    'O' : "Insufficent orders"
}

price_var = {
    'L' : "Less than 1%",
    '1' : "1 - 1.99%",
    '2' : "2 - 2.99%",
    '3' : "3 - 3.99%",
    '4' : "4 - 4.99%",
    '5' : "5 - 5.99%",
    '6' : "6 - 6.99%",
    '7' : "7 - 7.99%",
    '8' : "8 - 8.99%",
    '9' : "9 - 9.99%",
    'A' : "10 - 19.99%",
    'B' : "20 - 29.99%",
    'C' : "30% or greater",
    ' ' : "Cannot calculate"
}

interest_flag = {
    'B' : "RPI Orders available on the buy side",
    'S' : "RPT Orders available on the sell side",
    'A' : "RPI Orders available on both sides",
    'N' : "Not RPI orders available"
}

class ItchMessage(Packet):
    name = "ITCH 4.1"

class ItchTimeStamp(ItchMessage):
    name = "ITCH 4.1 Timestamp"
    fields_desc = [
        CharEnumField("message", 'T', message_types),
        IntField("seconds", 0)]

class ItchEvent(ItchMessage):
    name = "ITCH 4.1 System Event Message"
    fields_desc = [
        CharEnumField("header", 'S', message_types),
        IntField("nanoseconds", 0),
        CharEnumField("eventcode", " ", event_codes)]

class ItchStockDelivery(ItchMessage):
    name = "ITCH 4.1 Stock Delivery"
    fields_desc = [
        CharEnumField("header", 'R', message_types),
        IntField("nanoseconds", 0),
        StrFixedLenField("stock", "        ", length=8),
        CharEnumField("mktcat", ' ', market_catagories),
        CharEnumField("status", ' ', status_indicators),
        IntField("lotsize", 0),
        CharEnumField("lotsonly", ' ', {'Y' : "Only round lots", 'N' : "Odd/Mixed allowed"})]

class ItchStockAction(ItchMessage):
    name = "ITCH 4.1 Stock Trading Action"
    fields_desc = [
        CharEnumField("header", 'H', message_types),
        IntField("nanoseconds", 0),
        StrFixedLenField("stock", "        ", length=8),
        CharEnumField("state", ' ', trading_state),
        ByteField("reserved", 0),
        StrFixedLenField("reason", "    ", length=4)]

class ItchRegSHO(ItchMessage):
    name = "ITCH 4.1 Reg SHO Short Sale Price Test Restricted Indicator"
    fields_desc = [
        CharEnumField("header", 'Y', message_types),
        IntField("nanoseconds", 0),
        StrFixedLenField("stock", "        ", length=8),
        CharEnumField("reason", ' ', {'0' : "No test", '1' : "SHO on", '2' : "SHO remains"})]

class ItchMarketPartPos(ItchMessage):
    name = "ITCH 4.1 Matket Participant Position"
    fields_desc = [
        CharEnumField("header", 'L', message_types),
        IntField("nanoseconds", 0),
        StrFixedLenField("mpid", "    ", length=4),
        StrFixedLenField("stock", "        ", length=8),
        CharEnumField("primary", ' ', {'Y' : "Primary Maker", 'N' : "Non-primary"}),
        CharEnumField("mkmode", ' ' , market_mode),
        CharEnumField("mkstate", ' ', market_state)]

class ItchAddOrder(ItchMessage):
    name = "ITCH 4.1 Add order without MPID"
    fields_desc = [
        CharEnumField("header", 'A', message_types),
        IntField("nanoseconds", 0),
        LongDecimalField("order", 0, 8),
        CharEnumField("type", ' ', buy_sell),
        IntField("shares", 0),
        StrFixedLenField("stock", "        ", length=8),
        IntField("price", 0)]

class ItchAddOrderMPID(ItchMessage):
    name = "ITCH 4.1 Add order with MPID"
    fields_desc = [
        CharEnumField("header", 'F', message_types),
        IntField("nanoseconds", 0),
        LongDecimalField("order", 0, 8),
        CharEnumField("type", ' ', buy_sell),
        IntField("shares", 0),
        StrFixedLenField("stock", "        ", length=8),
        IntField("price", 0),
        StrFixedLenField("attrubution", "    ", length=4)]

class ItchOrderExec(ItchMessage):
    name = "ITCH 4.1 Order Executed"
    fields_desc = [
       CharEnumField("header", 'E', message_types),
       IntField("nanoseconds", 0),
       LongDecimalField("order", 0, 8),
       IntField("shares", 0),
       LongDecimalField("matchnum", 0, 8)]

class ItchOrderExecPrice(ItchMessage):
    name = "ITCH 4.1 Order Executed with price"
    fields_desc = [
        CharEnumField("header", 'C', message_types),
        IntField("nanoseconds", 0),
        LongDecimalField("order", 0, 8),
        IntField("shares", 0),
        LongDecimalField("matchnum", 0, 8),
        CharEnumField("printable", ' ', {'Y' : "Printable", 'N' : "Non-Printable"}),
        IntField("price", 0)]

class ItchOrderCancel(ItchMessage):
    name = "ITCH 4.1 Order Cancle"
    fields_desc = [
        CharEnumField("header", 'X', message_types),
        IntField("nanoseconds", 0),
        LongDecimalField("order", 0, 8),
        IntField("cancelnum", 0)]

class ItchOrderDelete(ItchMessage):
    name = "ITCH 4.1 Order Delete"
    filds_desc = [
        CharEnumField("header", 'D', message_types),
        IntField("nanoseconds", 0),
        LongDecimalField("order", 0, 8)]

class ItchOrderReplace(ItchMessage):
    name = "ITCH 4.1 Order Replace"
    fields_desc = [
        CharEnumField("header", 'U', message_types),
        IntField("nanoseconds", 0),
        LongDecimalField("oldorder", 0, 8),
        LongDecimalField("neworder", 0, 8),
        IntField("shares", 0),
        IntField("price", 0)]

class ItchTrade(ItchMessage):
    name = "ITCH 4.1 Trade Message Non-Cross"
    fields_desc = [
        CharEnumField("header", 'P', message_types),
        IntField("nanoseconds", 0),
        LongDecimalField("order", 0, 8),
        CharEnumField("type", ' ', buy_sell),
        IntField("shares", 0),
        StrFixedLenField("stock", "        ", length=8),
        IntField("price", 0),
        LongDecimalField("matchnum", 0, 8)]

class ItchTradeCross(ItchMessage):
    name = "ITCH 4.1 Cross Trade Message"
    fields_desc = [
        CharEnumField("header", 'P', message_types),
        IntField("nanoseconds", 0),
        LongDecimalField("shares", 0, 8),
        StrFixedLenField("stock", "        ", length=8),
        IntField("crossprice", 0),
        LongDecimalField("matchnum", 0, 8),
        CharEnumField("ctype", ' ', cross_type)]

class ItchBrokenTrade(ItchMessage):
    name = "ITCH 4.1 Broken Trade"
    fields_desc = [
        CharEnumField("header", 'B', message_types),
        IntField("nanoseconds", 0),
        LongDecimalField("matchnum", 0, 8)]

class ItchNOII(ItchMessage):
    name = "ITCH 4.1 NOII"
    fields_desc = [
        CharEnumField("header", 'B', message_types),
        IntField("nanoseconds", 0),
        LongDecimalField("paired", 0, 8),
        CharEnumField("Imdir", ' ', imbalance_dir),
        StrFixedLenField("stock", "        ", length=8),
        IntField("farprice", 0),
        IntField("nearprice", 0),
        IntField("currref", 0),
        CharEnumField("ctype", ' ', cross_type),
        CharEnumField("var", ' ', price_var)]

class ItchRPII(ItchMessage):
    name = "ITCH 4.1 RPII"
    fields_desc = [
        CharEnumField("header", 'B', message_types),
        IntField("nanoseconds", 0),
        StrFixedLenField("stock", "        ", length=8),
        CharEnumField("intflag", ' ', interest_flag)]

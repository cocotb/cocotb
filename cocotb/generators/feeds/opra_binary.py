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
import logging
logging.getLogger("scapy").setLevel(1)

from scapy.all import *


# TODO: Full implemenation

class DenominatorField(): pass

class OPRAValueField():
    """Representation of a value, adjusted for the appropriate denominator"""
    def __init__(self, denominator):
        pass




def hdr_to_msg_len(pkt):
    if pkt.header.msg_category == "a": return 35
    if pkt.header.msg_category == "d": return 22
    if pkt.header.msg_category == "f": return 64
    if pkt.header.msg_category == "k": raise Exception("Don't support msg category k yet")
    if pkt.header.msg_category == "q": raise Exception("Don't support msg category q yet")
    if pkt.header.msg_category == "Y": return 19
    if pkt.header.msg_category == "C": raise Exception("Don't support msg category C yet")
    if pkt.header.msg_category == "H": raise Exception("Don't support msg category H yet")
    raise Exception("Uknown message category %c" % chr(msg.category))

#class OPRAEquityAndIndexLastSale(Packet):
    #name = "EILS"
    #fields_desc = [
        #OPRABinaryMessageHeader(Header, None),
        #StrFixedLenField("symbol", "     ", length=5),
        #StrFixedLenField("padding", " ", length=26)]
        #ByteField("reserved", 0),
        #3ByteField("expiration", 0),
        #DenominatorField("strike_denom", default),
        #OPRAValueField("strike_price", "strike_denom"),
        #IntField("volume", 0),
        #DenominatorField("premium_denom", default),
        #OPRAValueField("premium_price", "premium_denom"),
        #IntField("trade_id", 0),
        #IntField("reserved1", 0)]


class OPRABinaryMessageHeader(Packet):
    name = "MSG"
    fields_desc = [
        StrFixedLenField("participant_id", " ", length=1),
        StrFixedLenField("msg_category", " ", length=1),
        StrFixedLenField("msg_type", " ", length=1),
        StrFixedLenField("msg_indicator", " ", length=1)]


class OPRAMessage(Packet):
    fields_desc = [
        OPRABinaryMessageHeader("header", None),
        StrFixedLenField("symbol", "     ", length=5),
        StrLenField("length", "", length_from=hdr_to_msg_len)] # Doesn't actually exist in protocol


class OPRABinaryBlock(Packet):
    name = "OPRA"
    fields_desc = [
        ByteField("version", 0),
        ShortField("block_size", 0),
        StrFixedLenField("feed_indicator", "O", length=1),
        CharEnumField("retransmission_indicator", " ", {" " : "Original", "V": "Retransmitted"}),
        ByteField("reserved", 0),
        IntField("block_sequence_number", 0),
        ByteField("nmsgs", 0),
        LongField("timestamp", 0),
        XShortField("checksum", 0),
        PacketListField("msgs", [], OPRAMessage)]
        #FieldLenField("length", None, count_of="msgs")]





# The Participant ID field is a 1 Byte, ASCII character that identifies the Participant or Processor that initiated the message
participant_ids = {
    'A' : "NYSE AMEX",
    'B' : "Boston Options Exchange",
    'C' : "Chicago Board Options Exchange",
    'I' : "International Securities Exchange",
    'M' : "Miami International Securities Exchange",
    'N' : "NYSE ARCA",
    'O' : "Options Price Reporting Authority",
    'Q' : "NASDAQ Stock Market",
    'T' : "NASDAQ OMX BX Options*",
    'W' : "C2",
    'X' : "NASDAQ OMX PHLX",
    'Z' : "BATS"}



# The Message Category field is a 1 Byte, ASCII character, either an upper or lower case letter.
message_category_ids = {
    'a' : "EQUITY AND INDEX LAST SALE",
    'd' : "OPEN INTEREST",
    'f' : "EQUITY AND INDEX END OF DAY SUMMARY",
    'k' : "LONG EQUITY AND INDEX QUOTE",
    'q' : "SHORT EQUITY AND INDEX QUOTE",
    'C' : "ADMINISTRATIVE",
    'H' : "CONTROL",
    'Y' : "UNDERLYING VALUE MESSAGE"}

message_types_category_a = {
    " " : "REGULAR" ,
    "A" : "CANC"    ,
    "B" : "OSEQ"    ,
    "C" : "CNCL"    ,
    "D" : "LATE"    ,
    "E" : "CNCO"    ,
    "F" : "OPEN"    ,
    "G" : "CNOL"    ,
    "H" : "OPNL"    ,
    "I" : "AUTO"    ,
    "J" : "REOP"    ,
    "K" : "AJST"    ,
    "L" : "SPRD"    ,
    "M" : "STDL"    ,
    "N" : "STPD"    ,
    "O" : "CSTP"    ,
    "P" : "BWRT"    ,
    "Q" : "CMBO"    ,
    "R" : "SPIM"    ,
    "S" : "ISOI"    ,
    "T" : "BNMT"    ,
    "X" : "XMPT"    ,}



type_2_description = {
    "REGULAR" : "Indicates that the transaction was a regular sale and was made without stated conditions.",
    "CANC"    : "Transaction previously reported (other than as the last or opening report for the particular option contract) is now to be cancelled.",
    "OSEQ"    : "Transaction is being reported late and is out of sequence; i.e., later transactions have been reported for the particular option contract.",
    "CNCL"    : "Transaction is the last reported for the particular option contract and is now cancelled.",
    "LATE"    : "Transaction is being reported late, but is in the correct sequence; i.e., no later transactions have been reported for the particular option contract.",
    "CNCO"    : "Transaction was the first one (opening) reported this day for the particular option contract. Although later transactions have been reported, this transaction is now to be cancelled.",
    "OPEN"    : "Transaction is a late report of the opening trade and is out of sequence; i.e., other transactions have been reported for the particular option contract.",
    "CNOL"    : "Transaction was the only one reported this day for the particular option contract and is now to be cancelled.",
    "OPNL"    : "Transaction is a late report of the opening trade, but is in the correct sequence; i.e., no other transactions have been reported for the particular option contract.",
    "AUTO"    : "Transaction was executed electronically. Prefix appears solely for information; process as a regular transaction.",
    "REOP"    : "Transaction is a reopening of an option contract in which trading has been previously halted. Prefix appears solely for information; process as a regular transaction.",
    "AJST"    : "Transaction is an option contract for which the terms have been adjusted to reflect a stock dividend, stock split, or similar event. Prefix appears solely for information; process as a regular transaction.",
    "SPRD"    : "Transaction represents a trade in two options in the same class (a buy and a sell in the same class). Prefix appears solely for information; process as a regular transaction.",
    "STDL"    : "Transaction represents a trade in two options in the same class (a buy and a sell in a put and a call). Prefix appears solely for information; process as a regular transaction.",
    "STPD"    : "Transaction is the execution of a sale at a price agreed upon by the floor personnel involved, where a condition of the trade is that it reported following a non-stopped trade of the same series at the same price.",
    "CSTP"    : "Cancel stopped transaction.",
    "BWRT"    : "Transaction represents the option portion of an order involving a single option leg (buy or sell of a call or put) and stock. Prefix appears solely for information: process as a regular transaction.",
    "CMBO"    : "Transaction represents the buying of a call and the selling of a put for the same underlying stock or index. Prefix appears solely for information; process as a regular transaction.",
    "SPIM"    : "Transaction was the execution of an order which was \"stopped\" at a price that did not constitute a Trade-Through on another market at the time of the stop. Process like a normal transaction except don't update \"last\".",
    "ISOI"    : "Transaction was the execution of an order identified as an Intermarket Sweep Order. Process like normal transaction",
    "BNMT"    : "Transaction reflects the execution of a \"benchmark trade\". A \"Benchmark Trade\" is a trade resulting from the matching of \"Benchmark Orders\". A \"Benchmark Order\" is an order for which the price is not based, directly or indirectly, on the quote price of the option at the time of the order's execution and for which the material terms were not reasonably determinable at the time a commitment to trade the order was made. Process like a normal transaction except don't update \"last\".",
    "XMPT"    : "Transaction is Trade Through Exempt. The transaction should be treated like a regular sale."}


message_types_category_h = {
    "A"   :  "Start of Test Cycle",
    "B"   :  "End of Test Cycle",
    "C"   :  "Start of Day",
    "D"   :  "Good Morning",
    "E"   :  "Start of Summary",
    "F"   :  "End of Summary",
    "G"   :  "Early Market Close",
    "H"   :  "End of Transaction Reporting",
    "I"   :  "Good Night",
    "J"   :  "End of Day",
    "K"   :  "Reset Block Sequence Number",
    "L"   :  "Start of Open Interest",
    "M"   :  "End of Open Interest",
    "N"   :  "Line Integrity",
    }

message_types_category_kq = {
    " "   :  "Regular Trading",
    "F"   :  "Non-Firm Quote",
    "R"   :  "Rotation",
    "T"   :  "Trading Halted",
    "A"   :  "Eligible for Automatic Execution",
    "B"   :  "Bid contains Customer Trading Interest",
    "O"   :  "Offer contains Customer Trading Interest",
    "C"   :  "Both Bid and Offer contain Customer Trading Interest",
    "X"   :  "Offer side of Quote Not Firm; Bid Side Firm",
    "Y"   :  "Bid Side of Quote Not Firm; Offer Side Firm",
    }

message_types_category_Y = {
    " "   :  "Index based on Last Sale",
    "I"   :  "Index based on Bid and Offer",
    }

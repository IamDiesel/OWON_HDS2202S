local json = require "json"

local owon_bulk = Proto("OWON_HDS2202S", "OWON_HDS2202S_USB_SCPI_PROTOCOL")
--inspired by: https://github.com/matthiasbock/logicport-wireshark-dissector/blob/master/logicport.lua#L10
--copy script to C:\Users\<USER>\AppData\Roaming\Wireshark\plugins
--if folder does not exist open help->folders (inside wireshark)
--json.lua from cloudshark is needed to parse header: https://github.com/cloudshark/wireshark-plugin/tree/master
--copy json.lua to plugin folder

local field_scpi_data_in = ProtoField.string(
    "owon_bulk.scpi_data_in",
    "Oscilloscope Output",
    base.none
)
local field_scpi_meas_data_in = ProtoField.string(
    "owon_bulk.scpi_meas_data_in",
    "Oscilloscope Measurement",
    base.none
)
local field_scpi_header_in = ProtoField.string(
    "owon_bulk.scpi_header_in",
    "Oscilloscope Header",
    base.none
)
local field_scpi_data_out = ProtoField.string(
    "owon_bulk.scpi_data_out",
    "Host output",
    base.none
)
local field_scpi_header_scale = ProtoField.string(
    --"owon_bulk.scpi_header_in",
    "owon_bulk.scpi_header",
    "SCALE",
    base.none)

owon_bulk.fields =
{
    field_scpi_meas_data_in,
    field_scpi_data_in,
    field_scpi_data_out,
    field_scpi_header_in
}

local usb_packet_data_length_field = Field.new("usb.urb_len")
local usb_direction_field = Field.new("usb.bmRequestType.direction")

function buffer_to_uint32(buffer)
    return  buffer(0,1):uint() +
            bit.lshift(buffer(1,1):uint(), 8) +
            bit.lshift(buffer(2,1):uint(), 16) +
            bit.lshift(buffer(3,1):uint(), 24)
end

function append_to_title(pinfo, text)
    pinfo.cols.info:set(tostring(pinfo.cols.info)..text)
end

function appendMeasurementPoints(buffer, amount_points, subtree, payload_offset)
    for i=1,amount_points do
        --(payload_offset+4+i-1)
        subtree:add(field_scpi_meas_data_in, "[".. i .. "]: " .. buffer(payload_offset+4+i-1,1):uint())
    end
end

--
-- This function dissects the
-- USB bulk traffic to and from the OWON HDS2202S
--
function owon_bulk.dissector(buffer, pinfo, tree)

    local USB_TRANSFER_TYPE_CONTROL = 0x02
    local USB_TRANSFER_TYPE_BULK = 0x03

    local DIRECTION_OUT = 0x00
    local DIRECTION_IN  = 0x80

    local LOGICPORT_ENDPOINT_OUT = 0x01
    local LOGICPORT_ENDPOINT_IN  = 0x81

    -- dissect general usb information
    local payload_offset = 27
    local usb_direction = bit.band(buffer(21,1):uint(), 0x80)
    local packet_data_length = buffer_to_uint32(buffer(23,4))
    local bmAttributes_transfer = buffer(22,1):uint()
    -- dissect scpi input
    local scpi_id = 0x00
    if packet_data_length > 0 then
        scpi_id = buffer(27,1):uint()
    end

    if bmAttributes_transfer == USB_TRANSFER_TYPE_BULK
    then
        if usb_direction == DIRECTION_OUT
        then
            if packet_data_length == 0
            then
                append_to_title(pinfo, ", OWON HOST empty")
                return
            else
                if scpi_id == 0x2a --'*' identifier for scpi base protocol commands
                then
                    if buffer(27, 5):string() == "*IDN?"
                    then
                        local subtree = tree:add(owon_bulk, buffer(payload_offset, packet_data_length))
                        subtree:add(field_scpi_header_in, buffer(payload_offset,packet_data_length))
                        append_to_title(pinfo, ", OWON HOST *IDN?")
                    end
                else
                    if scpi_id == 0x3a --':' identifies root command
                    then
                        local subtree = tree:add(owon_bulk, buffer(payload_offset, packet_data_length))
                        subtree:add(field_scpi_data_in, buffer(payload_offset,packet_data_length))
                        append_to_title(pinfo, ", OWON HOST ROOT CMD:    " .. buffer(payload_offset,packet_data_length):string())
                    else
                        local subtree = tree:add(owon_bulk, buffer(payload_offset, packet_data_length))
                        subtree:add(field_scpi_data_out, buffer(payload_offset,packet_data_length))
                        append_to_title(pinfo, ", OWON HOST UNKNOWN")
                    end
                end
            end
        else --direction in
            if packet_data_length == 0
            then
                append_to_title(pinfo, ",  OWON OSCI empty")
                return
            else
                if scpi_id == 0x4c --'L' identifier for header??
                then
                    local subtree = tree:add(owon_bulk, buffer(payload_offset, packet_data_length))
                    subtree:add(field_scpi_header_in, buffer(payload_offset+4,packet_data_length-4))
                    local mystr = buffer(payload_offset+4,packet_data_length-4):string()
                    local jsonobj = json.decode(mystr)
                    --print(jsonobj['TIMEBASE']['SCALE'])
                    subtree:add(field_scpi_header_scale, "SCALE:        ", jsonobj['TIMEBASE']['SCALE'])
                    subtree:add(field_scpi_header_scale, "HOFFSET:      ", jsonobj['TIMEBASE']['HOFFSET'])
                    subtree:add(field_scpi_header_scale, "FULLSCREEN:   ", jsonobj['SAMPLE']['FULLSCREEN'])
                    subtree:add(field_scpi_header_scale, "SLOWMOVE:     ", jsonobj['SAMPLE']['SLOWMOVE'])
                    subtree:add(field_scpi_header_scale, "DATALEN:      ", jsonobj['SAMPLE']['DATALEN'])
                    subtree:add(field_scpi_header_scale, "SAMPLERATE:   ", jsonobj['SAMPLE']['SAMPLERATE'])
                    subtree:add(field_scpi_header_scale, "TYPE:         ", jsonobj['SAMPLE']['TYPE'])
                    subtree:add(field_scpi_header_scale, "DEPMEM:       ", jsonobj['SAMPLE']['DEPMEM'])
                    subtree:add(field_scpi_header_scale, "CH1 NAME:     ", jsonobj['CHANNEL'][1]['NAME'])
                    subtree:add(field_scpi_header_scale, "CH1 DISPLAY:  ", jsonobj['CHANNEL'][1]['DISPLAY'])
                    subtree:add(field_scpi_header_scale, "CH1 COUPLING: ", jsonobj['CHANNEL'][1]['COUPLING'])
                    subtree:add(field_scpi_header_scale, "CH1 PROBE:    ", jsonobj['CHANNEL'][1]['PROBE'])
                    subtree:add(field_scpi_header_scale, "CH1 SCALE:    ", jsonobj['CHANNEL'][1]['SCALE'])
                    subtree:add(field_scpi_header_scale, "CH1 OFFSET:   ", jsonobj['CHANNEL'][1]['OFFSET'])
                    subtree:add(field_scpi_header_scale, "CH1 FREQUENCY:", jsonobj['CHANNEL'][1]['FREQUENCE'])
                    --print("here")
                    --print(jsonobj['CHANNEL'][1]['FREQUENCE'])
                    subtree:add(field_scpi_header_scale, "CH2 NAME:     ", jsonobj['CHANNEL'][2]['NAME'])
                    subtree:add(field_scpi_header_scale, "CH2 DISPLAY:  ", jsonobj['CHANNEL'][2]['DISPLAY'])
                    subtree:add(field_scpi_header_scale, "CH2 COUPLING: ", jsonobj['CHANNEL'][2]['COUPLING'])
                    subtree:add(field_scpi_header_scale, "CH2 PROBE:    ", jsonobj['CHANNEL'][2]['PROBE'])
                    subtree:add(field_scpi_header_scale, "CH2 SCALE:    ", jsonobj['CHANNEL'][2]['SCALE'])
                    subtree:add(field_scpi_header_scale, "CH2 OFFSET:   ", jsonobj['CHANNEL'][2]['OFFSET'])
                    subtree:add(field_scpi_header_scale, "CH2 FREQUENCY:", jsonobj['CHANNEL'][2]['FREQUENCE'])
                    subtree:add(field_scpi_header_scale, "DATATYPE:     ", jsonobj['DATATYPE'])
                    subtree:add(field_scpi_header_scale, "RUNSTATUS:    ", jsonobj['RUNSTATUS'])
                    subtree:add(field_scpi_header_scale, "IDN:          ", jsonobj['IDN'])
                    subtree:add(field_scpi_header_scale, "MODEL:        ", jsonobj['MODEL'])
                    subtree:add(field_scpi_header_scale, "Trigger Mode: ", jsonobj['Trig']['Mode'])
                    subtree:add(field_scpi_header_scale, "Trigger Type: ", jsonobj['Trig']['Type'])
                    subtree:add(field_scpi_header_scale, "Trig Channel: ", jsonobj['Trig']['Items']['Channel'])
                    subtree:add(field_scpi_header_scale, "Trig Level:   ", jsonobj['Trig']['Items']['Level'])
                    subtree:add(field_scpi_header_scale, "Trig Edge:    ", jsonobj['Trig']['Items']['Edge'])
                    subtree:add(field_scpi_header_scale, "Trig Coupling:", jsonobj['Trig']['Items']['Coupling'])
                    subtree:add(field_scpi_header_scale, "Trig Sweep:   ", jsonobj['Trig']['Items']['Sweep'])
                    --print(jsonobj['CHANNEL'][1]['NAME'])
                    append_to_title(pinfo, ",  OWON OSCI HEADER")

                else
                    local first_two = buffer_to_uint32(buffer(payload_offset,4))
                    --print("FirstTwo: " .. first_two)
                    if first_two == 300 or first_two == 600
                    then
                        local subtree = tree:add(owon_bulk, buffer(payload_offset, packet_data_length))
                        --subtree:add(field_scpi_data_in, buffer(payload_offset,packet_data_length))
                        appendMeasurementPoints(buffer,first_two, subtree, payload_offset)
                        append_to_title(pinfo, ",  OWON OSCI MEASUREMENT " .. first_two .. " points")
                    else
                        local subtree = tree:add(owon_bulk, buffer(payload_offset, packet_data_length))
                        subtree:add(field_scpi_data_in, buffer(payload_offset,packet_data_length))
                        append_to_title(pinfo, ",  OWON OSCI UNKNOWN")
                    end


                end


            end
        end
    end
end

local usb_bulk_dissector = DissectorTable.get("usb.bulk")

-- Check for a match in the field interface class
usb_bulk_dissector:add(0xffff, owon_bulk);

register_postdissector(owon_bulk)
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
    "owon_bulk.scpi_header_in",
    "SCALE",
    base.none)

owon_bulk.fields =
{
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
                    local subtree = tree:add(owon_bulk, buffer(payload_offset, packet_data_length))
                    subtree:add(field_scpi_data_out, buffer(payload_offset,packet_data_length))
                    append_to_title(pinfo, ", OWON HOST")
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
                    subtree:add(field_scpi_header_scale, "SCALE:", jsonobj['TIMEBASE']['SCALE'])
                    append_to_title(pinfo, ",  OWON OSCI HEADER")
                end
                if scpi_id == 0x3a --':' identifies root command
                then
                    local subtree = tree:add(owon_bulk, buffer(payload_offset, packet_data_length))
                    subtree:add(field_scpi_data_in, buffer(payload_offset,packet_data_length))
                    append_to_title(pinfo, ",  OWON OSCI")
                end
            end
        end
    end
end

local usb_bulk_dissector = DissectorTable.get("usb.bulk")

-- Check for a match in the field interface class
usb_bulk_dissector:add(0xffff, owon_bulk);

register_postdissector(owon_bulk)
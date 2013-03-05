'''
@author: Adam Hickerson
'''
from optparse import OptionParser
from CDEMessages_pb2 import CDEMessage
import random
import exceptions
import socket
import struct

def nodeactivate(dna,dcid,dcrn=0):
    message = CDEMessage()
    
    """Adding the DCID to the database is the primary purpose of this message.
    It is up to the Data Consumer to determine how to create unique DCIDs. The
    only restriction is that the length be no more than 64 characters"""
    if len(dcid) > 64:
        raise UDTXError("DCID cannot be longer than 16 characters")
    message.node_dcid = dcid
    
    """The DCRN allows the CDE to determine who is requesting this node. DCRNs
    are assigned through a simple application process. For testing, DCRN 0 may
    always be used- messages will always succeed but any actions will not be
    performed"""
    message.dcrn = dcrn
    
    """In reality, Data Consumers should have a controlled method of creating
    unique transaction identifiers. For now, we'll generate a random string """
    message.trans_id = '%030x' % random.randrange(256**15)
    
    """The DCID must be obtained from the unit being activated. It will be in
    the UDTX dashed-triplet format (e.g. A5F2-16D1-00A2). When communicating
    with the CDE, this should be converted to a 48-bit number stored in 64 bits.
    This is simply the un-dashed hex number. In this example the representation
    would be 0xA5F216D100A2."""
    message.activate_message.node_dna = parse_dna_string(dna)
    
    """A node name does not need to be specified during activation. But to
    reduce network traffic, it should be passed if available. We'll pass in a
    default name for demonstration purposes."""
    message.activate_message.node_name = "Node 1"
    
    """Our message is complete. We need to send and receive a response, and
    then we can work on reading that response."""
    """Let's get a connection to the CDE open"""
    s = socket.socket();
    s.connect(("cde.udtx.com",3886)) # Inbound messages port
    s.settimeout(5) # Nothing should take 5 seconds
    
    """ Now we send and receive a CDE message frame. The message frame is very
    simple- the first four bytes specify the length of the remaining part of
    the frame. The remaining portion is the serialized message, as seen
    below!"""
    s.send(struct.pack('!i', message.ByteSize())) # Write the length
    s.send(message.SerializeToString()) # Then the message!
    
    """Parse the response right into a new message object"""
    response = CDEMessage()
    response_length = struct.unpack('!i',s.recv(4))[0] # Receive the length
    response.ParseFromString(s.recv(response_length)) # Then the message!
    
    """Many types of messages can be sent using the CDEMessage class. We first
    verify that we have what we think we should have"""
    if not response.HasField('activate_response'):
        raise UDTXError("Incorrect message was returned in response to "
                        "Node Activate message")
    # If we don't error out, then it is safe to read the activate_reponse field
    
    """We specified a transaction ID. If we didn't get the same ID back, there
    is a problem. In production environments, this should never happen."""
    if response.trans_id != message.trans_id:
        raise UDTXError("Mismatched transaction ID returned. Sent " + 
                        message.trans_id + ", received " + response.trans_id)
    
    """Likewise, this message should be for my own DCRN. Likewise, this should
    never happen in a production environment."""
    if response.dcrn != dcrn:
        raise UDTXError("Received incorrect DCRN in response. Received " +
                        response.dcrn)
    
    """Final, never-to-occur scenario: the DCID isn't the one we just assigned.
    It should be noted that if any of three errors does occur, the message
    should not be attempted again."""
    if response.node_dcid != dcid:
        raise UDTXError("Received incorrect DCID in response. Received " +
                        response.dcid)
    
    """Now to check the actual response. Was the addition accepted?"""
    if response.activate_response.accepted:
        return True
    else:
        raise UDTXError("Failed to activate node. Server returned error " +
                        str(response.activate_response.error_code) + ": " +
                        response.activate_response.error_message)

def parse_dna_string(dna):
    dna_long = 0
    split = dna.split('-')
    if len(split) != 3:
        raise UDTXError("Malformed DNA string: " + dna)
    
    for i in xrange(0, 3):
        if len(split[i]) > 4:
            raise UDTXError("Malformed DNA string at component " + i + ": " +
                            dna)
        try:
            dna_long += int(split[i],16) << (3-i)
        except exceptions.ValueError:
            raise UDTXError("Malformed DNA string at component " + i + ": " +
                            dna)
            
    return dna_long

def main():
    p = OptionParser(description='Generates sample UDTX messages',
                     prog='udtx-sample',
                     version='udtx-sample 0.1',
                     usage='%prog [options] DNA DCID')
    p.add_option('-r','--registration-number',
                 type='int',
                 dest='dcrn',
                 help='use the specified DC Registration Number')
    options, args = p.parse_args()
    try:
        if len(args) == 2:
            if options.dcrn:
                dcrn = options.dcrn
            else:
                dcrn = 0
            
            if nodeactivate(args[0],args[1],dcrn):
                print "Node activated successfully"
            else:
                print "Failed node activation"
        else:
            p.print_help()
    except UDTXError as e:
        print e.message

class UDTXError(Exception):
    pass

if __name__ == '__main__':
    main()
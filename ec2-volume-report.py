from pprint import pprint as pp
import boto3
import os
import argparse
import string
import random

# Define output color classes
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# AWS example code ref : https://github.com/awsdocs/aws-doc-sdk-examples/tree/master/python/example_code

# Report should be run using restricted IAM Role.
# IAM 'ec2report' credentials should be stored as a boto3 profile (example: ~/.aws/credentials)
os.environ['AWS_PROFILE'] = 'script_ec2volumereport'   # Define which profile to connect with
session = boto3.Session(profile_name='script_ec2volumereport')   # Create a boto3 session using the defined profile

######################
# Set up the arguments
######################

# Make the sript user-friendly by providing some arguments and help options
# Search filters
parser = argparse.ArgumentParser(description="Retrieve a list of AWS EC2 instances.")

g_awsfilters = parser.add_argument_group('AWS SEARCH FILTERS')
g_filters = parser.add_argument_group('CUSTOM SEARCH FILTERS')
g_display = parser.add_argument_group('DISPLAY OPTIONS')
g_action = parser.add_argument_group('ACTIONS')
g_debug = parser.add_argument_group('DEBUG')

# AWS Search filters
status_args = ['creating', 'available', 'in-use', 'deleting', 'deleted', 'error']
g_filters.add_argument("-i", "--id", action='append', help="Return only volumes matching ID. Accepts multiple values.")
g_filters.add_argument("-r", "--region", action='append', help=" Return only volumes in Region(s) REGION, accepts multiple values.")
g_filters.add_argument("-s", "--size", action='append', help=" Return only volumes with exact size SIZE, accepts multiple values.")
g_filters.add_argument("-S", "--status", action='append', choices=status_args, help="Return only volumes with status STATE, accepts multiple values.")
g_filters.add_argument("-t", "--tag", action='append', help="Return only volumes where tag Key is exactly TAG, accepts multiple values.")
g_filters.add_argument("-T", "--type", action='append', choices=['gp2', 'io1', 'st1', 'sc1', 'standard'], help="Return only volumes where type is exactly TYPE, accepts multiple values.")
g_filters.add_argument("-z", "--zone", action='append', help="Return only volumes in availability zone ZONE, accepts multiple values.")

# Custom search filters
g_filters.add_argument("-n", "--name", action='append', help="Return only volumes where 'name' tag value contains NAME, accepts multiple values.")
#g_filters.add_argument("-N", "--name-exact", action='append', help="Return only volumes where 'name' tag value matches NAME exactly, accepts multiple values.")
#g_filters.add_argument("-o", "--owner", action='append', help="Return only volumes where 'owner' tag value contains OWNER, accepts multiple values.")
#g_filters.add_argument("-O", "--owner-exact", action='append', help="Return only volumes where 'owner' tag value matches OWNER exactly, accepts multiple values.")
#g_filters.add_argument("-p", "--project", action='append', help="Return only volumes where 'project' tag value contains PROJECT, accepts multiple values.")
#g_filters.add_argument("-P", "--project-exact", action='append', help="Return only volumes where 'project' tag value matches PROJECT exactly, accepts multiple values.")

# Display options (value printed if argument passed)
g_display.add_argument("--colour", help="Colorize the output.", action="store_true")
g_display.add_argument("--summary", help="Append a summary to the output.", action="store_true")

# Actions to be performed
g_action.add_argument("--delete", help="Delete all listed volumes", action="store_true")
g_action.add_argument("--dry-run", help="Enable a dry-run on actions.", action="store_true")

# Debug filters
g_debug.add_argument("--debug-args", help="Debug, print all args", action="store_true")
g_debug.add_argument("--debug-filters", help="Debug, print all filters", action="store_true")
g_debug.add_argument("--debug-dict", help="Debug, print the ec2data dictionary", action="store_true")
g_debug.add_argument("-R", "--region-print", action='store_true', help="Print all publicly available region names.")
g_debug.add_argument("-Z", "--zone-print", action='store_true', help="Print all availablity zones and status.")

global args
args = parser.parse_args()

##############################
# Define the various functions
##############################
def get_aws_filters(): # Filter instance results by AWS API_Filter attributes that are not Tags and do not require fuzzy searching (tag filtering should be case-insensitive)
    global filters
    filters = {}
    
    # Filter for Instance ID if provided
    if args.id:
        filters["volume_id"] = {
            'Name': 'volume-id',
            'Values': args.id
        }
    
    # Filter for custom tags if provided
    if args.tag:
        filters["tag"] = {
            'Name': 'tag-key',
            'Values': args.tag
        }
    
    # Filter for volume type if provided
    if args.type:
        filters["type"] = {
            'Name': 'volume-type',
            'Values': args.type
        }
    
    # Filter for zones if provided
    if args.zone:
        filters["zone"] = {
            'Name': 'availability-zone',
            'Values': args.zone
        }
    
    # Filter for specific volume size if provided
    if args.size:
        filters["size"] = {
            'Name': 'size',
            'Values': args.size
        }
    
    # Filter for instance status (default to all)
    if args.status:
        arg_status = args.status    # Set the instance status depending on -s --status argument
    else:
        arg_status = status_args    # Set the instance status to a default list of all states
    filters["status"] = {
        'Name': 'status',
        'Values': arg_status
    }

    if not args.debug_filters:
        Filters = []
        for value in filters.values():
            Filters.append(value)
        return Filters

def get_custom_filters():
    custom_filters = {}

def get_region():
    global region_list
    # Obtain all publicly accessible regions for this session
    region_list = session.get_available_regions('ec2')
    return region_list
    
def get_zone():
    global zone_list
    print('--------------------')
    for region in arg_region:
        print('REGION : ' + region)
        print('--------------------')
        client = boto3.client('ec2', region)
        # Obtain all accessible availablility zones for this session
        zone_list = client.describe_availability_zones()['AvailabilityZones']
        for zone in zone_list:
            if zone['State'] == 'available':
                if args.colour:
                    print(zone['ZoneName'] + " : " + bcolors.OKGREEN + zone['State'] + bcolors.ENDC)
                else:
                    print(zone['ZoneName'] + " : " + zone['State'])
            else:
                if args.color:
                    print(zone['ZoneName'] + " : " + bcolors.FAIL + zone['State'] + bcolors.ENDC)
                else:
                    print(zone['ZoneName'] + " : " + zone['State'])
        print('--------------------')
    
def get_volumes():
    global ec2data
    ec2data = dict()   # Declare dict to be used for storing instance details later
    global volume

    def store_voldata():
        ec2data[volume.id] = {
            'Region': 'NO_REGION',
            'Zone': 'NO_ZONE',
            'Volume ID': 'NO_VOL_ID',
            'Size': 'SIZE_UND',
            'Type': 'TYP_UND',
            'Status': "STATE_UND",
            'Name': 'NO_NAME',
            'Owner': 'NO_OWNER',
            'Project': 'NO_PROJECT',
            'Created': 'CREATION_UND',
            }
        # Retrieve all instance attributes and assign desired attributes to dict that can be iterated over later
        # List of available attributes : https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#volume

        # Add all standard volume info to dictionary
        ec2data[volume.id].update({'Region': str.lower(region)}) # Store the AWS Region of the volume

        if volume.availability_zone:                                                                                                                                                                                                                  
            ec2data[volume.id].update({'Zone': volume.availability_zone}) # Store the Availability Zone of the volume
        if volume.id:                                                                                                                                                                                                                  
            ec2data[volume.id].update({'Volume ID': volume.id}) # Store the Volume ID
        if volume.volume_type:                                                                                                                                                                                                                  
            ec2data[volume.id].update({'Type': volume.volume_type}) # Store the Volume Type
        if volume.state:                                                                                                                                                                                                                  
            ec2data[volume.id].update({'Status': volume.state}) # Store the Volume state
        if volume.create_time:                                                                                                                                                                                                                  
            ec2data[volume.id].update({'Created': str(volume.create_time)}) # Store the Volume Creation time
        if volume.size:                                                                                                                                                                                                                  
            ec2data[volume.id].update({'Size': str(volume.size)}) # Store the Volume Size (GB)

        # Add tag information to dictionary
        if volume.tags:
            for tag in volume.tags:
                key = tag['Key']
                if str.lower(key) == 'name':    # Check for any tags with a value of Name or name
                    name = tag['Value']   # Set name variable to be equal to the value of the Name/name tag
                    ec2data[volume.id].update({'Name': name})
                if str.lower(key) == 'owner':
                    owner = tag['Value']
                    ec2data[volume.id].update({'Owner': owner})
                if str.lower(key) == 'project':
                    project = tag['Value']
                    ec2data[volume.id].update({'Project': project})

                if args.tag:   # Loop over the list of custom tags if present
                    for custom_tag in args.tag:
                        if str.lower(tag['Key']) == str.lower(custom_tag):
                            ec2data[volume.id].update({tag['Key']: tag['Value']})

    for region in arg_region:
        ec2 = boto3.resource('ec2', str.lower(region))   # Print a delimiter to identify the current region
        volumes = ec2.volumes.filter(   # Filter the list of returned instance - https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.ServiceResource.instances 
            # List of available filters : https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeInstances.html
            Filters=get_aws_filters()
        )
        # Pre-define the dictionary with base values, also helps to order the output
        for volume in volumes:
            if args.name:
                if volume.tags:
                    for tag in volume.tags:
                        if str.lower(tag['Key']) == 'name':
                            for arg in args.name:
                                if str.lower(arg) == str.lower(tag['Value']):
                                    store_voldata()

    # Print results line by line
    if not args.debug_dict:
        for vol in ec2data:
            print("\t".join(ec2data[vol].values()))

    if args.summary:
        print('------------------')
        print('Total Volumes : ' + str(len(ec2data)))

#    selectedKeys = list()

#    print('------------')
#    for vol in ec2data:
#        if args.name:
#            pp(ec2data[vol].values())
#            if args.name in ec2data[vol].values():
#                pp(ec2data[vol])
#            if v == args.name:
#                selectedKeys.append(v)

def delete_volumes():
    passphrase = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(4))
    print("\n")
    print(bcolors.WARNING + "!! WARNING : THIS IS NOT REVERSABLE !!" + bcolors.ENDC)
    print("Please enter the following passphrase to DELETE ALL LISTED VOLUMES : " + passphrase)
    print(bcolors.WARNING + "!! WARNING : THIS IS NOT REVERSABLE !!" + bcolors.ENDC)
    print("\n")
    answer = ''
    while answer != passphrase:
        answer = input("Passphrase: ").strip()

    for vol in ec2data:
        response = volume.delete(
            VolumeId=vol,
            DryRun=args.dry_run
        )
        print(response)

##############
# Do the stuff
##############
volume_print = True

## CONFIRM THE CURRENT VALUES OF EACH ARGUMENT FOR TESTING
if args.debug_args:
    pp(args)
    print("\n")

# Check if --region set and assign variable values
if args.region:
    arg_region = args.region
else:
    arg_region = get_region()

# Print print all available regions if -R flag is set
if args.region_print:
    get_region()
    print('------------------')
    print('Available regions:')
    print('------------------')
    for region in region_list:
        print(region)
    print('------------------')
    print('Retrieved from AWS')
    print('------------------')
    volume_print = False

if args.debug_filters:
    get_aws_filters()
    # Print the list of filters and values
    if args.region:
        print('-----------------')
        print('FILTERED REGIONS')
        print('-----------------')
        for region in arg_region:
            print(str.lower(region))
        print("\n")
    volume_print = False
    print("-----------")
    print("FILTER LIST")
    print("-----------")
    print(filters)    # Print the full currently assigned filters dict

    print("\n-------------")
    print("FILTER KEYS")
    print("-------------")
    for value in filters.keys():    # Print each currently defined filter key
        print(value)

    print("\n-------------")
    print("FILTER VALUES")
    print("-------------")
    for value in filters.values():    # Print each currently defined filter value
        pp(value)

if args.debug_dict:
    get_volumes()
    print("------------------")
    print("EC2DATA DICTIONARY")
    print("------------------")
    pp(ec2data)
    for i_id, i_v in ec2data.items():
        print("-------------------")
        print(i_id)
        print("-------------------")
        for title, attribute in i_v.items():
            print(title, attribute, sep=" : ")

if args.zone_print:
    get_zone()
    volume_print = False

if volume_print:
    # Go ahead and output the instance details if not checking for a list of regions
    get_volumes()

if args.delete:
    delete_volumes()

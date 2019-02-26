from pprint import pprint as pp
from datetime import datetime, timedelta
import boto3
import os
import argparse

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

# Report should be run using restricted IAM Role.
# IAM 'ec2report' credentials should be stored as a boto3 profile (example: ~/.aws/credentials)
os.environ['AWS_PROFILE'] = 'script_ec2volumereport'   # Define which profile to connect with
session = boto3.Session(profile_name='script_ec2volumereport')   # Create a boto3 session using the defined profile


######################
# Set up the arguments
######################
    
# Make the sript user-friendly by providing some arguments and help options
# Search filters
parser = argparse.ArgumentParser(description="Retrieve a list of AWS EC2 volumes.")

g_filters = parser.add_argument_group('SEARCH FILTERS')
g_display = parser.add_argument_group('DISPLAY OPTIONS')
g_debug = parser.add_argument_group('DEBUG')

# Search filters
g_filters.add_argument("-r", "--region", action='append', type=str, help="Only volumes in Region(s) REGION, accepts multiple values. ALWAYS DISPLAYED.")
state_args = ['available', 'in-use']
g_filters.add_argument("-s", "--state", choices=state_args, action='append', type=str, help="Only volumes with status STATUS, accepts multiple values. ALWAYS DISPLAYED.")

# Display options (value printed if argument passed)
g_display.add_argument("--colour", help="Colorize the output.", action="store_true")
g_display.add_argument("--summary", help="Append a summary to the output.", action="store_true")

# Debug filters
#g_debug.add_argument("--debug-args", help="Debug, print all args", action="store_true")
g_debug.add_argument("--debug-filters", help="Debug, print all filters", action="store_true")
g_debug.add_argument("--debug-dict", help="Debug, print the ec2data dictionary", action="store_true")
g_debug.add_argument("-R", "--region-print", action='store_true', help="Print all publicly available region names.")
g_debug.add_argument("-Z", "--zone-print", action='store_true', help="Print all availablity zones and status.")    

global args
args = parser.parse_args()
 

##############################
# Define the various functions
##############################

def get_filters():
    global filters
    filters = {}
    filters.clear()

    if args.state:
        arg_state = args.state    # Set the instance state depending on -s --state argument
    else:
        arg_state = state_args    # Set the instance state to a default list of all states
    filter_state = {
    'Name': 'status',
    'Values': arg_state
    }
    filters["Status"] = filter_state

    if not args.debug_filters:
        # Return filters
        for value in filters.values():
            return value

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
    ec2data = dict()
    ec2data.clear()
    for region in arg_region:
        ec2 = boto3.resource('ec2', str.lower(region)) 
        volumes = ec2.volumes.filter(
            Filters=[
                get_filters()
            ]
        )
        for volume in volumes: 
            ec2data[volume.id] = {
                'Region': str.lower(region),
                'Volume ID': volume.id,
                'Status': volume.state,
                'Created': str(volume.create_time),
                'Size': str(volume.size)
            }

            if volume.state:
                if args.colour:
                    if volume.state == 'available':
                        ec2data[volume.id].update({'Status': bcolors.OKGREEN + volume.state + bcolors.ENDC})
                    elif volume.state == 'in-use':
                        ec2data[volume.id].update({'Status': bcolors.FAIL + volume.state + bcolors.ENDC})
                    else:
                        ec2data[volume.id].update({'Status': volume.state})
                else:
                    ec2data[volume.id].update({'Status': volume.state})

            print("\t".join(ec2data[volume.id].values()))

    if args.summary:
        print('------------------')
        print('Total Volumes : ' + str(len(ec2data)))

##############
# Do the stuff                                                                                                                                                                                                                                
##############

volumes_print = True

# Check if --region set and assign variable values
if args.region:
    arg_region = args.region
else:
    arg_region = get_region()

# Print print all available Regions if -R flag is set                                                                                                                                                                                         
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
    volumes_print = False

if args.debug_filters:
    get_filters()
    # Print the list of filters and values
    if args.region:
        print('-----------------')
        print('FILTERED REGIONS')
        print('-----------------')
        for region in arg_region:
            print(str.lower(region))
        print("\n")
    volumes_print = False
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
    get_volume()
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

# Print print all Availability Zones if -Z flag is set                                                                                                                                                                                         
if args.zone_print:
    get_zone()
    volumes_print = False

if volumes_print:
    get_volumes()

#-----------------------------

#region = "us-east-1"
#cloudwatch = boto3.client("cloudwatch", region_name=region)
#today = datetime.now() + timedelta(days=1) # today + 1 because we want all of today
#two_weeks = timedelta(days=14)
#start_date = today - two_weeks
#ec2 = boto3.resource("ec2", region_name=region)
#
#def get_available_volumes():
#    available_volumes = ec2.volumes.filter(
#        Filters=[{'Name': 'status', 'Values': ['available']}]
#    )
#    return available_volumes
#
#def get_metrics(volume_id):
#    """Get volume idle time on an individual volume over `start_date`
#       to today"""
#    metrics = cloudwatch.get_metric_statistics(
#        Namespace='AWS/EBS',
#        MetricName='VolumeIdleTime',
#        Dimensions=[{'Name': 'VolumeId', 'Value': volume_id}],
#        Period=3600,  # every hour
#        StartTime=start_date,
#        EndTime=today,
#        Statistics=['Minimum'],
#        Unit='Seconds'
#    )
#    return metrics['Datapoints']
#
#def is_candidate(volume_id):
#    """Make sure the volume has not been used in the past two weeks"""
#    metrics = get_metrics(volume_id)
#    if len(metrics):
#        for metric in metrics:
#            # idle time is 5 minute interval aggregate so we use
#            # 299 seconds to test if we're lower than that
#            if metric['Minimum'] < 299:
#                return False
#    # if the volume had no metrics lower than 299 it's probably not
#    # actually being used for anything so we can include it as
#    # a candidate for deletion
#    return True
#
#volumes = get_available_volumes()
#candidates = [volume for volume in volumes if is_candidate(volume.volume_id)]
#for candidate in candidates:
#    print("Removing volume: ", candidate)
#    try:
#        candidate.delete()
#    except:
#        print("Error: ", e)

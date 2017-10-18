import http.client
import json
import boto3
import smtplib
from email.mime.text import MIMEText
import datetime as dt
import os,sys


def get_config():
    try:
        dirpath = os.path.dirname(os.path.realpath(sys.argv[0]))
        jsonpath = os.path.join(dirpath, 'config.json')
        with open(jsonpath, 'r') as f:
            config = json.load(f)
            return config

    except Exception as e:
        print(e)
        return False

config = get_config()
if (config == False):
    print("Config File Not Found!!!")
    input("Enter to exit")
    sys.exit()
else:
    AK = config['DEFAULT']['aws_access_key']
    SK = config['DEFAULT']['aws_secret_key']
    Region = config['DEFAULT']['ec2_region_name']

    ec2client = boto3.client('ec2', aws_access_key_id=AK, aws_secret_access_key=SK)
    ec2resource = boto3.resource('ec2', aws_access_key_id=AK, aws_secret_access_key=SK)
    api_key = config['DEFAULT']['all_apikey']


def get_all_monitors():
        conn = http.client.HTTPSConnection("api.uptimerobot.com")
        payload = "api_key=" + api_key + "&format=json&logs=1"

        headers = {
            'content-type': "application/x-www-form-urlencoded",
            'cache-control': "no-cache"
        }
        try:
            conn.request("POST", "/v2/getMonitors", payload, headers)
            res = conn.getresponse()
            data = res.read()
            decoded = data.decode("utf-8")

            monitors = json.loads(decoded)
            print(monitors)
            return monitors

        except Exception as e:
            print(e)

        return



def get_sites_status(status):
    sites_to_check = get_all_monitors()
    if status == 'down':
        down_sites = {}
        for site in sites_to_check["monitors"]:
            mon_name = site['friendly_name']
            mon_down_time = site['logs'][0]['duration']
            print(mon_name)
            print(mon_down_time)
            print(" ")

            try:
                down_instance = parse_instance_id(mon_name)
                mon_stat_id = str(site['status'])
                if mon_stat_id == '9':
                    down_sites[down_instance] = mon_down_time
            except Exception as e:
                pass


        return down_sites

    elif status == 'up':
        up_sites = []
        for site in sites_to_check["monitors"]:
            mon_name = site['friendly_name']
            mon_down_time = site['logs'][0]['duration']
            try:
                up_instance = parse_instance_id(mon_name)
                mon_stat_id = str(site['status'])
                if mon_stat_id == '2':
                    up_sites.append(up_instance)

            except Exception as e:
                pass


        return up_sites


def parse_instance_id(friendly_name):
    inst_id = friendly_name.split('|')[1]


    return inst_id


def check_an_instance(instanceID):
    try:
        state = ec2client.describe_instance_status(InstanceIds=[instanceID],IncludeAllInstances=True)
        cur_state = state['InstanceStatuses'][0]['InstanceState']['Name']
        return cur_state
    except Exception as e:
        return e



def check_time_to_reboot(down_time):
    if down_time > config['LocalSettings']['reboot_threshold']:

        return True

    else:
        return False


def reboot_down_instance(instance):
    print("Rebooting instance: " + instance)
    if ec2client.reboot_instances(InstanceIds=[instance],DryRun=False):
        return True

    else:
        return False


def check_reboot_tag():
    servers_currently_rebooting = []
    rebooting_instances = ec2client.describe_tags(Filters=[{'Name': 'tag:IS_Rebooting','Values': ['TRUE']}])
    for instance in rebooting_instances['Tags']:
        servers_currently_rebooting.append(instance['ResourceId'])



    return servers_currently_rebooting


def check_instance_reboot_tag(instance_id):
    reboot_status = ''
    rebooting_instances = ec2client.describe_instances(InstanceIds=[instance_id])
    reboot_tag = rebooting_instances['Reservations'][0]['Instances'][0]['Tags']
    for value in reboot_tag:
        if value['Key'] == 'IS_Rebooting':
            reboot_status = value['Value']

    return reboot_status


def update_reboot_tag(instance_id,status):

    if status != 'FALSE' and status != 'TRUE':
        print("bad status")
        return
    else:
        response = ec2client.create_tags(Resources=[instance_id],Tags=[{'Key': 'IS_Rebooting','Value': status,},],)

    return

def reset_reboot_tags():
    servers = check_reboot_tag()

    up_sites = get_sites_status('up')
    servers_reset = []

    for server in servers:
        if server in up_sites:
            update_reboot_tag(server,'FALSE')
            servers_reset.append(servers)

        else:
            print("we cant retag")




    return servers_reset

def email_results(rebooted_instance,status='success'):

    if status == 'success':
        msg = "Attention DOWN Instance!!! " + rebooted_instance + " was just rebooted becuase uptimerobot has reported it down for longer than 5 minutes. \n\nIf the reboot does not resolve the issue please take additional action."

    else:
        msg = "Attention!!\n DOWN Instance: " + rebooted_instance + " did not reboot successfully. Please take further action"


    msg = MIMEText(msg)




    fromaddr = config['EMAIL']['from_addr']
    toaddr = config['EMAIL']['to_addr']
    date = str(dt.date.today())

    username = config['EMAIL']['email_username']
    password = config['EMAIL']['email_password']

    msg['Subject'] = "Attn: " + rebooted_instance + " WAS JUST REBOOTED " + date
    msg['To'] = toaddr
    msg['From'] = fromaddr

    s = smtplib.SMTP('smtp.gmail.com:587')
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login(username,password)
    s.sendmail(fromaddr,toaddr,msg.as_string())
    s.close()

    return


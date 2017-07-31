#!/usr/bin/env python
import boto3
import jinja2
import json
import os
import pyboto3
import pyboto3.ec2
import re
import simplejson
import yaml
from ansible.module_utils._text import to_text
from ansible.parsing.yaml.dumper import AnsibleDumper
from ansible.plugins.filter.core import to_nice_json, to_nice_yaml, to_yaml
from botocore.exceptions import ClientError
from jinja2 import Environment, FileSystemLoader

r53c = None
rdsc = None
snsc = None


def main():
    region = 'eu-central-1'
    # region = 'eu-west-1'
    fail_on_change = True

    print "Region: " + region

    # ec2 CLIENT
    ec2c = boto3.client('ec2', region_name=region)
    """ :type : pyboto3.ec2 """

    global r53c
    r53c = boto3.client('route53', region_name=region)
    """ :type : pyboto3.route53 """

    elbc = boto3.client('elb', region_name=region)
    """ :type : pyboto3.elb """

    global iamc
    iamc = boto3.client('iam', region_name=region)
    """ :type : pyboto3.iam """

    global rdsc
    rdsc = boto3.client('rds', region_name=region)
    """ :type : pyboto3.rds """

    global snsc
    snsc = boto3.client('sns', region_name=region)
    """ :type : pyboto3.sns """

    global s3c
    s3c = boto3.client('s3', region_name=region)
    """ :type : pyboto3.s3 """

    working_dir = os.path.dirname(os.path.abspath(__file__))

    # trim_blocks=True controls whitespace
    # undefined=jinja2.StrictUndefined causes a UndefinedError when a template is not fully populated
    jinja2_environment = Environment(loader=FileSystemLoader(working_dir), trim_blocks=True, lstrip_blocks=True)

    # needed in order to use the 'continue' loop control keyword
    jinja2_environment.add_extension('jinja2.ext.loopcontrols')

    ## add a custom filter
    # finds a regex in a string and returns it
    jinja2_environment.filters['regex_search'] = regex_search
    # coverts json to yaml
    jinja2_environment.filters['to_yaml_tpa'] = to_yaml_tpa
    jinja2_environment.filters['to_nice_json'] = to_nice_json

    ###

    aws_api_call_name = 'describe_route_tables'
    aws_api_response_key = 'RouteTables'
    ansible_command_name = 'ec2_vpc_route_table'
    json = ec2c.describe_route_tables()
    if ('IsTruncated' in json) and (json['IsTruncated']):
        raise Exception("No code to handle paginated result sets")

    write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region, fail_on_change)

    ###

    aws_api_call_name = 'describe_security_groups'
    aws_api_response_key = 'SecurityGroups'
    ansible_command_name = 'ec2_group'
    json = ec2c.describe_security_groups()
    if ('IsTruncated' in json) and (json['IsTruncated']):
        raise Exception("No code to handle paginated result sets")

    write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region, fail_on_change)

    ###

    aws_api_call_name = 'describe_addresses'
    aws_api_response_key = 'Addresses'
    ansible_command_name = 'ec2_eip'
    json = ec2c.describe_addresses()
    if ('IsTruncated' in json) and (json['IsTruncated']):
        raise Exception("No code to handle paginated result sets")

    write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region, fail_on_change)

    ###

    aws_api_call_name = 'list_hosted_zones'
    aws_api_response_key = 'HostedZones'
    ansible_command_name = 'route53_zone'
    json = r53c.list_hosted_zones()
    if ('IsTruncated' in json) and (json['IsTruncated']):
        raise Exception("No code to handle paginated result sets")

    jinja2_environment.globals['route53_list_resource_record_sets'] = route53_list_resource_record_sets

    write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region, fail_on_change)

    #
    ansible_command_name = 'route53'

    # use same keys as above
    write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region, fail_on_change)

    ###

    aws_api_call_name = 'describe_load_balancers'
    aws_api_response_key = 'LoadBalancerDescriptions'
    ansible_command_name = 'ec2_elb_lb'
    json = elbc.describe_load_balancers()
    if ('IsTruncated' in json) and (json['IsTruncated']):
        raise Exception("No code to handle paginated result sets")

    write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region, fail_on_change)

    ###

    aws_api_call_name = 'describe_db_instances'
    aws_api_response_key = 'DBInstances'
    ansible_command_name = 'rds'
    json = rdsc.describe_db_instances()
    if ('IsTruncated' in json) and (json['IsTruncated']):
        raise Exception("No code to handle paginated result sets")

    # need additional tagging support
    jinja2_environment.globals['rds_list_tags_for_resource'] = rds_list_tags_for_resource

    write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region, fail_on_change)

    ###

    aws_api_call_name = 'describe_db_subnet_groups'
    aws_api_response_key = 'DBSubnetGroups'
    ansible_command_name = 'rds_subnet_group'
    json = rdsc.describe_db_subnet_groups()
    if ('IsTruncated' in json) and (json['IsTruncated']):
        raise Exception("No code to handle paginated result sets")

    write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region, fail_on_change)

    ###

    aws_api_call_name = 'describe_db_parameter_groups'
    aws_api_response_key = 'DBParameterGroups'
    ansible_command_name = 'rds_param_group'
    json = rdsc.describe_db_parameter_groups()
    if ('IsTruncated' in json) and (json['IsTruncated']):
        raise Exception("No code to handle paginated result sets")

    # group param information
    jinja2_environment.globals['rds_describe_db_parameters'] = rds_describe_db_parameters

    write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region, fail_on_change)

    ##

    # iam users + associated groups, plus groups

    aws_api_call_name = 'list_users'
    aws_api_response_key = 'Users'
    ansible_command_name = 'iam'
    json = iamc.list_users()
    if ('IsTruncated' in json) and (json['IsTruncated']):
        raise Exception("No code to handle paginated result sets")

    # additional data
    jinja2_environment.globals['iam_list_groups_for_user'] = iam_list_groups_for_user
    jinja2_environment.globals['iam_list_groups'] = iam_list_groups

    write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region, fail_on_change)

    ###

    aws_api_call_name = 'list_roles'
    aws_api_response_key = 'Roles'
    ansible_command_name = 'iam_role'
    json = iamc.list_roles()
    if ('IsTruncated' in json) and (json['IsTruncated']):
        raise Exception("No code to handle paginated result sets")

    # additional data
    jinja2_environment.globals['iam_list_attached_role_policies'] = iam_list_attached_role_policies

    write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region, fail_on_change)

    ###

    aws_api_call_name = 'list_topics'
    aws_api_response_key = 'Topics'
    ansible_command_name = 'sns_topic'
    json = snsc.list_topics()
    if ('IsTruncated' in json) and (json['IsTruncated']):
        raise Exception("No code to handle paginated result sets")

    # # create a reusable Paginator
    # iamc_paginator = snsc.get_paginator(aws_api_call_name)
    #
    # # create a PageIterator from the Paginator
    # page_iterator = iamc_paginator.paginate()
    #
    # json = {'Topics': []}
    # for page in page_iterator:
    #     json['Topics'] = json['Topics'] + page[aws_api_response_key]

    # additional data
    jinja2_environment.globals['sns_get_topic_attributes'] = sns_get_topic_attributes
    jinja2_environment.globals['sns_list_subscriptions_by_topic'] = sns_list_subscriptions_by_topic

    write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region, fail_on_change)

    ###

    aws_api_call_name = 'list_buckets'
    aws_api_response_key = 'Buckets'
    ansible_command_name = 's3'
    json = s3c.list_buckets()
    if ('IsTruncated' in json) and (json['IsTruncated']):
        raise Exception("No code to handle paginated result sets")

    # additional data
    jinja2_environment.globals['get_bucket_location'] = get_bucket_location
    jinja2_environment.globals['get_bucket_tagging'] = get_bucket_tagging

    write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region, fail_on_change)


def get_bucket_tagging(bucket_name):
    foo = None
    try:
        foo = s3c.get_bucket_tagging(Bucket=bucket_name)['TagSet']
    except ClientError:
        pass
    return foo


def get_bucket_location(bucket_name):
    return s3c.get_bucket_location(Bucket=bucket_name)


def route53_list_resource_record_sets(zone_id):
    return r53c.list_resource_record_sets(HostedZoneId=zone_id)['ResourceRecordSets']


def sns_list_subscriptions_by_topic(topic_arn):
    bar = snsc.list_subscriptions_by_topic(TopicArn=topic_arn)
    foo = bar['Subscriptions']
    return foo


def sns_get_topic_attributes(topic_arn):
    return snsc.get_topic_attributes(TopicArn=topic_arn)['Attributes']


def iam_list_attached_role_policies(role_name):
    # create a reusable Paginator
    iamc_paginator = iamc.get_paginator('list_attached_role_policies')

    # create a PageIterator from the Paginator
    page_iterator = iamc_paginator.paginate(RoleName=role_name)

    finalList = []
    for page in page_iterator:
        finalList = finalList + page['AttachedPolicies']

    return finalList


def iam_list_groups():
    # create a reusable Paginator
    iamc_paginator = iamc.get_paginator('list_groups')

    # create a PageIterator from the Paginator
    page_iterator = iamc_paginator.paginate()

    finalList = []
    for page in page_iterator:
        finalList = finalList + page['Groups']

    print "Number of IAM Groups: " + str(len(finalList))

    return finalList


def iam_list_groups_for_user(username):
    # create a reusable Paginator
    iamc_paginator = iamc.get_paginator('list_groups_for_user')

    # create a PageIterator from the Paginator
    page_iterator = iamc_paginator.paginate(UserName=username)

    finalList = []
    for page in page_iterator:
        finalList = finalList + page['Groups']

    return finalList


def rds_list_tags_for_resource(arn):
    return rdsc.list_tags_for_resource(ResourceName=arn)['TagList']


def rds_describe_db_parameters(db_parameter_group_name):
    # create a reusable Paginator
    rdsc_paginator = rdsc.get_paginator('describe_db_parameters')

    # create a PageIterator from the Paginator
    page_iterator = rdsc_paginator.paginate(DBParameterGroupName=db_parameter_group_name)

    finalList = []
    for page in page_iterator:
        # print(page['Parameters'])
        # print json.dumps(page['Parameters'], indent=4, sort_keys=True)
        finalList = finalList + page['Parameters']

    # print json.dumps(finalList, indent=4, sort_keys=True)
    return finalList


def write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region, fail_on_change):
    write_aws_call_to_file(json, aws_api_response_key, aws_api_call_name, region)
    template_file = jinja2_environment.get_template('./jinja/' + ansible_command_name + '.jinja.yml')
    template_data = json[aws_api_response_key]
    # pass the json output to the template as a variable
    template_vars = {
        'json': template_data,
        'region': region,
        'fail_on_change': fail_on_change
    }
    # run the template render
    rendered_template = template_file.render(template_vars)

    region_path = "./" + region + "/"
    tasks_path = region_path + "tasks/"

    if not os.path.exists(tasks_path):
        os.makedirs(tasks_path)

    # write out rendered template to yml file named after the ansible module name
    with open(tasks_path + ansible_command_name + ".yml", "wb") as f:
        f.write(rendered_template)


def write_aws_call_to_file(aws_api_response_json, aws_api_response_key, aws_api_call_name, region):
    region_path = "./" + region + "/"

    if not os.path.exists(region_path):
        os.makedirs(region_path)

    json_path = region_path + "json/"

    if not os.path.exists(json_path):
        os.makedirs(json_path)

    count_json = len(aws_api_response_json[aws_api_response_key])
    print "Number of " + aws_api_response_key + ": " + str(count_json)
    with open(json_path + aws_api_call_name + ".json", "wb") as f:
        f.write(json.dumps(aws_api_response_json, indent=2, default=str))


# find regex in value, and return the matching string
def regex_search(regex, value):
    # assumes there will be a match, no error handling
    try:
        match = re.search(regex, value).group()
    except AttributeError:
        # no match found
        return ''
    return match


def to_yaml_tpa(data, keys_to_lowercase=True):
    jsona = simplejson.loads(data)
    transformed = yaml.dump(jsona, indent=2, allow_unicode=True, default_flow_style=False)
    return transformed


# not used
# def resource_access(region):
# ec2 RESOURCE
# ec2 = boto3.resource('ec2', region_name=region)
# Use the filter() method of the instances collection to retrieve
# all running EC2 instances.
# instances = ec2.instances.filter(
#     Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
# for instance in instances:
#     print(instance.id, instance.instance_type)
# show route table IDs
# route_tables = ec2.route_tables.all()
# for route_table in route_tables:
#     print(route_table.id)


if __name__ == '__main__':
    # execute only if run as a script
    main()

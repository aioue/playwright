#!/usr/bin/env python
import json
import os
import jinja2
import pyboto3
import boto3
import re
from jinja2 import Environment, FileSystemLoader


r53c = None

def main():
    region = 'eu-central-1'
    # region = 'eu-west-1'
    print "Region: " + region

    # ec2 CLIENT
    ec2c = boto3.client('ec2', region_name=region)
    """ :type : pyboto3.ec2 """

    r53c = boto3.client('route53', region_name=region)
    """ :type : pyboto3.route53 """

    elbc = boto3.client('elb', region_name=region)
    """ :type : pyboto3.elb """

    working_dir = os.path.dirname(os.path.abspath(__file__))

    # trim_blocks=True helps control whitespace
    # undefined=jinja2.StrictUndefined causes a UndefinedError when a template is no fully populated
    jinja2_environment = Environment(loader=FileSystemLoader(working_dir), trim_blocks=True, lstrip_blocks=True)

    # needed in order to use the 'continue' loop control keyword
    jinja2_environment.add_extension('jinja2.ext.loopcontrols')

    jinja2_environment.filters['regex_search'] = regex_search

    ###

    aws_api_call_name = 'describe_route_tables'
    aws_api_response_key = 'RouteTables'
    ansible_command_name = 'ec2_vpc_route_table'
    json = ec2c.describe_route_tables()

    write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region)

    ###

    aws_api_call_name = 'describe_security_groups'
    aws_api_response_key = 'SecurityGroups'
    ansible_command_name = 'ec2_group'
    json = ec2c.describe_security_groups()

    write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region)

    ###

    aws_api_call_name = 'describe_addresses'
    aws_api_response_key = 'Addresses'
    ansible_command_name = 'ec2_eip'
    json = ec2c.describe_addresses()

    write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region)

    ### TODO: INCOMPLETE - SEE JINJA NOTES ABOUT PR

    aws_api_call_name = 'list_hosted_zones'
    aws_api_response_key = 'HostedZones'
    ansible_command_name = 'route53_zone'
    json = r53c.list_hosted_zones()
    if json['IsTruncated'] == 'true':
        raise Exception("No code to handle paginated result sets")



    write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region)

    ###
    # Coupled with the call above (needs to loop over zones in order to get record sets)

    aws_api_call_name = 'list_resource_record_sets'
    aws_api_response_key = 'ResourceRecordSets'
    ansible_command_name = 'route53'
    # json = r53c.list_resource_record_sets(HostedZoneId='/hostedzone/Z2ASR1N3O6RHFA')

    ###

    aws_api_call_name = 'describe_load_balancers'
    aws_api_response_key = 'LoadBalancerDescriptions'
    ansible_command_name = 'ec2_elb_lb'
    json = elbc.describe_load_balancers()

    write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region)




def write_tasks_to_file(ansible_command_name, aws_api_call_name, aws_api_response_key, jinja2_environment, json, region, additional_json=None):
    write_aws_call_to_file(json, aws_api_response_key, aws_api_call_name)
    template_file = jinja2_environment.get_template(ansible_command_name + '.jinja.yml')
    template_data = json[aws_api_response_key]
    # pass the json output to the template as a variable
    template_vars = {
        'json': template_data,
        'additional_json': additional_json,
        'region': region
    }
    # run the template render
    rendered_template = template_file.render(template_vars)
    # write out rendered template to yml file named after the ansible module name
    with open(ansible_command_name + ".yml", "wb") as f:
        f.write(rendered_template)

def write_aws_call_to_file(aws_api_response_json, aws_api_response_key, aws_api_call_name):
    count_json = len(aws_api_response_json[aws_api_response_key])
    print "Number of " + aws_api_response_key + ": " + str(count_json)
    with open(aws_api_call_name + ".json", "wb") as f:
        f.write(json.dumps(aws_api_response_json, indent=2, default=str))

def regex_search(regex, value):
    # target = "HTTP:8080/dashboard/index.html"
    # assumes there will be a match, no error handling
    try:
        match = re.search(regex, value).group()
    except AttributeError:
        # no match found
        return ''
    return match


if __name__ == '__main__':
    # execute only if run as a script
    main()

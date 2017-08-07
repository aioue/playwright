# playwright
Creates Ansible playbook task files programatically from existing AWS resources.

## Description

Runs describe API calls against AWS infrastructure and creates playbook tasks.

Turns resources into Ansible tasks that can be included in a playbook.

Useful for migrating from one config management system to another - e.g. Terraform to Ansible, where Terraform's tf.state file locks out share responsibility.

## Pre-requistes

- A configured AWS environment (~/.aws/)
  - configure using `aws configure`

Python packages
- pyboto
- jinja2
- boto3
- json

### Create tasks

Creates JSON dumps of the API calls, and YAML files with tasks for each module.

Change `region = 'eu-central-1'` in the python file to point to the region you want to make tasks for.

```bash
playwright$ ./util/create-ansible-tasks.py
```

Output:

playwright$ cat eu-central-1/tasks/ec2_eip.yml
```yaml
---

- name: manage EC2 EIP address [1/24] eipalloc-123456
  ec2_eip:
    device_id: eni-123456
    in_vpc: yes
    private_ip_address: 1.2.3.4
    public_ip: 4.5.6.7
    region: eu-central-1
    release_on_disassociation:
    reuse_existing_ip_allowed:
    state: present
```

### Test tasks

Change your `ec2.ini` file `regions` param to point to your preferred targets.

Change you `regions: [ 'eu-central-1' ]` in the `translate_terraform.yml` to point to the regions you wish to test.

```bash
playwright$ ansible-playbook translate_terraform.yml -i inventory/generic/ --check -v --tags ec2_eip
```

### Execute tasks

Once you are happy no changes will be made that you do not expect, run your tasks without the `--check` options.

```bash
playwright$ ansible-playbook translate_terraform.yml -i inventory/generic/ --tags all
```

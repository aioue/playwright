# playwright
Creates Ansible playbook tasks files programatically from existing AWS resources.

## Description

Runs describe API calls against AWS infrastructure and creates playbook tasks.

Turns resources into Ansible tasks that can be included in a playbook.

Useful for migrating from one config management system to another - e.g. Terraform to Ansible, where Terraform's tf.state file locks out share responsibility.

## prerequistes

- A configured AWS environment (~/.aws/)
  - configure using `aws configure`

Python packages
- pyboto
- jinja2
- boto3
- json

## Run

```bash
./create-ansible-tasks.py
```

Creates JSON dumps of the API calls, and YAML files with tasks for each module.

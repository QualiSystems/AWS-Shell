import json

import boto3
import sys

from generate_test_cf import read_file_data, set_working_dir, write_file_to_test_dir, TEST_DIR

cloudformation_stacks = [
    [
        "0_Main.json",
        "1_VPC.json",
        "2_EC2.json"
    ],
    [
        "0_Main_EX.json",
        "1_VPC_EX.json",
        "2_EC2_EX.json"
    ],
    [
        "0_Main_EX_No_VPN.json",
        "1_VPC_EX_No_VPN.json",
        "2_EC2_EX_No_VPN.json"
    ]
]
helper_stacks = [
    "AMI_Lookup.json"
]

def main():
    set_working_dir()

    bucket_name = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else "alex-az"
    folder = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else "tmp"

    uploaded_keys = []

    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)

    # upload CF json files
    for stack in cloudformation_stacks:
        for specs_file in stack:
            test_if_json_valid(specs_file)

            content = None
            if specs_file.startswith("0_Main"):
                content = read_file_data(specs_file)
                content = content.replace("/cf-dynamic-execution-server/", "/{}/{}/".format(bucket_name, folder))
                write_file_to_test_dir(content, specs_file)

            key = get_s3_key(folder, specs_file)
            uploaded_keys.append(key)
            bucket.upload_file(specs_file if content is None else "{}/{}".format(TEST_DIR, specs_file), key)

    for stack_file in helper_stacks:
        test_if_json_valid(stack_file)
        key = get_s3_key(folder, stack_file)
        uploaded_keys.append(key)
        bucket.upload_file(stack_file, key)

    for obj in bucket.objects.all():
        if obj.key in uploaded_keys:
            # Make all the uploaded files public
            obj.Acl().put(ACL='public-read')
            print "https://{}.s3.amazonaws.com/{}".format(bucket_name, obj.key)


def get_s3_key(folder, specs_file):
    key = "{0}/{1}".format(folder, specs_file)
    return key


def test_if_json_valid(file_name):
    json_file = open(file_name, 'r')
    json_string = json_file.read()
    json.loads(json_string)


if __name__ == "__main__":
    main()

import json

import boto3

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


def main():
    set_working_dir()

    bucket_name = "alex-az"  # sys.argv[1]
    folder = "tmp"  # sys.argv[2]

    uploaded_keys = []

    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)

    for stack in cloudformation_stacks:
        for specs_file in stack:
            test_if_json_valid(specs_file)

            content = None
            if specs_file.startswith("0_Main"):
                content = read_file_data(specs_file)
                content = content.replace("/cf-dynamic-execution-server/", "/{}/{}/".format(bucket_name, folder))
                write_file_to_test_dir(content, specs_file)

            key = "{0}/{1}".format(folder, specs_file)
            uploaded_keys.append(key)
            bucket.upload_file(specs_file if content is None else "{}/{}".format(TEST_DIR, specs_file), key)

    for obj in bucket.objects.all():
        if obj.key in uploaded_keys:
            # Make all the uploaded files public
            obj.Acl().put(ACL='public-read')
            print "https://s3.amazonaws.com/{}/{}".format(bucket_name, obj.key)


def test_if_json_valid(file_name):
    json_file = open(file_name, 'r')
    json_string = json_file.read()
    json.loads(json_string)


if __name__ == "__main__":
    main()

import os

TEST_DIR = 'test'

EC2_JSON = '2_EC2.json'
EC2_EX_JSON = '2_EC2_EX.json'

TEST_EC2_JSON = '2_EC2_test.json'
TEST_EC2_EX_JSON = '2_EC2_EX_test.json'

PROD_INSTANCE_TYPE = '"c3.xlarge"'
TEST_INSTANCE_TYPE = '"t2.small"'

TEST_MAIN_JSON = '0_Main_test.json'
TEST_MAIN_EX_JSON = '0_Main_EX_test.json'


def main():
    set_working_dir()

    ec2_data = read_file_data(EC2_JSON)
    ec2_data = ec2_data.replace(PROD_INSTANCE_TYPE, TEST_INSTANCE_TYPE)
    write_file_to_test_dir(ec2_data, TEST_EC2_JSON)

    ec2_ex_data = read_file_data(EC2_EX_JSON)
    ec2_ex_data = ec2_ex_data.replace(PROD_INSTANCE_TYPE, TEST_INSTANCE_TYPE)
    write_file_to_test_dir(ec2_ex_data, TEST_EC2_EX_JSON)

    main_data = read_file_data('0_Main.json')
    main_data = main_data.replace(EC2_JSON, '' + TEST_EC2_JSON)
    write_file_to_test_dir(main_data, TEST_MAIN_JSON)

    main_ex_data = read_file_data('0_Main_EX.json')
    main_ex_data = main_ex_data.replace(EC2_EX_JSON, '' + TEST_EC2_EX_JSON)
    write_file_to_test_dir(main_ex_data, TEST_MAIN_EX_JSON)


def read_file_data(file_name):
    with open(file_name, 'r') as f:
        filedata = f.read()
    return filedata


def write_file_to_test_dir(file_data, file_name):
    test_dir = os.path.join(os.getcwd(), TEST_DIR)
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)

    with open(os.path.join(test_dir, file_name), 'w') as file:
        file.write(file_data)


def set_working_dir():
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)


if __name__ == "__main__":
    main()

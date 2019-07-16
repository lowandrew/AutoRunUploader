#!/usr/bin/env python

from gooey import Gooey, GooeyParser
import datetime
import requests
import urllib3
import time
import glob
import os

API_ENDPOINT = 'https://olc.cloud.inspection.gc.ca/api/'

# SSL cert isn't quite right on portal. Use this to disable warning.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def check_credentials(email, password):
    # Try to access an API endpoint that's password protected.
    response = requests.get(API_ENDPOINT + 'run_cowbat/totally_fake_run_name', auth=(email, password), verify=False)
    if response.status_code == 403:
        raise ValueError('Your username or password is incorrect! Close the application and try again.')


def wait_for_run_completion(run_folder):
    # Once GenerateFASTQRunStatistics is created the run has completed. Check status every 20 minutes until run
    # completion.
    run_complete = False
    while run_complete is False:
        if os.path.isfile(os.path.join(run_folder, 'GenerateFASTQRunStatistics.xml')):
            run_complete = True
        else:
            print('{}: Sequencing run not yet complete. Will check again in 20 minutes...'.format(datetime.datetime.now()))
            time.sleep(1200)

    # Sleep for a few minutes once everything finishes just so we're super duper sure that all files are created.
    time.sleep(120)


def upload_files_and_start_run(run_folder, email_address, password):
    x = os.path.split(run_folder)[1].split('_')
    run_name = x[0] + '_' + x[1]
    metadata_files = ['CompletedJobInfo.xml', 'GenerateFASTQRunStatistics.xml', 'RunInfo.xml', 'runParameters.xml',
                      'SampleSheet.csv']
    config_xml = os.path.join(run_folder, 'Data', 'Intensities', 'BaseCalls', 'config.xml')
    interop_files = sorted(glob.glob(os.path.join(run_folder, 'InterOp', '*.bin')))
    sequence_files = sorted(glob.glob(os.path.join(run_folder, 'Data', 'Intensities', 'BaseCalls', '*.fastq.gz')))

    all_uploaded_successfully = True

    # Upload metadata files.
    for metadata_file in metadata_files:
        # Check if file already exists, don't want to bother re-uploading if it does.
        response = requests.get(API_ENDPOINT + 'upload/{}/{}'.format(run_name, metadata_file),
                                auth=(email_address, password),
                                verify=False)
        response_dict = response.json()
        if response_dict['exists'] is False or response_dict['size'] == 0:
            with open(os.path.join(run_folder, metadata_file), 'rb') as data:
                response = requests.put(API_ENDPOINT + 'upload/{}/{}'.format(run_name, metadata_file),
                                        data=data,
                                        auth=(email_address, password),
                                        verify=False)
                if response.status_code == 204:
                    print('{}: Successfully uploaded {}'.format(datetime.datetime.now(), metadata_file))
                else:
                    all_uploaded_successfully = False

    # Upload config.xml
    response = requests.get(API_ENDPOINT + 'upload/{}/{}'.format(run_name, os.path.split(config_xml)[1]),
                            auth=(email_address, password),
                            verify=False)
    response_dict = response.json()
    if response_dict['exists'] is False or response_dict['size'] == 0:
        with open(config_xml, 'rb') as data:
            response = requests.put(API_ENDPOINT + 'upload/{}/{}'.format(run_name, os.path.split(config_xml)[1]),
                                    data=data,
                                    auth=(email_address, password),
                                    verify=False)
            if response.status_code == 204:
                print('{}: Successfully uploaded config.xml'.format(datetime.datetime.now()))
            else:
                all_uploaded_successfully = False

    # InterOp files
    for interop_file in interop_files:
        response = requests.get(API_ENDPOINT + 'upload/{}/{}'.format(run_name, os.path.split(interop_file)[1]),
                                auth=(email_address, password),
                                verify=False)
        response_dict = response.json()
        if response_dict['exists'] is False or response_dict['size'] == 0:
            with open(interop_file, 'rb') as data:
                response = requests.put(API_ENDPOINT + 'upload/{}/{}'.format(run_name, os.path.split(interop_file)[1]),
                                        data=data,
                                        auth=(email_address, password),
                                        verify=False)
                if response.status_code == 204:
                    print('{}: Successfully uploaded {}'.format(datetime.datetime.now(), interop_file))
                else:
                    all_uploaded_successfully = False

    # Sequence files.
    for sequence_file in sequence_files:
        response = requests.get(API_ENDPOINT + 'upload/{}/{}'.format(run_name, os.path.split(sequence_file)[1]),
                                auth=(email_address, password),
                                verify=False)
        response_dict = response.json()
        if response_dict['exists'] is False or response_dict['size'] == 0:
            with open(sequence_file, 'rb') as data:
                response = requests.put(API_ENDPOINT + 'upload/{}/{}'.format(run_name, os.path.split(sequence_file)[1]),
                                        data=data,
                                        auth=(email_address, password),
                                        verify=False)
                if response.status_code == 204:
                    print('{}: Successfully uploaded {}'.format(datetime.datetime.now(), sequence_file))
                else:
                    all_uploaded_successfully = False

    if all_uploaded_successfully:
        # Now start the run actually going
        requests.get(API_ENDPOINT + 'run_cowbat/{}'.format(run_name),
                     auth=(email_address, password),
                     verify=False)
        return True
    else:
        return False


def upload_run(run_folder, email_address, password):
    wait_for_run_completion(run_folder)
    attempted_uploads = 0
    successful_upload = False
    while attempted_uploads < 5 and successful_upload is False:
        successful_upload = upload_files_and_start_run(run_folder, email_address, password)
        attempted_uploads += 1
    if successful_upload:
        print('Complete!')
    else:
        print('Something went wrong uploading files. You\'ll have to upload them manually.')


def check_run_exists_in_portal(run_folder, email, password):
    x = os.path.split(run_folder)[1].split('_')
    run_name = x[0] + '_' + x[1]
    response = requests.get(API_ENDPOINT + 'run_cowbat/{}'.format(run_name),
                            auth=(email, password),
                            verify=False)
    if response.status_code == 404:
        return False
    elif 'status' in response.json():
        if 'Did not start' in response.json()['status']:
            return True
        else:
            return False
    else:
        return True


@Gooey
def main():
    parser = GooeyParser(description='Watches a MiSeq for new runs, and automatically uploads any new runs to '
                                     'the CFIA FoodPort for assembly.')
    parser.add_argument('miseq_folder', widget='DirChooser', help='MiSeqAnalysis directory.')
    parser.add_argument('email_address', help='Email you used to sign up for FoodPort.')
    parser.add_argument('password', widget='PasswordField', help='Your password for FoodPort.')
    args = parser.parse_args()

    # Will kick user out if credentials are wrong. Should get this somewhat more elegant in the future.
    check_credentials(args.email_address, args.password)

    while True:
        print('Checking for runs that haven\'t been uploaded.')
        run_folders = [x[0] for x in os.walk(args.miseq_folder)]
        if args.miseq_folder in run_folders:
            run_folders.remove(args.miseq_folder)
        for run_folder in run_folders:
            run_exists = check_run_exists_in_portal(run_folder, args.email_address, args.password)
            if run_exists is False:
                print('Found new run to upload! Starting upload of {}'.format(run_folder))
                upload_run(run_folder, args.email_address, args.password)
        time.sleep(1800)


if __name__ == '__main__':
    main()

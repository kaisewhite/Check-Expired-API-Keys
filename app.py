import boto3
import os
from datetime import datetime, timezone

# Environment variables: 'TopicArn', 'Exceptions'?, 'AccountName'


def sns_publish(subject, message):
    sns_client = boto3.client('sns')
    response = sns_client.publish(
        TopicArn=os.environ['TopicArn'],
        Subject=subject,
        Message=message,
    )
    return response


def lambda_handler(event, context):

    iam_client = boto3.client('iam')
    now = datetime.now(timezone.utc)
    key_warning_age = 84
    key_disable_age = 87
    key_deletion_age = 90
    account_name = os.environ.get('AccountName', '')

    users_response = iam_client.list_users()
    usernames = [user.get('UserName') for user in users_response.get('Users')]
    for username in usernames:

        # If there are exceptions, add comma-separated "Exceptions" to Lambda env variables.
        if username in os.environ.get('Exceptions', '').split(','):
            continue

        access_keys_response = iam_client.list_access_keys(UserName=username)
        for key_metadata in access_keys_response.get('AccessKeyMetadata'):
            key_id = key_metadata.get('AccessKeyId')
            key_create_date = key_metadata.get('CreateDate')
            key_status = key_metadata.get('Status')
            key_age = (now - key_create_date).days
            subject, message = '', ''

            if key_age == key_warning_age and key_status == 'Active':
                subject = f"AWS {account_name}: {username} Access Key Expiring Soon"
                message = f"{username}'s access key in AWS {account_name} account is at {str(key_age)} days and will be deleted at {key_deletion_age} days."

            elif key_age > key_deletion_age:
                iam_client.delete_access_key(
                    UserName=username, AccessKeyId=key_id)
                subject = f"AWS {account_name}: {username} Access Key Deleted"
                message = f"{username}'s access key in AWS {account_name} account is {str(key_age)} days old and has been deleted."

            elif key_age > key_disable_age and key_status == 'Active':
                iam_client.update_access_key(
                    UserName=username,
                    AccessKeyId=key_id,
                    Status='Inactive'
                )
                subject = f"AWS {account_name}: {username} Access Key Disabled"
                message = f"{username}'s access key in AWS {account_name} account is {str(key_age)} days old and has been disabled. Keys older than {str(key_deletion_age)} days will be deleted."

            # print(f"{username}: {key_status}: {key_age}")
            if subject and message:
                print(subject, '\n', message)
                sns_publish(subject=subject, message=message)

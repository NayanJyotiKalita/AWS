import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timezone, timedelta

def lambda_handler(event, context):

    ec2 = boto3.client('ec2')

    # Snapshots older than 30 days
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=1)  # We can change the no of days according to our needs, or we can also put minutes and hours if necessary

    # Get all snapshots owned by this account
    snapshots = ec2.describe_snapshots(OwnerIds=['self'])

    for snapshot in snapshots['Snapshots']:

        snapshot_id = snapshot['SnapshotId']
        snapshot_time = snapshot['StartTime']

        print(f"Checking snapshot: {snapshot_id}")

        # Delete only if snapshot is older than 30 days
        if snapshot_time < cutoff_date:

            try:
                ec2.delete_snapshot(SnapshotId=snapshot_id)
                print(f"Deleted snapshot {snapshot_id} - older than 1 day") 

            except ClientError as e:
                print(f"Failed to delete {snapshot_id}: {e}")

        else:
            print(f"Keeping snapshot {snapshot_id} - newer than 1 day")

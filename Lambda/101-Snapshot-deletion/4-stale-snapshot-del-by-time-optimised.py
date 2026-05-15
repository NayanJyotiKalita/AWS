import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timezone, timedelta

def lambda_handler(event, context):

    ec2 = boto3.client('ec2')

    # Define 2-day cutoff
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=2)

    # Get all snapshots owned by this account
    snapshots = ec2.describe_snapshots(OwnerIds=['self'])

    for snapshot in snapshots['Snapshots']:

        snapshot_id = snapshot['SnapshotId']
        volume_id = snapshot.get('VolumeId')
        snapshot_time = snapshot['StartTime']

        print(f"Checking snapshot: {snapshot_id}")

        # Skip snapshots newer than 2 days
        if snapshot_time > cutoff_date:
            print(f"Keeping {snapshot_id} - newer than 2 days")
            continue

        print(f"{snapshot_id} is older than 2 days")

        # If snapshot has no volume associated
        if not volume_id:
            try:
                ec2.delete_snapshot(SnapshotId=snapshot_id)
                print(f"Deleted {snapshot_id} - no associated volume")
            except ClientError as e:
                print(f"Error deleting {snapshot_id}: {e}")

            continue

        try:
            # Check if volume exists
            volume_response = ec2.describe_volumes(
                VolumeIds=[volume_id]
            )

            volumes = volume_response['Volumes']

            # Delete if volume does not exist
            if not volumes:
                ec2.delete_snapshot(SnapshotId=snapshot_id)
                print(f"Deleted {snapshot_id} - volume deleted")
                continue

            volume = volumes[0]
            attachments = volume.get('Attachments', [])

            # Delete if volume exists but is detached
            if not attachments:
                ec2.delete_snapshot(SnapshotId=snapshot_id)
                print(f"Deleted {snapshot_id} - volume detached")
                continue

            # Volume attached to an instance
            instance_id = attachments[0]['InstanceId']

            try:
                instance_response = ec2.describe_instances(
                    InstanceIds=[instance_id]
                )

                reservations = instance_response['Reservations']

                # Delete if instance does not exist
                if not reservations:
                    ec2.delete_snapshot(SnapshotId=snapshot_id)
                    print(f"Deleted {snapshot_id} - instance deleted")

                else:
                    print(f"Keeping {snapshot_id} - linked instance exists")

            except ClientError as e:

                if e.response['Error']['Code'] == 'InvalidInstanceID.NotFound':
                    ec2.delete_snapshot(SnapshotId=snapshot_id)
                    print(f"Deleted {snapshot_id} - instance deleted")

                else:
                    print(f"Error checking instance for {snapshot_id}: {e}")

        except ClientError as e:

            if e.response['Error']['Code'] == 'InvalidVolume.NotFound':

                try:
                    ec2.delete_snapshot(SnapshotId=snapshot_id)
                    print(f"Deleted {snapshot_id} - volume deleted")

                except ClientError as delete_error:
                    print(f"Delete failed for {snapshot_id}: {delete_error}")

            else:
                print(f"Unexpected error for {snapshot_id}: {e}")

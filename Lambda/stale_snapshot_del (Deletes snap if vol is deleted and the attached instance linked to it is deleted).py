import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):

    ec2 = boto3.client('ec2')

    # Get all snapshots
    snapshots = ec2.describe_snapshots(OwnerIds=['self'])

    for snapshot in snapshots['Snapshots']:

        snapshot_id = snapshot['SnapshotId']
        volume_id = snapshot.get('VolumeId')

        print(f"Checking snapshot: {snapshot_id}")

        # If no volume associated
        if not volume_id:
            try:
                ec2.delete_snapshot(SnapshotId=snapshot_id)
                print(f"Deleted {snapshot_id} - no associated volume")
            except ClientError as e:
                print(f"Error deleting snapshot {snapshot_id}: {e}")

            continue

        try:
            # Check if volume exists
            volume_response = ec2.describe_volumes(
                VolumeIds=[volume_id]
            )

            volumes = volume_response['Volumes']

            # Volume deleted
            if not volumes:
                ec2.delete_snapshot(SnapshotId=snapshot_id)
                print(f"Deleted {snapshot_id} - volume not found")
                continue

            volume = volumes[0]
            attachments = volume.get('Attachments', [])

            # Volume exists but detached
            # DO NOT delete in your use case
            if not attachments:
                print(f"Keeping {snapshot_id} - volume exists but detached")
                continue

            # Get attached instance
            instance_id = attachments[0]['InstanceId']

            try:
                instance_response = ec2.describe_instances(
                    InstanceIds=[instance_id]
                )

                reservations = instance_response['Reservations']

                # Instance deleted
                if not reservations:
                    ec2.delete_snapshot(SnapshotId=snapshot_id)
                    print(f"Deleted {snapshot_id} - instance deleted")

                else:
                    print(f"Keeping {snapshot_id} - instance exists")

            except ClientError as e:

                if e.response['Error']['Code'] == 'InvalidInstanceID.NotFound':
                    ec2.delete_snapshot(SnapshotId=snapshot_id)
                    print(f"Deleted {snapshot_id} - instance deleted")

                else:
                    print(f"Error checking instance: {e}")

        except ClientError as e:

            if e.response['Error']['Code'] == 'InvalidVolume.NotFound':

                try:
                    ec2.delete_snapshot(SnapshotId=snapshot_id)
                    print(f"Deleted {snapshot_id} - volume deleted")

                except ClientError as delete_error:
                    print(f"Delete failed for {snapshot_id}: {delete_error}")

            else:
                print(f"Unexpected error: {e}")

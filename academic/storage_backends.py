from storages.backends.s3boto3 import S3Boto3Storage


class PrivateMediaStorage(S3Boto3Storage):
    """
    S3 storage for files that shouldn't be served from the public 'static'
    prefix. Kept in a separate 'private' location; URLs are signed since
    S3Boto3Storage defaults querystring_auth to True.
    """
    location = 'private'
    file_overwrite = False

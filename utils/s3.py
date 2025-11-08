import os

from dotenv import load_dotenv

from conf.settings import settings

load_dotenv()


def upload_image(
        file_name: str,
        buf: bytes,
):
    Key = f'media/{file_name}.jpg'
    res = settings.s3_client.Bucket(os.getenv('AWS_STORAGE_BUCKET_NAME')).put_object(
        Key=Key,
        Body=buf,
        ContentType='image/jpeg'
    )
    return os.getenv('S3_BASE_URL') + Key

import boto3
import json
import logging
import re
from typing import Optional, Dict, Any, BinaryIO
from botocore.exceptions import ClientError
from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import datetime

# Try to import config module, fall back to environment variables
try:
    from config import get_aws_config
except ImportError:
    # Fallback if config module not available
    def get_aws_config():
        load_dotenv()
        return {
            "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "region_name": os.getenv("AWS_REGION", "us-east-1"),
            "bucket_name": os.getenv("S3_BUCKET_NAME", "excel-cleaner-storage")
        }

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        # Get configuration from config module or environment
        aws_config = get_aws_config()
        self.aws_access_key_id = aws_config["aws_access_key_id"]
        self.aws_secret_access_key = aws_config["aws_secret_access_key"]
        self.aws_region = aws_config["region_name"]
        self.bucket_name = aws_config["bucket_name"]
        
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            logger.warning("AWS credentials not configured. S3 operations will fail.")
            self.s3_client = None
        else:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region
            )
        
    def create_bucket_if_not_exists(self):
        """Create S3 bucket if it doesn't exist"""
        if not self.s3_client:
            logger.warning("S3 client not initialized. Skipping bucket creation.")
            return False
            
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} already exists and is accessible")
            return True
        except ClientError as e:
            error_code = e.response['Error'].get('Code', '')
            
            # Handle 403 Forbidden - bucket exists but we don't have access
            if error_code == '403':
                logger.warning(f"Bucket {self.bucket_name} exists but access is forbidden. Attempting to use it anyway.")
                # Don't raise error, just log and continue
                # The actual upload might still work if we have PutObject permissions
                return True
                
            # Handle 404 Not Found - bucket doesn't exist
            elif error_code == '404':
                try:
                    logger.info(f"Bucket {self.bucket_name} not found. Attempting to create it...")
                    if self.aws_region == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.aws_region}
                        )
                    logger.info(f"Successfully created bucket {self.bucket_name}")
                    return True
                except ClientError as create_error:
                    error_code = create_error.response['Error'].get('Code', '')
                    if error_code == 'BucketAlreadyExists' or error_code == 'BucketAlreadyOwnedByYou':
                        logger.info(f"Bucket {self.bucket_name} already exists")
                        return True
                    else:
                        logger.error(f"Error creating bucket: {create_error}")
                        return False
            else:
                logger.error(f"Unexpected error checking bucket: {e}")
                return False

    def upload_file(self, file_content: bytes, key: str, content_type: str = None) -> bool:
        """Upload file content to S3"""
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                **extra_args
            )
            logger.info(f"Successfully uploaded file to s3://{self.bucket_name}/{key}")
            return True
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            return False

    def download_file(self, key: str) -> Optional[bytes]:
        """Download file from S3"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"Error downloading file from S3: {e}")
            return None

    def _sanitize_name(self, name: str) -> str:
        """Sanitize file/folder names for S3"""
        # Remove file extension if present
        if name.endswith(('.xlsx', '.xls')):
            name = name[:-5] if name.endswith('.xlsx') else name[:-4]
        # Replace problematic characters with underscores
        name = re.sub(r'[^\w\-]', '_', name)
        # Remove multiple underscores
        name = re.sub(r'_+', '_', name)
        return name.strip('_')

    def upload_metadata(self, excel_id: str, excel_name: str, sheet_name: str, metadata: Dict[str, Any]) -> bool:
        """Upload metadata as JSON to S3"""
        try:
            excel_folder = self._sanitize_name(excel_name)
            sheet_folder = self._sanitize_name(sheet_name) if sheet_name else "default_sheet"
            metadata_key = f"{excel_folder}/{sheet_folder}/metadata/{excel_id}.json"
            metadata_json = json.dumps(metadata, indent=2, default=str)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=metadata_key,
                Body=metadata_json,
                ContentType='application/json'
            )
            logger.info(f"Successfully uploaded metadata to s3://{self.bucket_name}/{metadata_key}")
            return True
        except ClientError as e:
            logger.error(f"Error uploading metadata to S3: {e}")
            return False

    def download_metadata(self, excel_id: str, excel_name: str, sheet_name: str) -> Optional[Dict[str, Any]]:
        """Download metadata from S3"""
        try:
            excel_folder = self._sanitize_name(excel_name)
            sheet_folder = self._sanitize_name(sheet_name) if sheet_name else "default_sheet"
            metadata_key = f"{excel_folder}/{sheet_folder}/metadata/{excel_id}.json"
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=metadata_key)
            metadata_json = response['Body'].read().decode('utf-8')
            return json.loads(metadata_json)
        except ClientError as e:
            logger.error(f"Error downloading metadata from S3: {e}")
            return None

    def upload_original_file(self, excel_id: str, excel_name: str, sheet_name: str, file_content: bytes) -> bool:
        """Upload original Excel file to uploads folder"""
        excel_folder = self._sanitize_name(excel_name)
        sheet_folder = self._sanitize_name(sheet_name) if sheet_name else "default_sheet"
        key = f"{excel_folder}/{sheet_folder}/uploads/{excel_id}.xlsx"
        return self.upload_file(file_content, key, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def upload_cleaned_file(self, excel_id: str, excel_name: str, sheet_name: str, file_content: bytes) -> bool:
        """Upload/overwrite cleaned Excel file in cleaned folder"""
        excel_folder = self._sanitize_name(excel_name)
        sheet_folder = self._sanitize_name(sheet_name) if sheet_name else "default_sheet"
        key = f"{excel_folder}/{sheet_folder}/cleaned/{excel_id}.xlsx"
        success = self.upload_file(file_content, key, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        if success:
            # Update metadata with last cleaned timestamp
            metadata = self.download_metadata(excel_id, excel_name, sheet_name) or {}
            metadata['last_cleaned'] = datetime.now().isoformat()
            self.upload_metadata(excel_id, excel_name, sheet_name, metadata)
        
        return success

    def download_original_file(self, excel_id: str, excel_name: str, sheet_name: str) -> Optional[bytes]:
        """Download original Excel file from uploads folder"""
        excel_folder = self._sanitize_name(excel_name)
        sheet_folder = self._sanitize_name(sheet_name) if sheet_name else "default_sheet"
        key = f"{excel_folder}/{sheet_folder}/uploads/{excel_id}.xlsx"
        return self.download_file(key)

    def download_cleaned_file(self, excel_id: str, excel_name: str, sheet_name: str) -> Optional[bytes]:
        """Download cleaned Excel file from cleaned folder"""
        excel_folder = self._sanitize_name(excel_name)
        sheet_folder = self._sanitize_name(sheet_name) if sheet_name else "default_sheet"
        key = f"{excel_folder}/{sheet_folder}/cleaned/{excel_id}.xlsx"
        return self.download_file(key)

    def file_exists(self, excel_id: str, excel_name: str, sheet_name: str, file_type: str) -> bool:
        """Check if file exists in S3"""
        try:
            excel_folder = self._sanitize_name(excel_name)
            sheet_folder = self._sanitize_name(sheet_name) if sheet_name else "default_sheet"
            
            if file_type == "original":
                key = f"{excel_folder}/{sheet_folder}/uploads/{excel_id}.xlsx"
            elif file_type == "cleaned":
                key = f"{excel_folder}/{sheet_folder}/cleaned/{excel_id}.xlsx"
            elif file_type == "metadata":
                key = f"{excel_folder}/{sheet_folder}/metadata/{excel_id}.json"
            else:
                return False
            
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def delete_files(self, excel_id: str, excel_name: str, sheet_name: str) -> bool:
        """Delete all files for an excel_id from S3"""
        try:
            excel_folder = self._sanitize_name(excel_name)
            sheet_folder = self._sanitize_name(sheet_name) if sheet_name else "default_sheet"
            
            keys_to_delete = [
                f"{excel_folder}/{sheet_folder}/uploads/{excel_id}.xlsx",
                f"{excel_folder}/{sheet_folder}/cleaned/{excel_id}.xlsx",
                f"{excel_folder}/{sheet_folder}/metadata/{excel_id}.json"
            ]
            
            for key in keys_to_delete:
                try:
                    self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
                    logger.info(f"Deleted {key}")
                except ClientError:
                    pass  # File might not exist
            
            return True
        except ClientError as e:
            logger.error(f"Error deleting files from S3: {e}")
            return False

    def list_all_files(self) -> list:
        """List all Excel files with their structure"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Delimiter='/'
            )
            
            if 'Contents' not in response and 'CommonPrefixes' not in response:
                return []
            
            files_info = []
            
            # List all objects recursively
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=self.bucket_name)
            
            processed_combinations = set()
            
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        # Parse the key to extract excel_name, sheet_name, and excel_id
                        parts = key.split('/')
                        if len(parts) >= 4 and parts[2] == 'metadata' and key.endswith('.json'):
                            excel_name = parts[0]
                            sheet_name = parts[1]
                            excel_id = parts[3][:-5]  # Remove .json
                            
                            combination = f"{excel_name}/{sheet_name}/{excel_id}"
                            if combination not in processed_combinations:
                                processed_combinations.add(combination)
                                files_info.append({
                                    "excel_id": excel_id,
                                    "excel_name": excel_name,
                                    "sheet_name": sheet_name,
                                    "path": f"{excel_name}/{sheet_name}"
                                })
            
            return files_info
        except ClientError as e:
            logger.error(f"Error listing files: {e}")
            return []

    def get_file_info(self, excel_id: str, excel_name: str, sheet_name: str) -> Dict[str, Any]:
        """Get information about files for an Excel ID"""
        try:
            excel_folder = self._sanitize_name(excel_name)
            sheet_folder = self._sanitize_name(sheet_name) if sheet_name else "default_sheet"
            
            info = {
                "excel_id": excel_id,
                "excel_name": excel_name,
                "sheet_name": sheet_name,
                "original_file_exists": self.file_exists(excel_id, excel_name, sheet_name, "original"),
                "cleaned_file_exists": self.file_exists(excel_id, excel_name, sheet_name, "cleaned"),
                "metadata_exists": self.file_exists(excel_id, excel_name, sheet_name, "metadata")
            }
            
            # Add file sizes if they exist
            try:
                if info["original_file_exists"]:
                    key = f"{excel_folder}/{sheet_folder}/uploads/{excel_id}.xlsx"
                    response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
                    info["original_file_size"] = response['ContentLength']
                
                if info["cleaned_file_exists"]:
                    key = f"{excel_folder}/{sheet_folder}/cleaned/{excel_id}.xlsx"
                    response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
                    info["cleaned_file_size"] = response['ContentLength']
            except ClientError:
                pass
            
            return info
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return {"excel_id": excel_id, "error": str(e)}

s3_service = S3Service()
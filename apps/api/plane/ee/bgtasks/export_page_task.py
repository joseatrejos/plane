# Python imports
import logging
import os
import io
import tempfile
import zipfile
from datetime import datetime

# Third party imports
import boto3
import requests
from botocore.client import Config
from celery import shared_task
from collections import defaultdict

# Django imports
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db.models import Q, OuterRef, Exists, Subquery
from django.template.loader import render_to_string
from django.utils.html import strip_tags

# Module imports
from plane.db.models import (
    FileAsset,
    Page,
    PageLog,
    Issue,
    WorkspaceMember,
    ProjectPage,
    User,
)
from plane.ee.models import PageUser
from plane.license.utils.instance_value import get_email_configuration
from plane.utils.url import normalize_url_path
from plane.utils.exception_logger import log_exception
from plane.ee.utils.page_descendants import get_descendant_page_ids

logger = logging.getLogger(__name__)


def get_s3_client():
    """
    Get configured S3 client
    """
    if settings.AWS_S3_ENDPOINT_URL:
        return boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
        )
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )


class StreamingZipFile:
    """
    Custom ZIP file handler that creates ZIP in chunks and streams to S3
    """

    def __init__(self, s3_client, bucket, key, chunk_size=50 * 1024 * 1024):  # 50MB chunks
        self.s3_client = s3_client
        self.bucket = bucket
        self.key = key
        self.chunk_size = chunk_size
        self.upload_id = None
        self.parts = []
        self.part_number = 1
        self.buffer = io.BytesIO()
        self.temp_file = None
        self.zipf = None

    def __enter__(self):
        # Initialize multipart upload
        response = self.s3_client.create_multipart_upload(
            Bucket=self.bucket, Key=self.key, ContentType="application/zip"
        )
        self.upload_id = response["UploadId"]

        # Create temporary file for ZIP creation
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        self.zipf = zipfile.ZipFile(self.temp_file, "w", zipfile.ZIP_DEFLATED)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.zipf:
                self.zipf.close()

            if exc_type is not None:
                # Error occurred, abort multipart upload
                if self.upload_id:
                    self.s3_client.abort_multipart_upload(Bucket=self.bucket, Key=self.key, UploadId=self.upload_id)
                return False

            # Upload remaining data in temp file
            self._upload_remaining_chunks()

            # Complete multipart upload
            if self.parts:
                self.s3_client.complete_multipart_upload(
                    Bucket=self.bucket,
                    Key=self.key,
                    UploadId=self.upload_id,
                    MultipartUpload={"Parts": self.parts},
                )
            else:
                # If no parts were uploaded (very small file), upload as single object
                self.temp_file.seek(0)
                self.s3_client.upload_fileobj(
                    self.temp_file,
                    self.bucket,
                    self.key,
                    ExtraArgs={"ContentType": "application/zip"},
                )

        finally:
            if self.temp_file:
                self.temp_file.close()
                try:
                    os.unlink(self.temp_file.name)
                except OSError:
                    pass

    def _upload_remaining_chunks(self):
        """Upload the completed ZIP file in chunks"""
        if not self.temp_file:
            return

        self.temp_file.seek(0)

        while True:
            chunk = self.temp_file.read(self.chunk_size)
            if not chunk:
                break

            response = self.s3_client.upload_part(
                Bucket=self.bucket,
                Key=self.key,
                PartNumber=self.part_number,
                UploadId=self.upload_id,
                Body=chunk,
            )

            self.parts.append({"ETag": response["ETag"], "PartNumber": self.part_number})
            self.part_number += 1

            logger.info("Uploaded part %d (%d bytes)", self.part_number - 1, len(chunk))

    def add_file(self, archive_path, content=None, s3_key=None):
        """Add a file to the ZIP with memory-efficient processing"""
        if content is not None:
            # Add text/markdown content directly
            self.zipf.writestr(archive_path, content)
        elif s3_key is not None:
            # Stream S3 file in chunks to avoid memory issues
            self._add_s3_file_chunked(archive_path, s3_key)

    def _add_s3_file_chunked(self, archive_path, s3_key):
        """Add S3 file to ZIP by streaming in chunks"""
        try:
            # Get file size first
            response = self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
            file_size = response["ContentLength"]

            # For small files (< 10MB), download directly
            if file_size < 10 * 1024 * 1024:
                buffer = io.BytesIO()
                self.s3_client.download_fileobj(self.bucket, s3_key, buffer)
                buffer.seek(0)
                self.zipf.writestr(archive_path, buffer.read())
                return

            # For large files, we need to use a temporary file approach
            # since zipfile doesn't support streaming writes for individual files
            with tempfile.NamedTemporaryFile() as temp_asset:
                # Download in chunks to temp file
                chunk_size = 10 * 1024 * 1024  # 10MB chunks
                bytes_downloaded = 0

                while bytes_downloaded < file_size:
                    # Calculate range for this chunk
                    start_byte = bytes_downloaded
                    end_byte = min(bytes_downloaded + chunk_size - 1, file_size - 1)

                    # Download chunk
                    response = self.s3_client.get_object(
                        Bucket=self.bucket,
                        Key=s3_key,
                        Range=f"bytes={start_byte}-{end_byte}",
                    )

                    chunk_data = response["Body"].read()
                    temp_asset.write(chunk_data)
                    bytes_downloaded += len(chunk_data)

                    logger.debug(
                        "Downloaded chunk %d-%d for %s",
                        start_byte,
                        end_byte,
                        archive_path,
                    )

                # Add the complete file to ZIP
                temp_asset.seek(0)
                self.zipf.writestr(archive_path, temp_asset.read())

        except Exception as exc:
            logger.error("Failed to add S3 file %s to ZIP: %s", s3_key, str(exc))
            # Add error file instead
            error_content = f"Error downloading asset: {str(exc)}"
            self.zipf.writestr(f"{archive_path}.error.txt", error_content)


def send_export_email(email, presigned_url, filename, rows=None):
    """
    Helper function to send export email with a presigned URL for download
    """
    logger.info("Sending email to %s with presigned URL: %s", email, presigned_url)
    subject = "Your Export is ready"
    html_content = render_to_string(
        "emails/exports/page.html",
        {
            "rows": rows or [],
            "download_url": presigned_url,
            "filename": filename,
            "expiry_days": 7,
        },
    )
    text_content = strip_tags(html_content)

    (
        EMAIL_HOST,
        EMAIL_HOST_USER,
        EMAIL_HOST_PASSWORD,
        EMAIL_PORT,
        EMAIL_USE_TLS,
        EMAIL_USE_SSL,
        EMAIL_FROM,
    ) = get_email_configuration()

    connection = get_connection(
        host=EMAIL_HOST,
        port=int(EMAIL_PORT),
        username=EMAIL_HOST_USER,
        password=EMAIL_HOST_PASSWORD,
        use_tls=EMAIL_USE_TLS == "1",
        use_ssl=EMAIL_USE_SSL == "1",
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=EMAIL_FROM,
        to=[email],
        connection=connection,
    )

    # Attach HTML content as an alternative
    msg.attach_alternative(html_content, "text/html")

    msg.send(fail_silently=False)
    return


def build_page_hierarchy(type, slug, project_id=None, user_id=None, page_id=None):
    """
    Build the page hierarchy.
    - If page_id is provided → return only that page + all its descendants.
    - If no page_id → return all root-level pages and their complete hierarchies.
    """

    if type not in ["WORKSPACE", "PROJECT"]:
        return None

    # Start with base queryset - filters first, then limit fields with .values()
    pages_qs = Page.objects.filter(workspace__slug=slug, moved_to_page__isnull=True)

    if type == "WORKSPACE":
        pages_qs = pages_qs.filter(is_global=True)
        # Use Exists subquery instead of loading all IDs into memory
        user_pages_subquery = PageUser.objects.filter(
            user_id=user_id,
            workspace__slug=slug,
            page__is_global=True,
            page_id=OuterRef("id"),
        )
        access_filter = Q(owned_by=user_id) | Q(access=0) | Q(Exists(user_pages_subquery))
    else:
        project_page_subquery = ProjectPage.objects.filter(page_id=OuterRef("id"), project_id=project_id).values_list(
            "page_id", flat=True
        )
        access_filter = Q(owned_by=user_id) | Q(access=0) | Q(id__in=project_page_subquery)

    # Apply filters
    pages_qs = pages_qs.filter(access_filter)

    if page_id:
        page_ids = get_descendant_page_ids(page_id) + [page_id]
        pages_qs = pages_qs.filter(id__in=page_ids)

    # ⚡ Return only lightweight dicts instead of full model instances
    # Apply .values() at the end to limit fields fetched from DB
    pages = pages_qs.values("id", "parent_id", "created_at")

    # Convert to list for easier processing
    pages_list = list(pages)

    # Build parent → children map
    children_map = defaultdict(list)
    pages_dict = {}  # id → page mapping for quick lookup

    for page in pages_list:
        children_map[page["parent_id"]].append(page)
        pages_dict[page["id"]] = page

    def build_subtree(pid, level=0):
        """Recursively build subtree starting from given page id"""
        if pid not in pages_dict:
            return None

        return {
            "level": level,
            "page_id": pid,
            "children": [
                build_subtree(child["id"], level + 1)
                for child in sorted(children_map.get(pid, []), key=lambda x: x["created_at"])
            ],
        }

    if page_id:
        # Return hierarchy for the specific page and all its descendants
        if page_id not in pages_dict:
            return None  # Page not found or no access
        return build_subtree(page_id)
    else:
        # Return all root-level pages (parent_id=None) with their complete hierarchies
        root_pages = children_map.get(None, [])
        return [build_subtree(root_page["id"]) for root_page in sorted(root_pages, key=lambda x: x["created_at"])]


def process_page_hierarchy_streaming(hierarchy, slug, streaming_zip, parent_path=""):
    """
    Process a page hierarchy and add files directly to streaming ZIP
    """
    current_page = hierarchy["page_id"]
    current_path = f"{parent_path}/{current_page}" if parent_path else str(current_page)

    # Fetch page content in markdown format
    markdown_content = fetch_page_markdown(current_page, slug)

    # Add markdown file directly to ZIP
    streaming_zip.add_file(archive_path=f"{current_path}/{current_page}.md", content=markdown_content)

    # Process images/attachments from file asset
    file_assets = (
        FileAsset.objects.filter(
            Q(entity_identifier=current_page) | Q(page_id=current_page),
        )
        .filter(
            entity_type=FileAsset.EntityTypeContext.PAGE_DESCRIPTION,
            is_uploaded=True,  # Only fetch uploaded assets
        )
        .values("id", "asset", "attributes")  # Fetch 'asset' field which has the full S3 key
    )

    logger.info("Found %s file assets for page %s", file_assets.count(), current_page)

    # Add asset files directly to ZIP (one by one, streaming)
    for asset in file_assets:
        try:
            # Get the S3 key (full path) to download from S3
            s3_key = asset.get("asset")
            if not s3_key:
                logger.warning("Asset %s has no S3 key, skipping", asset.get("id"))
                continue

            # Get the user-friendly filename from attributes to use in the ZIP archive
            attributes = asset.get("attributes") or {}
            filename = attributes.get("name")
            if not filename:
                logger.warning("Asset %s has no filename in attributes, skipping", asset.get("id"))
                continue

            # Add asset directly to streaming ZIP
            # - Archive path uses the user-friendly filename
            # - S3 key is the full path to download from S3
            streaming_zip.add_file(archive_path=f"{current_path}/{filename}", s3_key=s3_key)

            logger.info("Added asset %s to streaming ZIP (S3 key: %s)", filename, s3_key)
        except Exception as exc:
            asset_id = asset.get("id", "unknown")
            filename = asset.get("attributes", {}).get("name", "unknown")
            logger.error("Failed to process asset %s (filename: %s): %s", asset_id, filename, str(exc))

    # Process child pages recursively
    for child_hierarchy in hierarchy["children"]:
        process_page_hierarchy_streaming(child_hierarchy, slug, streaming_zip, current_path)


def create_streaming_zip(file_manifest, zip_key, bucket=None, expires_in=604800):
    """
    Create a ZIP using streaming multipart upload to S3 with minimal memory usage.
    Args:
        file_manifest: list of file objects with type, archive_path, and content/s3_key
        zip_key: destination key in S3
        bucket: S3 bucket name (default: from settings)
        expires_in: presigned URL expiry (default 7 days)
    """
    if bucket is None:
        bucket = settings.AWS_STORAGE_BUCKET_NAME

    s3 = get_s3_client()

    with StreamingZipFile(s3, bucket, zip_key) as streaming_zip:
        for file_item in file_manifest:
            archive_path = file_item["archive_path"]

            if file_item["type"] == "markdown":
                # Add markdown content directly
                streaming_zip.add_file(archive_path, content=file_item["content"])

            elif file_item["type"] == "asset":
                # Add S3 asset file (will be streamed in chunks)
                streaming_zip.add_file(archive_path, s3_key=file_item["s3_key"])

    # Return presigned URL
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": zip_key},
        ExpiresIn=expires_in,
    )


def create_streaming_zip_direct(page_hierarchy, slug, zip_key, bucket=None, expires_in=604800):
    """
    Create a ZIP using direct streaming - process files one by one without building manifest
    Args:
        page_hierarchy: page hierarchy structure
        slug: workspace slug
        zip_key: destination key in S3
        bucket: S3 bucket name (default: from settings)
        expires_in: presigned URL expiry (default 7 days)
    """
    if bucket is None:
        bucket = settings.AWS_STORAGE_BUCKET_NAME

    s3 = get_s3_client()

    with StreamingZipFile(s3, bucket, zip_key) as streaming_zip:
        # Handle multiple root pages or single page hierarchy
        if isinstance(page_hierarchy, list):
            # Multiple root pages - process each one
            for root_hierarchy in page_hierarchy:
                process_page_hierarchy_streaming(root_hierarchy, slug, streaming_zip)
        else:
            # Single page hierarchy
            process_page_hierarchy_streaming(page_hierarchy, slug, streaming_zip)

    # Return presigned URL
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": zip_key},
        ExpiresIn=expires_in,
    )


def fetch_page_markdown(page_id, slug):
    """
    Fetch page content in markdown format from live server
    """
    try:
        # Only fetch the fields we need to minimize memory usage
        page = (
            Page.objects.filter(pk=page_id, workspace__slug=slug)
            .annotate(project_id=Subquery(ProjectPage.objects.filter(page_id=OuterRef("id")).values("project_id")))
            .values("id", "name", "description_html", "workspace__slug", "project_id")
            .first()
        )

        if not page:
            return f"# {page_id}\n\nError: Page not found"

        # get all the file assets for the page and return the corresponding things in the body
        file_assets = FileAsset.objects.filter(
            page_id=page_id,
            entity_type=FileAsset.EntityTypeContext.PAGE_DESCRIPTION.value,
        ).values("id", "attributes__name")

        page_entities = PageLog.objects.filter(page_id=page_id).values("entity_name", "entity_identifier")

        # get all the issue embeds in the page from pagelog table
        issue_embeds = page_entities.filter(entity_name="issue").values_list("entity_identifier", flat=True).distinct()
        # get the basic details of the issue from the issue table
        issues = Issue.issue_objects.filter(id__in=issue_embeds).values("id", "project__identifier", "sequence_id")

        # get all work item mentions in the page from pagelog table
        page_log_work_item_mentions = (
            page_entities.filter(entity_name="issue_mention").values_list("entity_identifier", flat=True).distinct()
        )
        # get the basic details of the work item from the issue table
        work_item_mentions = Issue.issue_objects.filter(id__in=page_log_work_item_mentions).values(
            "id", "project__identifier", "sequence_id"
        )

        # get all the user mentions in the page from pagelog table
        page_user_mentions = (
            page_entities.filter(entity_name="user_mention").values_list("entity_identifier", flat=True).distinct()
        )
        # get the basic details of the user from the user table
        users_mentions = (
            User.objects.filter(id__in=page_user_mentions).filter(is_bot=False).values("id", "display_name").distinct()
        )

        # page embeds in the page from pagelog table
        page_embeds = (
            page_entities.filter(entity_name="sub_page").values_list("entity_identifier", flat=True).distinct()
        )
        # get the basic details of the page from the page table
        page_embeds = (
            Page.objects.filter(id__in=page_embeds)
            .filter(moved_to_page__isnull=True)
            .annotate(project_id=Subquery(ProjectPage.objects.filter(page_id=OuterRef("id")).values("project_id")[:1]))
            .values("id", "name", "project_id")
        )

        # Convert UUIDs to strings for JSON serialization
        file_assets_serializable = [
            {**asset, "id": str(asset["id"]), "name": asset["attributes__name"]} for asset in file_assets
        ]

        issues_serializable = [{**issue, "id": str(issue["id"])} for issue in issues]

        users_serializable = [
            {
                **user,
                "id": str(user["id"]),
                "display_name": user["display_name"],
            }
            for user in users_mentions
        ]

        pages_serializable = [
            {
                "id": str(p["id"]),
                "name": str(p["name"]),
                "project_id": str(p["project_id"]) if p["project_id"] else None,
            }
            for p in page_embeds
        ]

        work_item_mentions_serializable = [
            {
                "id": str(w["id"]),
                "project_identifier": str(w["project__identifier"]),
                "sequence_id": str(w["sequence_id"]),
            }
            for w in work_item_mentions
        ]

        # Combine all data into a single payload
        payload = {
            "id": str(page["id"]),
            "name": page["name"],
            "description_html": page["description_html"],
            "workspace__slug": str(page["workspace__slug"]),
            "meta_data": {
                "file_assets": file_assets_serializable,
                "work_item_embeds": issues_serializable,
                "user_mentions": users_serializable,
                "page_embeds": pages_serializable,
                "work_item_mentions": work_item_mentions_serializable,
            },
        }

        live_url = settings.LIVE_URL
        if not live_url:
            return "Error: fetching markdown from live server"

        url = normalize_url_path(f"{live_url}/convert-html-to-markdown/")

        response = requests.post(
            url,
            json=payload,
            headers={
                "LIVE-SERVER-SECRET-KEY": settings.LIVE_SERVER_SECRET_KEY,
            },
            timeout=30,
        )
        if response.status_code == 200:
            return response.json().get("markdown", "")
        return f"# {page_id}\n\nError: Server returned {response.status_code}"

    except requests.RequestException as exc:
        logger.error("Error fetching markdown for page %s: %s", page_id, str(exc))
        # Fallback to basic content if available
        return f"# {page_id}\n\nError fetching content: {str(exc)}"


@shared_task
def page_export_task(email, slug, user_id, type="WORKSPACE", project_id=None, page_id=None):
    """
    Export a page and all its sub-pages using streaming S3 workflow
    """
    try:
        # Build the complete page hierarchy
        page_hierarchy = build_page_hierarchy(type, slug, project_id, user_id, page_id)

        if not page_hierarchy:
            logger.error("No pages found for export")
            return

        # Create zip file in S3 using direct streaming (most memory efficient)
        zip_filename = f"{slug}_page_export.zip"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_key = f"exports/pages/{timestamp}_{zip_filename}"

        logger.info("Creating streaming zip file in S3")
        presigned_url = create_streaming_zip_direct(page_hierarchy, slug, zip_key)
        logger.info("Generated presigned URL: %s", presigned_url)

        # Send email with presigned URL
        send_export_email(email, presigned_url, zip_filename)
        logger.info("Email sent successfully")

        return presigned_url

    except Page.DoesNotExist:
        logger.error("Page with ID %s not found in workspace %s", page_id, slug)
        return
    except Exception as exc:
        logger.error("Error exporting page hierarchy: %s", str(exc))
        log_exception(exc)
        return


@shared_task
def cleanup_expired_exports():
    """
    Clean up expired export files from S3 (files older than 7 days)
    """
    try:
        s3 = get_s3_client()

        # List objects with the export prefix
        response = s3.list_objects_v2(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Prefix="exports/pages/")

        if "Contents" not in response:
            logger.info("No export files found to clean up")
            return 0

        deleted_count = 0
        for obj in response["Contents"]:
            # Check if file is older than 7 days
            file_age = (datetime.now() - obj["LastModified"].replace(tzinfo=None)).days

            if file_age >= 7:
                s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=obj["Key"])
                deleted_count += 1
                logger.info("Deleted expired export file: %s", obj["Key"])

        logger.info("Cleanup completed. Deleted %s expired files", deleted_count)
        return deleted_count

    except Exception as exc:
        logger.error("Error during export cleanup: %s", str(exc))
        return

from rest_framework import serializers
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.uploadedfile import UploadedFile


class ExtractionRequestSerializer(serializers.Serializer):
    """Handles the two required inputs: file upload and fields string."""

    # This field handles the PDF file upload

    document = serializers.FileField(
        help_text = "The PDF file to extract data from.",
        allow_empty_file=False
    )

    # This field handles the comma-separated string of fields
    fields = serializers.CharField(
        max_length=1024,
        help_text="Comma-separated names of the fields to extract (e.g., 'Invoice ID, Customer Name, Total Amount')."
    )

    # optional custom validation if needed(checking for specific file extensions)
    def validate_document(self, value: UploadedFile):
        if not value.name.lower().endswith('.pdf'):
            raise serializers.ValidationError("Only PDF files are supported.")
        return value
    
    
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from langchain_community.document_loaders import PyPDFLoader
from .serializers import ExtractionRequestSerializer
from .lc_service import create_extraction_schema, run_extraction_chain
import tempfile
import os

import logging

logger = logging.getLogger(__name__)


class StructuredExtractorAPIView(APIView):
    """
    API endpoint to accept PDF and fields, then return structured JSON data.
    Uses MultiPartParser for file uploads.
    """

    # This tells DRF to expect multipart form data
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):

        logger.info(
            f"Received extraction request from user: {request.user.id if request.user.is_authenticated else 'Anonymous'}")

        serializer = ExtractionRequestSerializer(data=request.data)

        if not serializer.is_valid():
            #  Log validation failure
            logger.warning(f"Request validation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # validate data
        document_file = serializer.validated_data['document']
        field_string = serializer.validated_data['fields']

        # Log validated request details
        logger.info(
            f"Starting extraction for file: {document_file.name}, requested fields: '{field_string}'")

        # langchain orchestraction

        try:
            # save the uploaded file temporarily to disk(langchain PyPDF loader often need a path)
            with tempfile.TemporaryFile(delete=False) as tmp_file:
                for chunk in document_file.chunks():
                    tmp_file.write(chunk)
                temp_path = tmp_file.name
            logger.debug(f"Temporary file created at: {temp_path}")

            # load and parse the PDF text
            loader = PyPDFLoader(temp_path)

            # load all pages and join the content into one large string
            pages = loader.load()

            document_text = "\n\n".join([page.page_content for page in pages])
            logger.debug(
                f"PDF successfully loaded. Total text length: {len(document_text)}")

            # dynamic pydantic schema
            DynamicSchema = create_extraction_schema(field_string)

            # run extraction pipeline
            extracted_data = run_extraction_chain(
                document_text=document_text,
                schema=DynamicSchema
            )

            # Log success and return response
            logger.info(
                f"Extraction complete for file: {document_file.name}. Result keys: {list(extracted_data.keys())}")

            # Return the structured JSON response
            return Response(extracted_data, status=status.HTTP_200_OK)

        except Exception as e:
            # Log critical errors with traceback
            # logger.exception logs the traceback automatically
            logger.exception(
                f"CRITICAL EXTRACTION ERROR for file: {document_file.name}")

            # error handling and logging
            print(f"Extraction Error: {e}")
            return Response(
                {"detail": f"An error occurred during extraction: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # CRITICAL: Clean up the temporary file
            if "temp_path" in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
                logger.debug(f"Cleaned up temporary file: {temp_path}")

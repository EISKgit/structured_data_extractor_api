from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock


# dummy pdf content for testing
TEST_PDF_CONTENT = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 55 >>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(This is document text for testing.) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000107 00000 n\n0000000179 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n243\n%%EOF"


# target path for mocking the Langchain function
LC_MOCK_PATH = 'extractor.views.run_extraction_chain'


# --------- Test cases for success and failure--------------------

# Integration - This test simulates a successful request and verifies the core logic is called correctly with a mocked response.


class ExtractorAPITests(APITestCase):
    url = reverse('structured-extract')

    @patch(LC_MOCK_PATH)
    def test_successful_data_extraction(self, mock_run_chain):
        # mock response from the url
        mock_response = {
            "invoice_number": "INV-2025-456",
            "customer_name": "Acme Corp.",
            "total_amount": "500.00"
        }

        mock_run_chain.return_value = mock_response

        # multipart data
        test_file = SimpleUploadedFile(
            "test_invoice.pdf",
            TEST_PDF_CONTENT,
            content_type="application/pdf"
        )

        data = {
            'document': test_file,
            'fields': 'Invoice Number, Customer Name, Total Amount'
        }

        # make the request
        response = self.client.post(self.url, data, format='multipart')

        # assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), mock_response)

        # verify the langchain function was actually called once
        mock_run_chain.assert_called_once()


# --------------- Validation Test Cases (Failure) ----------

    def test_missing_fileds(self):
        """Should fail if the 'fields' parameter is missing. """
        test_file = SimpleUploadedFile(
            "test.pdf",
            TEST_PDF_CONTENT,
            content_type="application/pdf"
        )

        data = {'document': test_file}  # fields is missing

        response = self.client.post(self.url, data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check that the correct error field is returned
        self.assertIn('fields', response.json())

    def test_invalid_file_type(self):
        """Should fail if a non-PDF file is uploaded."""

        # dummy test file
        test_file = SimpleUploadedFile(
            "test_doc.txt",
            b"This is not a PDF.",
            content_type="text/plain"
        )

        data = {
            'document': test_file,
            'fields': 'Name'
        }

        response = self.client.post(self.url, data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        #  implemented a custom validation for PDF in  Serializer.
        self.assertIn('document', response.json())


# ---------------- Null/Missing Data Test -----------------------------
# This test confirms the "CRITICAL RULE" of setting missing fields to null is handled by the overall system.

    @patch(LC_MOCK_PATH)
    def test_handles_missing_data_as_null(self, mock_run_chain):
        """Verifies that fields not found in the doc are returned as null."""

        #  Mock LangChain to return null for the missing field
        expected_response = {
            "name": "Acme Corp.",
            "total_amount": "100.00",
            "delivery_driver": None  # This field was requested but not found
        }
        mock_run_chain.return_value = expected_response

        test_file = SimpleUploadedFile("doc.pdf", TEST_PDF_CONTENT)
        data = {
            'document': test_file,
            'fields': 'Name, Total Amount, Delivery Driver'
        }

        # Make the request
        response = self.client.post(self.url, data, format='multipart')

        # assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['delivery_driver'], None)
        self.assertEqual(response.json(), expected_response)

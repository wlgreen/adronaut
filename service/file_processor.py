import aiofiles
import os
import uuid
from typing import Dict, Any
import json
from fastapi import UploadFile
import PyPDF2
from PIL import Image
import pandas as pd
import io

class FileProcessor:
    """File processing and analysis utilities"""

    def __init__(self):
        self.upload_dir = "temp_uploads"
        os.makedirs(self.upload_dir, exist_ok=True)

    async def process_file(self, file: UploadFile, project_id: str) -> Dict[str, Any]:
        """Process uploaded file and extract summary information"""
        try:
            # Generate unique filename
            file_id = str(uuid.uuid4())
            file_extension = os.path.splitext(file.filename)[1]
            temp_filename = f"{file_id}{file_extension}"
            temp_path = os.path.join(self.upload_dir, temp_filename)

            # Save file temporarily
            async with aiofiles.open(temp_path, 'wb') as f:
                content = await file.read()
                await f.write(content)

            # Extract summary based on file type
            summary = await self._extract_summary(temp_path, file.content_type)

            # In a real implementation, this would upload to Supabase Storage
            # For MVP, we'll simulate storage URL
            storage_url = f"storage://artifacts/{project_id}/{temp_filename}"

            # Clean up temp file
            try:
                os.remove(temp_path)
            except:
                pass

            return {
                "artifact_id": file_id,
                "storage_url": storage_url,
                "summary": summary
            }

        except Exception as e:
            print(f"File processing error: {e}")
            return {
                "artifact_id": str(uuid.uuid4()),
                "storage_url": f"storage://artifacts/{project_id}/error",
                "summary": {"error": str(e)}
            }

    async def _extract_summary(self, file_path: str, mime_type: str) -> Dict[str, Any]:
        """Extract summary information from different file types"""
        try:
            if mime_type.startswith('text/csv') or file_path.endswith('.csv'):
                return await self._process_csv(file_path)
            elif mime_type.startswith('application/json') or file_path.endswith('.json'):
                return await self._process_json(file_path)
            elif mime_type.startswith('application/pdf') or file_path.endswith('.pdf'):
                return await self._process_pdf(file_path)
            elif mime_type.startswith('image/'):
                return await self._process_image(file_path)
            else:
                return await self._process_generic(file_path)

        except Exception as e:
            return {"processing_error": str(e), "file_type": mime_type}

    async def _process_csv(self, file_path: str) -> Dict[str, Any]:
        """Process CSV files and extract marketing-relevant insights"""
        try:
            df = pd.read_csv(file_path)

            summary = {
                "file_type": "csv",
                "rows": len(df),
                "columns": list(df.columns),
                "column_count": len(df.columns),
                "data_types": df.dtypes.to_dict(),
                "sample_data": df.head(3).to_dict('records') if len(df) > 0 else [],
                "marketing_insights": {}
            }

            # Try to identify marketing-relevant columns
            marketing_columns = {
                "revenue": ["revenue", "sales", "amount", "price", "cost"],
                "metrics": ["clicks", "impressions", "views", "conversions", "ctr", "cpc", "cpm"],
                "demographic": ["age", "gender", "location", "region", "country"],
                "temporal": ["date", "time", "timestamp", "created_at", "month", "week"]
            }

            identified_columns = {}
            for category, keywords in marketing_columns.items():
                identified_columns[category] = []
                for col in df.columns:
                    if any(keyword.lower() in col.lower() for keyword in keywords):
                        identified_columns[category].append(col)

            summary["marketing_insights"]["identified_columns"] = identified_columns

            # Basic statistics for numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                summary["marketing_insights"]["numeric_summary"] = df[numeric_cols].describe().to_dict()

            return summary

        except Exception as e:
            return {"file_type": "csv", "error": str(e)}

    async def _process_json(self, file_path: str) -> Dict[str, Any]:
        """Process JSON files"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            summary = {
                "file_type": "json",
                "structure": self._analyze_json_structure(data),
                "keys": list(data.keys()) if isinstance(data, dict) else [],
                "size": len(data) if isinstance(data, (list, dict)) else 1,
                "sample_data": data if len(str(data)) < 1000 else str(data)[:1000] + "..."
            }

            return summary

        except Exception as e:
            return {"file_type": "json", "error": str(e)}

    async def _process_pdf(self, file_path: str) -> Dict[str, Any]:
        """Process PDF files"""
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)

                text_content = ""
                for page in pdf_reader.pages[:3]:  # First 3 pages only
                    text_content += page.extract_text()

            summary = {
                "file_type": "pdf",
                "pages": len(pdf_reader.pages),
                "text_preview": text_content[:500] + "..." if len(text_content) > 500 else text_content,
                "text_length": len(text_content),
                "metadata": {
                    "title": pdf_reader.metadata.get('/Title', '') if pdf_reader.metadata else '',
                    "author": pdf_reader.metadata.get('/Author', '') if pdf_reader.metadata else ''
                }
            }

            return summary

        except Exception as e:
            return {"file_type": "pdf", "error": str(e)}

    async def _process_image(self, file_path: str) -> Dict[str, Any]:
        """Process image files"""
        try:
            with Image.open(file_path) as img:
                summary = {
                    "file_type": "image",
                    "dimensions": img.size,
                    "mode": img.mode,
                    "format": img.format,
                    "has_transparency": img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                }

            return summary

        except Exception as e:
            return {"file_type": "image", "error": str(e)}

    async def _process_generic(self, file_path: str) -> Dict[str, Any]:
        """Process generic files"""
        try:
            file_stats = os.stat(file_path)

            # Try to read as text
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(1000)  # First 1000 chars
                text_preview = content
            except:
                text_preview = "Binary file or encoding issue"

            summary = {
                "file_type": "generic",
                "size_bytes": file_stats.st_size,
                "text_preview": text_preview,
                "is_text": text_preview != "Binary file or encoding issue"
            }

            return summary

        except Exception as e:
            return {"file_type": "generic", "error": str(e)}

    def _analyze_json_structure(self, data: Any, max_depth: int = 3, current_depth: int = 0) -> Dict[str, Any]:
        """Analyze JSON structure recursively"""
        if current_depth >= max_depth:
            return {"type": type(data).__name__, "truncated": True}

        if isinstance(data, dict):
            return {
                "type": "dict",
                "keys": list(data.keys()),
                "key_count": len(data),
                "sample_values": {k: self._analyze_json_structure(v, max_depth, current_depth + 1)
                                for k, v in list(data.items())[:3]}
            }
        elif isinstance(data, list):
            return {
                "type": "list",
                "length": len(data),
                "sample_items": [self._analyze_json_structure(item, max_depth, current_depth + 1)
                               for item in data[:3]]
            }
        else:
            return {
                "type": type(data).__name__,
                "value": str(data)[:100] + "..." if len(str(data)) > 100 else str(data)
            }
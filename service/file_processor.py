import aiofiles
import os
import uuid
from typing import Dict, Any, Tuple
import json
from fastapi import UploadFile
import PyPDF2
from PIL import Image
import pandas as pd
import io
import numpy as np
import base64

class FileProcessor:
    """File processing and analysis utilities"""

    def __init__(self):
        self.upload_dir = "temp_uploads"
        os.makedirs(self.upload_dir, exist_ok=True)

    def _serialize_data(self, data: Any) -> Any:
        """Convert non-serializable data types to JSON-serializable format"""
        if data is None:
            return None

        try:
            # Try direct JSON serialization first
            json.dumps(data)
            return data
        except (TypeError, ValueError):
            pass

        if isinstance(data, dict):
            return {k: self._serialize_data(v) for k, v in data.items()}
        elif isinstance(data, (list, tuple)):
            return [self._serialize_data(item) for item in data]
        elif isinstance(data, np.ndarray):
            return data.tolist()
        elif hasattr(data, 'dtype'):
            # Handle pandas/numpy data types
            try:
                if 'object' in str(data.dtype):
                    return str(data)
                elif 'int' in str(data.dtype):
                    return int(data)
                elif 'float' in str(data.dtype):
                    return float(data)
                else:
                    return str(data)
            except:
                return str(data)
        elif isinstance(data, (np.integer, np.floating, np.bool_)):
            return data.item()
        elif hasattr(data, '__dict__'):
            # Handle objects with attributes
            try:
                return str(data)
            except:
                return f"<{type(data).__name__} object>"
        else:
            try:
                return str(data)
            except:
                return f"<non-serializable {type(data).__name__}>"

    async def _prepare_file_storage(self, content: bytes, mime_type: str, project_id: str, filename: str) -> Tuple[str, str]:
        """Prepare file content for database storage"""
        try:
            # For text-based files, try to decode as UTF-8 and store as text
            if mime_type.startswith('text/') or mime_type in ['application/json', 'application/csv']:
                try:
                    text_content = content.decode('utf-8')
                    # Store as text directly for small files, base64 for large ones
                    if len(text_content) < 50000:  # 50KB limit for direct text storage
                        file_content = text_content
                    else:
                        file_content = base64.b64encode(content).decode('utf-8')
                except UnicodeDecodeError:
                    # Fall back to base64 if decode fails
                    file_content = base64.b64encode(content).decode('utf-8')
            else:
                # For binary files, always use base64
                file_content = base64.b64encode(content).decode('utf-8')

            # Create storage URL reference
            storage_url = f"db://artifacts/{project_id}/{filename}"

            return file_content, storage_url

        except Exception as e:
            print(f"File storage preparation error: {e}")
            # Fallback to base64 encoding
            return base64.b64encode(content).decode('utf-8'), f"db://artifacts/{project_id}/{filename}"

    async def process_file(self, file: UploadFile, project_id: str) -> Dict[str, Any]:
        """Process uploaded file and extract summary information"""
        try:
            # Generate unique filename
            file_id = str(uuid.uuid4())
            file_extension = os.path.splitext(file.filename)[1]
            temp_filename = f"{file_id}{file_extension}"
            temp_path = os.path.join(self.upload_dir, temp_filename)

            # Read file content into memory
            content = await file.read()
            file_size = len(content)

            # Save file temporarily for processing
            async with aiofiles.open(temp_path, 'wb') as f:
                await f.write(content)

            # Extract summary based on file type
            summary = await self._extract_summary(temp_path, file.content_type)

            # Store file content and metadata
            file_content_b64, storage_url = await self._prepare_file_storage(content, file.content_type, project_id, temp_filename)

            # Clean up temp file
            try:
                os.remove(temp_path)
            except:
                pass

            return {
                "artifact_id": file_id,
                "storage_url": storage_url,
                "file_content": file_content_b64,
                "file_size": file_size,
                "summary": self._serialize_data(summary)
            }

        except Exception as e:
            print(f"File processing error: {e}")
            return {
                "artifact_id": str(uuid.uuid4()),
                "storage_url": f"db://artifacts/{project_id}/error",
                "file_content": None,
                "file_size": 0,
                "summary": self._serialize_data({"error": str(e)})
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
                "data_types": {col: str(dtype) for col, dtype in df.dtypes.to_dict().items()},
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
                numeric_summary = df[numeric_cols].describe().to_dict()
                # Convert numpy types to Python types
                summary["marketing_insights"]["numeric_summary"] = {
                    col: {stat: float(val) if pd.notna(val) else None
                          for stat, val in stats.items()}
                    for col, stats in numeric_summary.items()
                }

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
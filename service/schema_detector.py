"""
Schema Detector - Auto-detect data structure for generic marketing data
Classifies columns into dimensions, metrics (efficiency/cost/volume), and identifiers
"""

import logging
import re
from typing import Dict, List, Any, Optional
from collections import Counter
import json

logger = logging.getLogger(__name__)


class SchemaDetector:
    """Automatically detect and classify data schema from marketing data"""

    # Common metric name patterns (case-insensitive)
    EFFICIENCY_PATTERNS = [
        r'roas', r'roi', r'return', r'ctr', r'click.*through', r'conversion.*rate',
        r'cvr', r'engagement.*rate', r'quality.*score', r'relevance.*score',
        r'view.*rate', r'completion.*rate', r'vtr'
    ]

    COST_PATTERNS = [
        r'cpc', r'cpa', r'cpm', r'cost.*per', r'acos', r'spend', r'budget',
        r'price', r'bid', r'cost', r'expense', r'cpl', r'cpe'
    ]

    VOLUME_PATTERNS = [
        r'impression', r'click', r'view', r'reach', r'order', r'conversion',
        r'sale', r'purchase', r'lead', r'signup', r'install', r'engagement',
        r'share', r'like', r'comment', r'follower'
    ]

    COMPARATIVE_PATTERNS = [
        (r'current', r'suggested'), (r'current', r'benchmark'), (r'actual', r'target'),
        (r'actual', r'expected'), (r'previous', r'current'), (r'before', r'after')
    ]

    # Common dimension patterns
    DIMENSION_PATTERNS = [
        r'keyword', r'campaign', r'ad.*group', r'creative', r'geo', r'location',
        r'region', r'country', r'city', r'device', r'platform', r'channel',
        r'audience', r'segment', r'age', r'gender', r'interest', r'placement',
        r'match.*type', r'type', r'category', r'product', r'sku'
    ]

    # Identifier patterns
    ID_PATTERNS = [r'id$', r'_id$', r'^id', r'uuid', r'guid', r'key']

    def __init__(self):
        self.efficiency_regex = [re.compile(p, re.IGNORECASE) for p in self.EFFICIENCY_PATTERNS]
        self.cost_regex = [re.compile(p, re.IGNORECASE) for p in self.COST_PATTERNS]
        self.volume_regex = [re.compile(p, re.IGNORECASE) for p in self.VOLUME_PATTERNS]
        self.dimension_regex = [re.compile(p, re.IGNORECASE) for p in self.DIMENSION_PATTERNS]
        self.id_regex = [re.compile(p, re.IGNORECASE) for p in self.ID_PATTERNS]

    def detect_schema(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Auto-detect schema from list of data rows

        Args:
            data: List of dicts (rows from CSV/JSON)

        Returns:
            Schema dict with classified columns
        """
        if not data:
            logger.warning("No data provided for schema detection")
            return self._empty_schema()

        logger.info(f"🔍 Detecting schema from {len(data)} rows")

        # Get all column names
        all_columns = set()
        for row in data:
            all_columns.update(row.keys())

        logger.info(f"Found {len(all_columns)} columns: {sorted(all_columns)}")

        # Classify each column
        dimensions = []
        identifiers = []
        metrics = {
            'efficiency_metrics': [],
            'cost_metrics': [],
            'volume_metrics': [],
            'comparative_metrics': []
        }
        unclassified = []

        for col in sorted(all_columns):
            # Extract column values
            values = [row.get(col) for row in data if col in row]
            classification = self._classify_column(col, values, all_columns)

            if classification == 'identifier':
                identifiers.append(col)
            elif classification == 'dimension':
                dimensions.append(col)
            elif classification == 'efficiency':
                metrics['efficiency_metrics'].append(col)
            elif classification == 'cost':
                metrics['cost_metrics'].append(col)
            elif classification == 'volume':
                metrics['volume_metrics'].append(col)
            elif classification == 'comparative':
                metrics['comparative_metrics'].append(col)
            else:
                unclassified.append(col)

        # Determine primary dimension (most informative categorical column)
        primary_dimension = self._determine_primary_dimension(dimensions, data)

        # Detect opportunities
        opportunities = self._detect_opportunities(data, dimensions, metrics)

        schema = {
            'primary_dimension': primary_dimension,
            'row_count': len(data),
            'dimensions': dimensions,
            'identifiers': identifiers,
            'metrics': metrics,
            'unclassified': unclassified,
            'opportunities': opportunities
        }

        logger.info(f"✅ Schema detected: {primary_dimension} ({len(data)} rows)")
        logger.info(f"   Dimensions: {len(dimensions)}")
        logger.info(f"   Efficiency metrics: {len(metrics['efficiency_metrics'])}")
        logger.info(f"   Cost metrics: {len(metrics['cost_metrics'])}")
        logger.info(f"   Volume metrics: {len(metrics['volume_metrics'])}")
        logger.info(f"   Opportunities: {len(opportunities)}")

        return schema

    def _classify_column(self, col_name: str, values: List[Any], all_columns: set) -> str:
        """
        Classify a single column by name pattern + value analysis

        Returns: 'identifier', 'dimension', 'efficiency', 'cost', 'volume', 'comparative', or 'unknown'
        """
        # Filter out None/empty values
        values = [v for v in values if v is not None and str(v).strip() != '']
        if not values:
            return 'unknown'

        # Check for identifier patterns
        if any(regex.search(col_name) for regex in self.id_regex):
            return 'identifier'

        # Check if numeric (potential metric)
        numeric_values = self._extract_numeric_values(values)
        is_numeric = len(numeric_values) > len(values) * 0.7  # 70%+ are numeric

        if is_numeric:
            # Classify by name pattern
            if any(regex.search(col_name) for regex in self.efficiency_regex):
                return 'efficiency'
            if any(regex.search(col_name) for regex in self.cost_regex):
                return 'cost'
            if any(regex.search(col_name) for regex in self.volume_regex):
                return 'volume'

            # Check for comparative pairs
            col_lower = col_name.lower()
            for prefix1, prefix2 in self.COMPARATIVE_PATTERNS:
                if re.search(prefix1, col_lower):
                    # Look for matching column with prefix2
                    partner_col = col_name.replace(prefix1, prefix2, 1)
                    if partner_col in all_columns:
                        return 'comparative'
                if re.search(prefix2, col_lower):
                    partner_col = col_name.replace(prefix2, prefix1, 1)
                    if partner_col in all_columns:
                        return 'comparative'

            # Check by value range
            if numeric_values:
                avg_val = sum(numeric_values) / len(numeric_values)
                max_val = max(numeric_values)

                # Efficiency metrics typically 0-100 or 0-10
                if 0 <= avg_val <= 100 and all(0 <= v <= 1000 for v in numeric_values[:20]):
                    return 'efficiency'

                # Large counts suggest volume
                if max_val > 1000:
                    return 'volume'

        # Check for dimension patterns
        if any(regex.search(col_name) for regex in self.dimension_regex):
            return 'dimension'

        # Categorical column (low cardinality) = dimension
        unique_count = len(set(str(v) for v in values))
        cardinality_ratio = unique_count / len(values) if len(values) > 0 else 0

        if cardinality_ratio < 0.5:  # <50% unique values
            return 'dimension'

        return 'unknown'

    def _extract_numeric_values(self, values: List[Any]) -> List[float]:
        """Extract numeric values from mixed-type list"""
        numeric = []
        for v in values:
            try:
                # Handle percentage strings
                if isinstance(v, str):
                    v_clean = v.replace('%', '').replace('$', '').replace(',', '').strip()
                    if v_clean and v_clean.replace('.', '', 1).replace('-', '', 1).isdigit():
                        numeric.append(float(v_clean))
                elif isinstance(v, (int, float)):
                    numeric.append(float(v))
            except (ValueError, AttributeError):
                continue
        return numeric

    def _determine_primary_dimension(self, dimensions: List[str], data: List[Dict]) -> str:
        """
        Determine the most informative dimension (primary grouping variable)

        Heuristics:
        1. Prefer "keyword" if present
        2. Otherwise, pick dimension with highest cardinality (most unique values)
        """
        if not dimensions:
            return 'row'  # Fallback

        # Check for keyword first
        for dim in dimensions:
            if 'keyword' in dim.lower():
                return dim

        # Check for campaign
        for dim in dimensions:
            if 'campaign' in dim.lower():
                return dim

        # Pick dimension with highest cardinality
        cardinalities = {}
        for dim in dimensions:
            unique_count = len(set(row.get(dim) for row in data if row.get(dim)))
            cardinalities[dim] = unique_count

        return max(cardinalities, key=cardinalities.get) if cardinalities else dimensions[0]

    def _detect_opportunities(
        self,
        data: List[Dict],
        dimensions: List[str],
        metrics: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """
        Detect high-level opportunities (gaps, concentrations, outliers)
        """
        opportunities = []

        # Check for comparative gaps
        comparative_metrics = metrics.get('comparative_metrics', [])
        for metric in comparative_metrics:
            # Find partner metric
            metric_lower = metric.lower()
            partner = None
            for comp_metric in comparative_metrics:
                if comp_metric != metric and any(
                    p1 in metric_lower and p2 in comp_metric.lower()
                    for p1, p2 in self.COMPARATIVE_PATTERNS
                ):
                    partner = comp_metric
                    break

            if partner:
                # Calculate average gap
                gaps = []
                for row in data:
                    val1 = self._extract_numeric_values([row.get(metric)])
                    val2 = self._extract_numeric_values([row.get(partner)])
                    if val1 and val2 and val2[0] != 0:
                        gap_pct = ((val1[0] - val2[0]) / val2[0]) * 100
                        gaps.append(gap_pct)

                if gaps:
                    avg_gap = sum(gaps) / len(gaps)
                    opportunities.append({
                        'type': 'comparative_gap',
                        'description': f"{metric} vs {partner}: avg gap {avg_gap:.1f}%",
                        'magnitude': abs(avg_gap),
                        'affected_count': len(gaps)
                    })

        return opportunities

    def build_data_dictionary(self, schema: Dict[str, Any], data: List[Dict[str, Any]]) -> str:
        """
        Generate human-readable data dictionary for LLM

        Returns formatted string describing the data
        """
        parts = []

        # Header
        parts.append(f"## Data Structure\n")
        parts.append(f"Dataset: {schema['row_count']} rows")
        parts.append(f"Primary dimension: {schema['primary_dimension']}\n")

        # Efficiency metrics
        if schema['metrics']['efficiency_metrics']:
            parts.append("### Efficiency Metrics (higher = better):")
            for metric in schema['metrics']['efficiency_metrics']:
                stats = self._calculate_metric_stats(metric, data)
                parts.append(f"- **{metric}**: {stats}")
            parts.append("")

        # Cost metrics
        if schema['metrics']['cost_metrics']:
            parts.append("### Cost Metrics (lower = better):")
            for metric in schema['metrics']['cost_metrics']:
                stats = self._calculate_metric_stats(metric, data)
                parts.append(f"- **{metric}**: {stats}")
            parts.append("")

        # Volume metrics
        if schema['metrics']['volume_metrics']:
            parts.append("### Volume Metrics:")
            for metric in schema['metrics']['volume_metrics']:
                stats = self._calculate_metric_stats(metric, data)
                parts.append(f"- **{metric}**: {stats}")
            parts.append("")

        # Opportunities
        if schema.get('opportunities'):
            parts.append("### Opportunities Detected:")
            for opp in schema['opportunities']:
                parts.append(f"- {opp['description']}")
            parts.append("")

        return "\n".join(parts)

    def _calculate_metric_stats(self, metric: str, data: List[Dict]) -> str:
        """Calculate min/max/avg for a metric"""
        values = []
        top_performer = None
        top_value = None

        for row in data:
            val = row.get(metric)
            numeric = self._extract_numeric_values([val])
            if numeric:
                values.append(numeric[0])
                if top_value is None or numeric[0] > top_value:
                    top_value = numeric[0]
                    # Try to get dimension value
                    for key, value in row.items():
                        if key not in [metric] and isinstance(value, str):
                            top_performer = value
                            break

        if not values:
            return "insufficient data"

        result = f"range {min(values):.2f}-{max(values):.2f}, avg {sum(values)/len(values):.2f}"
        if top_performer and top_value:
            result += f", top: '{top_performer}' ({top_value:.2f})"

        return result

    def _empty_schema(self) -> Dict[str, Any]:
        """Return empty schema structure"""
        return {
            'primary_dimension': 'row',
            'row_count': 0,
            'dimensions': [],
            'identifiers': [],
            'metrics': {
                'efficiency_metrics': [],
                'cost_metrics': [],
                'volume_metrics': [],
                'comparative_metrics': []
            },
            'unclassified': [],
            'opportunities': []
        }

"""
Merchant Mapping Editor and CLI Tool

Features:
- Add new merchant mappings via CLI
- Review and export unmapped merchants
- Import reviewed mappings from CSV
- Track mapping metadata (source, last_updated)
- Human-in-the-loop review workflow

Usage:
    # As module
    from mapping.editor import MerchantMappingEditor
    editor = MerchantMappingEditor()
    editor.add_mapping('Swiggy Ltd', 'Swiggy', 'Food')

    # As CLI (add to main CLI later)
    python -m mapping.editor add "Swiggy Ltd" "Swiggy" "Food"
"""

import pandas as pd
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import logging
import click

logger = logging.getLogger(__name__)


class MerchantMappingEditor:
    """Manage merchant mapping CSV with metadata tracking"""

    def __init__(self, mapping_file: str = "mapping/merchant_map.csv"):
        """
        Initialize merchant mapping editor

        Args:
            mapping_file: Path to merchant mapping CSV
        """
        self.mapping_file = Path(mapping_file)
        self.mapping_file.parent.mkdir(parents=True, exist_ok=True)

        self.df = self._load_mappings()

    def _load_mappings(self) -> pd.DataFrame:
        """
        Load mappings with metadata

        Returns:
            DataFrame with columns: merchant_raw, merchant_canonical, category,
                                   source, last_updated, confidence
        """
        if not self.mapping_file.exists():
            # Create empty DataFrame with schema
            return pd.DataFrame(columns=[
                'merchant_raw',
                'merchant_canonical',
                'category',
                'source',
                'last_updated',
                'confidence'
            ])

        try:
            df = pd.read_csv(self.mapping_file)

            # Add missing columns if they don't exist
            if 'source' not in df.columns:
                df['source'] = 'legacy'
            if 'last_updated' not in df.columns:
                df['last_updated'] = datetime.utcnow().isoformat() + 'Z'
            if 'confidence' not in df.columns:
                df['confidence'] = 1.0

            logger.info(f"Loaded {len(df)} merchant mappings from {self.mapping_file}")
            return df

        except Exception as e:
            logger.error(f"Failed to load merchant mappings: {e}")
            return pd.DataFrame(columns=[
                'merchant_raw', 'merchant_canonical', 'category',
                'source', 'last_updated', 'confidence'
            ])

    def add_mapping(self, merchant_raw: str, merchant_canonical: str,
                   category: str, source: str = 'manual') -> bool:
        """
        Add new merchant mapping

        Args:
            merchant_raw: Raw merchant name from transactions
            merchant_canonical: Canonical merchant name
            category: Category for this merchant
            source: Source of mapping (manual, auto, human_review)

        Returns:
            True if added, False if already exists
        """
        # Check if mapping already exists (case-insensitive)
        existing = self.df[self.df['merchant_raw'].str.lower() == merchant_raw.lower()]

        if len(existing) > 0:
            logger.warning(f"Mapping for '{merchant_raw}' already exists: "
                         f"{existing.iloc[0]['merchant_canonical']} -> {existing.iloc[0]['category']}")
            return False

        # Add new mapping
        new_row = pd.DataFrame([{
            'merchant_raw': merchant_raw,
            'merchant_canonical': merchant_canonical,
            'category': category,
            'source': source,
            'last_updated': datetime.utcnow().isoformat() + 'Z',
            'confidence': 1.0
        }])

        self.df = pd.concat([self.df, new_row], ignore_index=True)
        self._save_mappings()

        logger.info(f"✓ Added mapping: {merchant_raw} → {merchant_canonical} ({category})")
        return True

    def update_mapping(self, merchant_raw: str, merchant_canonical: Optional[str] = None,
                      category: Optional[str] = None) -> bool:
        """
        Update existing merchant mapping

        Args:
            merchant_raw: Raw merchant name to update
            merchant_canonical: New canonical name (optional)
            category: New category (optional)

        Returns:
            True if updated, False if not found
        """
        idx = self.df[self.df['merchant_raw'].str.lower() == merchant_raw.lower()].index

        if len(idx) == 0:
            logger.warning(f"Mapping for '{merchant_raw}' not found")
            return False

        # Update fields
        if merchant_canonical:
            self.df.loc[idx, 'merchant_canonical'] = merchant_canonical
        if category:
            self.df.loc[idx, 'category'] = category

        self.df.loc[idx, 'last_updated'] = datetime.utcnow().isoformat() + 'Z'
        self.df.loc[idx, 'source'] = 'manual_update'

        self._save_mappings()

        logger.info(f"✓ Updated mapping: {merchant_raw}")
        return True

    def export_unmapped_for_review(self, transactions: List[Dict],
                                   output_file: str = "mapping/unmapped_review.csv") -> str:
        """
        Export unmapped merchants for human review

        Args:
            transactions: List of transaction dictionaries
            output_file: Path to save review CSV

        Returns:
            Path to generated CSV file
        """
        unmapped = []
        unmapped_merchants = set()

        # Find uncategorized transactions
        for txn in transactions:
            if txn.get('category') == 'Uncategorized' and txn.get('merchant_raw'):
                merchant = txn['merchant_raw']

                # Skip if already processed
                if merchant in unmapped_merchants:
                    continue

                unmapped_merchants.add(merchant)

                # Count occurrences
                occurrences = sum(1 for t in transactions
                                if t.get('merchant_raw') == merchant)

                unmapped.append({
                    'merchant_raw': merchant,
                    'occurrences': occurrences,
                    'suggested_canonical': merchant,  # User can edit
                    'suggested_category': 'FILL_ME',  # User must fill
                    'reviewed': False,
                    'notes': ''
                })

        if not unmapped:
            logger.info("No unmapped merchants found")
            return None

        # Sort by occurrences (most frequent first)
        unmapped_df = pd.DataFrame(unmapped)
        unmapped_df = unmapped_df.sort_values('occurrences', ascending=False)

        # Save to CSV
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        unmapped_df.to_csv(output_path, index=False)

        logger.info(f"✓ Exported {len(unmapped)} unmapped merchants to {output_path}")
        logger.info(f"  Review the file and:")
        logger.info(f"    1. Fill in suggested_canonical and suggested_category")
        logger.info(f"    2. Set reviewed=True for entries you've completed")
        logger.info(f"    3. Run: finance-app import-mappings {output_path}")

        return str(output_path)

    def import_reviewed_mappings(self, review_file: str) -> int:
        """
        Import mappings from reviewed CSV

        Args:
            review_file: Path to reviewed CSV file

        Returns:
            Number of mappings imported
        """
        try:
            review_df = pd.read_csv(review_file)

            # Filter for reviewed entries with valid category
            reviewed = review_df[
                (review_df['reviewed'] == True) &
                (review_df['suggested_category'] != 'FILL_ME')
            ]

            count = 0
            for _, row in reviewed.iterrows():
                success = self.add_mapping(
                    row['merchant_raw'],
                    row['suggested_canonical'],
                    row['suggested_category'],
                    source='human_review'
                )
                if success:
                    count += 1

            logger.info(f"✓ Imported {count} reviewed mappings from {review_file}")
            return count

        except Exception as e:
            logger.error(f"Failed to import reviewed mappings: {e}")
            return 0

    def get_stats(self) -> Dict:
        """
        Get mapping statistics

        Returns:
            Dictionary with mapping stats
        """
        if len(self.df) == 0:
            return {
                'total_mappings': 0,
                'categories': {},
                'sources': {}
            }

        category_counts = self.df['category'].value_counts().to_dict()
        source_counts = self.df['source'].value_counts().to_dict()

        return {
            'total_mappings': len(self.df),
            'categories': category_counts,
            'sources': source_counts,
            'most_common_category': max(category_counts, key=category_counts.get) if category_counts else None
        }

    def _save_mappings(self):
        """Save mappings to CSV"""
        try:
            self.df.to_csv(self.mapping_file, index=False)
            logger.debug(f"Saved mappings to {self.mapping_file}")
        except Exception as e:
            logger.error(f"Failed to save mappings: {e}")


# CLI Interface (can be integrated into main CLI later)
@click.group()
def mapping_cli():
    """Merchant mapping management commands"""
    pass


@mapping_cli.command('add')
@click.argument('merchant_raw')
@click.argument('merchant_canonical')
@click.argument('category')
@click.option('--source', default='manual', help='Mapping source')
def add_mapping_cmd(merchant_raw, merchant_canonical, category, source):
    """
    Add a new merchant mapping

    Example:
        python -m mapping.editor add "Swiggy Ltd" "Swiggy" "Food"
    """
    editor = MerchantMappingEditor()
    success = editor.add_mapping(merchant_raw, merchant_canonical, category, source)

    if success:
        click.echo(f"✓ Added: {merchant_raw} → {merchant_canonical} ({category})")
    else:
        click.echo(f"✗ Mapping already exists for '{merchant_raw}'", err=True)
        click.echo("  Use 'update' command to modify existing mapping", err=True)


@mapping_cli.command('update')
@click.argument('merchant_raw')
@click.option('--canonical', help='New canonical name')
@click.option('--category', help='New category')
def update_mapping_cmd(merchant_raw, canonical, category):
    """
    Update existing merchant mapping

    Example:
        python -m mapping.editor update "Swiggy" --category "Food & Beverage"
    """
    if not canonical and not category:
        click.echo("Error: Provide at least --canonical or --category", err=True)
        return

    editor = MerchantMappingEditor()
    success = editor.update_mapping(merchant_raw, canonical, category)

    if success:
        click.echo(f"✓ Updated mapping for '{merchant_raw}'")
    else:
        click.echo(f"✗ Mapping not found for '{merchant_raw}'", err=True)


@mapping_cli.command('stats')
def stats_cmd():
    """Show mapping statistics"""
    editor = MerchantMappingEditor()
    stats = editor.get_stats()

    click.echo("\n" + "="*60)
    click.echo("MERCHANT MAPPING STATISTICS")
    click.echo("="*60)
    click.echo(f"\nTotal Mappings: {stats['total_mappings']}")

    if stats['categories']:
        click.echo("\nBy Category:")
        for cat, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True):
            click.echo(f"  {cat:<30} {count:>5}")

    if stats['sources']:
        click.echo("\nBy Source:")
        for source, count in stats['sources'].items():
            click.echo(f"  {source:<30} {count:>5}")

    click.echo()


@mapping_cli.command('export-unmapped')
@click.argument('transactions_file')
@click.option('--output', default='mapping/unmapped_review.csv', help='Output CSV file')
def export_unmapped_cmd(transactions_file, output):
    """
    Export unmapped merchants from transactions file

    Example:
        python -m mapping.editor export-unmapped data/transactions.jsonl
    """
    # Load transactions
    transactions = []
    try:
        with open(transactions_file, 'r') as f:
            for line in f:
                if line.strip():
                    transactions.append(json.loads(line))
    except Exception as e:
        click.echo(f"Error loading transactions: {e}", err=True)
        return

    editor = MerchantMappingEditor()
    output_path = editor.export_unmapped_for_review(transactions, output)

    if output_path:
        click.echo(f"✓ Exported unmapped merchants to {output_path}")
    else:
        click.echo("No unmapped merchants found")


@mapping_cli.command('import-reviewed')
@click.argument('review_file')
def import_reviewed_cmd(review_file):
    """
    Import reviewed mappings from CSV

    Example:
        python -m mapping.editor import-reviewed mapping/unmapped_review.csv
    """
    editor = MerchantMappingEditor()
    count = editor.import_reviewed_mappings(review_file)

    if count > 0:
        click.echo(f"✓ Imported {count} reviewed mappings")
    else:
        click.echo("No reviewed mappings found to import", err=True)


if __name__ == '__main__':
    mapping_cli()

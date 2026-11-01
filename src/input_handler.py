import os
from src.utils import logger
from src.data_loader import load_csv

class InputHandler:
    def __init__(self, config):
        self.config = config
        self.supported_extensions = ['.csv', '.pcap', '.pcapng']

    def validate_file(self, filepath):
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return False
        
        _, ext = os.path.splitext(filepath)
        if ext.lower() not in self.supported_extensions:
            logger.error(f"Unsupported file format: {ext}")
            return False
            
        return True

    def process_file(self, filepath, mode='detect'):
        """
        Routes the file to the correct processor based on extension.
        
        Args:
            filepath: Path to input file
            mode: 'detect' or 'train' (though 'train' usually takes directories)
        """
        if not self.validate_file(filepath):
            return None

        _, ext = os.path.splitext(filepath)
        ext = ext.lower()

        if ext == '.csv':
            logger.info(f"Processing CSV file: {filepath}")
            # For detection, we load the CSV and assume it fits the model schema
            return load_csv(filepath)
            
        elif ext in ['.pcap', '.pcapng']:
            logger.info(f"Processing PCAP file: {filepath}")
            from src.feature_extractor import FeatureExtractor
            extractor = FeatureExtractor(self.config)
            df = extractor.extract_features(filepath)
            
            if df is not None and not df.empty:
                logger.info(f"PCAP processing complete. Extracted {len(df)} flows.")
                return df
            else:
                logger.error("Failed to extract features from PCAP.")
                return None

import unittest
import numpy as np
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.feature_extractor import FeatureExtractor
from scapy.layers.inet import IP, TCP
from scapy.layers.l2 import Ether

class TestFeatureExtractor(unittest.TestCase):
    def setUp(self):
        self.config = {'selected_features': ['total fwd packets', 'flow duration', 'fwd psh flags']}
        self.extractor = FeatureExtractor(self.config)

    def test_calculate_flow_stats(self):
        # Create Synthetic Packets
        # A -> B (SYN) at t=0
        pkt1 = Ether()/IP(src="192.168.1.10", dst="10.0.0.5")/TCP(sport=1234, dport=80, flags="S")
        pkt1.time = 1000.0

        # B -> A (SYN-ACK) at t=0.1
        pkt2 = Ether()/IP(src="10.0.0.5", dst="192.168.1.10")/TCP(sport=80, dport=1234, flags="SA")
        pkt2.time = 1000.1

        # A -> B (ACK) at t=0.2
        pkt3 = Ether()/IP(src="192.168.1.10", dst="10.0.0.5")/TCP(sport=1234, dport=80, flags="A")
        pkt3.time = 1000.2

        # A -> B (PSH-ACK) at t=0.3
        pkt4 = Ether()/IP(src="192.168.1.10", dst="10.0.0.5")/TCP(sport=1234, dport=80, flags="PA")
        pkt4.time = 1000.3

        packets = [pkt1, pkt2, pkt3, pkt4]
        # Direction logic: 1 is Fwd (A->B), -1 is Bwd (B->A)
        # Pkt1: A->B (1)
        # Pkt2: B->A (-1)
        # Pkt3: A->B (1)
        # Pkt4: A->B (1)
        directions = [1, -1, 1, 1]

        flow_data = {'packets': packets, 'directions': directions}
        key = ("192.168.1.10", "10.0.0.5", 1234, 80, 6) # proto 6 is TCP
        initiator = ("192.168.1.10", 1234)

        # Calculate Stats
        stats = self.extractor._calculate_flow_stats(flow_data, key, initiator)

        # Assertions (Characterization)
        # Duration: 1000.3 - 1000.0 = 0.3s = 300,000 microseconds
        self.assertAlmostEqual(stats['flow duration'], 300000.0, delta=1.0)
        
        # Counts
        self.assertEqual(stats['total fwd packets'], 3)
        self.assertEqual(stats['total backward packets'], 1)

        # Flags (PSH)
        # Pkt4 has PSH flag and is Forward (A->B)
        self.assertEqual(stats['fwd psh flags'], 1)
        self.assertEqual(stats['bwd psh flags'], 0)

        # IAT
        # Flow IATs: [0.1, 0.1, 0.1] -> Mean = 0.1s = 100,000 us
        self.assertAlmostEqual(stats['flow iat mean'], 100000.0, delta=1.0)

if __name__ == '__main__':
    unittest.main()

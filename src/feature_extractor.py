import pandas as pd
import numpy as np
import logging
from scapy.all import PcapReader, IP, TCP, UDP
from collections import defaultdict
from src.utils import logger
import warnings
from typing import Dict, List, Tuple, Any, Optional

# Suppress Scapy runtime warnings
warnings.filterwarnings("ignore")

class FeatureExtractor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.selected_features = config.get('selected_features', [])
        
    def extract_features(self, pcap_path: str) -> Optional[pd.DataFrame]:
        """
        Reads a PCAP file and converts it to a DataFrame compatible with the model.
        Supports Bidirectional Flows by aggregating A->B and B->A into a single session.
        """
        logger.info(f"Extracting features from {pcap_path}...")
        
        # Store flows as: key -> {'packets': [], 'direction': []}
        # direction: 1 for forward (initiator), -1 for backward (responder)
        flows = defaultdict(lambda: {'packets': [], 'directions': []})
        
        # Store which IP/Port initiated the flow to maintain consistency
        # Key: canonical_tuple -> (src_ip, src_port) of initiator
        flow_initiators = {} 
        
        try:
            packet_count = 0
            with PcapReader(pcap_path) as packets:
                for pkt in packets:
                    if IP in pkt:
                        src_ip = pkt[IP].src
                        dst_ip = pkt[IP].dst
                        proto = pkt[IP].proto
                        
                        sport = 0
                        dport = 0
                        
                        if TCP in pkt:
                            sport = pkt[TCP].sport
                            dport = pkt[TCP].dport
                        elif UDP in pkt:
                            sport = pkt[UDP].sport
                            dport = pkt[UDP].dport
                            
                        # Canonical Key: Sorted tuples to treat (A,B) and (B,A) as same connection
                        # But protocol must match.
                        if src_ip < dst_ip:
                            key = (src_ip, dst_ip, sport, dport, proto)
                        else:
                            key = (dst_ip, src_ip, dport, sport, proto)
                            
                        # Determine Direction
                        if key not in flow_initiators:
                            # First packet sets the Forward direction
                            flow_initiators[key] = (src_ip, sport)
                            direction = 1 # Forward
                        else:
                            # Check if this packet matches initiator
                            init_ip, init_port = flow_initiators[key]
                            if src_ip == init_ip and sport == init_port:
                                direction = 1 # Forward
                            else:
                                direction = -1 # Backward
                                
                        flows[key]['packets'].append(pkt)
                        flows[key]['directions'].append(direction)
                        
                        packet_count += 1
                        if packet_count % 10000 == 0:
                            logger.info(f"Processed {packet_count} packets...")
                        
            logger.info(f"Aggregated {len(flows)} bidirectional sessions. Calculating statistics...")
            
            data = []
            
            for key, flow_data in flows.items():
                features = self._calculate_flow_stats(flow_data, key, flow_initiators[key])
                data.append(features)
                
            df = pd.DataFrame(data)
            
            # Ensure all selected features exist (fill missing with 0)
            for feature in self.selected_features:
                if feature not in df.columns:
                    df[feature] = 0.0
                    
            # Return selected features PLUS identifiers
            cols_to_return = ['src_ip', 'dst_ip', 'src_port', 'dst_port', 'protocol'] + self.selected_features
            
            # Filter only columns that exist
            cols_to_return = [c for c in cols_to_return if c in df.columns]
            
            return df[cols_to_return]
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _calculate_flow_stats(self, flow_data: Dict[str, List], key: Tuple, initiator: Tuple) -> Dict[str, Any]:
        """
        Calculates statistical features for a single flow (Bidirectional).
        Refactored to improve maintainability and readability.
        """
        packets = flow_data['packets']
        directions = flow_data['directions']
        
        stats = {}
        
        # 1. Identifiers
        self._set_identifiers(stats, key, initiator)
        
        # 2. Timestamps & Duration
        timestamps = [float(pkt.time) for pkt in packets]
        flow_duration_us = self._calculate_duration(timestamps)
        stats['flow duration'] = flow_duration_us
        
        # 3. Separate Directions
        fwd_pkts = [p for p, d in zip(packets, directions) if d == 1]
        bwd_pkts = [p for p, d in zip(packets, directions) if d == -1]
        
        # 4. Volume Stats (Counts, Lengths, Rates)
        self._calculate_volume_stats(stats, packets, fwd_pkts, bwd_pkts, flow_duration_us)
        
        # 5. Packet Length Stats
        self._calculate_len_stats(stats, fwd_pkts, bwd_pkts)
            
        # 6. IAT Stats
        self._calculate_iat_stats(stats, timestamps, fwd_pkts, bwd_pkts)
        
        # 7. Flags (TCP)
        self._calculate_flag_stats(stats, packets, directions)
        
        return stats

    def _set_identifiers(self, stats: Dict[str, Any], key: Tuple, initiator: Tuple):
        src_ip, src_port = initiator
        if src_ip == key[0]:
            dst_ip = key[1]
            dst_port = key[3]
        else:
            dst_ip = key[0]
            dst_port = key[2]
            
        proto = key[4]
        
        stats['src_ip'] = src_ip
        stats['dst_ip'] = dst_ip
        stats['src_port'] = src_port
        stats['dst_port'] = dst_port
        stats['protocol'] = proto

    def _calculate_duration(self, timestamps: List[float]) -> float:
        if not timestamps:
            return 0.0
        start_time = min(timestamps)
        end_time = max(timestamps)
        return (end_time - start_time) * 1e6 # microseconds

    def _calculate_volume_stats(self, stats: Dict[str, Any], packets: List, fwd_pkts: List, bwd_pkts: List, duration_us: float):
        fwd_lens = [len(p) for p in fwd_pkts]
        bwd_lens = [len(p) for p in bwd_pkts]
        
        stats['total fwd packets'] = len(fwd_pkts)
        stats['total backward packets'] = len(bwd_pkts)
        stats['total length of fwd packets'] = sum(fwd_lens)
        stats['total length of bwd packets'] = sum(bwd_lens)
        
        total_bytes = sum(fwd_lens) + sum(bwd_lens)
        # Avoid division by zero
        duration_sec = duration_us / 1e6
        stats['flow bytes/s'] = total_bytes / duration_sec if duration_sec > 0 else 0
        stats['flow packets/s'] = len(packets) / duration_sec if duration_sec > 0 else 0

    def _calculate_len_stats(self, stats: Dict[str, Any], fwd_pkts: List, bwd_pkts: List):
        fwd_lens = [len(p) for p in fwd_pkts]
        bwd_lens = [len(p) for p in bwd_pkts]
        
        self._set_stat_block(stats, 'fwd packet length', fwd_lens)
        self._set_stat_block(stats, 'bwd packet length', bwd_lens)

    def _calculate_iat_stats(self, stats: Dict[str, Any], timestamps: List[float], fwd_pkts: List, bwd_pkts: List):
        # Flow IAT
        if len(timestamps) > 1:
            iats = np.diff(sorted(timestamps)) * 1e6
            self._set_stat_block(stats, 'flow iat', iats, include_total=False)
        else:
            self._set_zero_stat_block(stats, 'flow iat', include_total=False)
            
        # Fwd IAT
        fwd_times = sorted([float(p.time) for p in fwd_pkts])
        if len(fwd_times) > 1:
            f_iats = np.diff(fwd_times) * 1e6
            self._set_stat_block(stats, 'fwd iat', f_iats, include_total=True)
        else:
            self._set_zero_stat_block(stats, 'fwd iat', include_total=True)
            
        # Bwd IAT
        bwd_times = sorted([float(p.time) for p in bwd_pkts])
        if len(bwd_times) > 1:
            b_iats = np.diff(bwd_times) * 1e6
            self._set_stat_block(stats, 'bwd iat', b_iats, include_total=True)
        else:
            self._set_zero_stat_block(stats, 'bwd iat', include_total=True)

    def _calculate_flag_stats(self, stats: Dict[str, Any], packets: List, directions: List[int]):
        fwd_psh = 0; bwd_psh = 0
        fwd_urg = 0; bwd_urg = 0
        
        for p, d in zip(packets, directions):
            if TCP in p:
                flags = p[TCP].flags
                # Scapy flags are objects, cast to str
                flags = str(flags)
                if 'P' in flags:
                    if d == 1: fwd_psh += 1
                    else: bwd_psh += 1
                if 'U' in flags:
                    if d == 1: fwd_urg += 1
                    else: bwd_urg += 1
                    
        stats['fwd psh flags'] = fwd_psh
        stats['bwd psh flags'] = bwd_psh
        stats['fwd urg flags'] = fwd_urg
        stats['bwd urg flags'] = bwd_urg

    def _set_stat_block(self, stats: Dict[str, Any], prefix: str, data: Any, include_total: bool = False):
        """Helper to set min, max, mean, std for a dataset"""
        if len(data) == 0:
            self._set_zero_stat_block(stats, prefix, include_total)
            return

        stats[f'{prefix} mean'] = np.mean(data)
        stats[f'{prefix} std'] = np.std(data)
        stats[f'{prefix} max'] = np.max(data)
        stats[f'{prefix} min'] = np.min(data)
        if include_total:
            stats[f'{prefix} total'] = sum(data)

    def _set_zero_stat_block(self, stats: Dict[str, Any], prefix: str, include_total: bool = False):
        stats[f'{prefix} mean'] = 0
        stats[f'{prefix} std'] = 0
        stats[f'{prefix} max'] = 0
        stats[f'{prefix} min'] = 0
        if include_total:
            stats[f'{prefix} total'] = 0

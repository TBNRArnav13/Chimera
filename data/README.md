# Chimera Dataset Directory & Documentation

This directory manages dataset ingestion and verification for the **Chimera Intrusion Detection System**.

---

## 1. Quick Verification (Sample Data Included)

Chimera includes a verified, lightweight sample dataset for immediate testing:
- **`data/sample_flows.csv`**: 200 standardized network flows (100 Benign, 100 DoS/DDoS attacks across multiple reflection vectors).

Run detection immediately:
```bash
python run.py detect --input data/sample_flows.csv
```

---

## 2. Benchmark Datasets (CIC-IDS2017 & CIC-DDoS2019)

As reported in the research paper (*IEEE CICN 2026*), Chimera is evaluated across 5.5 million network flows drawn from a corpus of 48.9 million flows spanning 10 distinct attack categories:
- **Download**: [UNB Datasets](https://www.unb.ca/cic/datasets/index.html)
- **10 Attack Vectors Covered**:
  1. DNS Amplification (`Polished_Dos_DNS.csv`)
  2. LDAP Reflection (`Polished_Dos_LDAP.csv`)
  3. MSSQL Floods (`Polished_Dos_MSSQL.csv`)
  4. NetBIOS Floods (`Polished_Dos_NetBIOS.csv`)
  5. NTP Amplification (`Polished_Dos_NTP.csv`)
  6. SNMP Floods (`Polished_Dos_SNMP.csv`)
  7. SSDP Reflection (`Polished_Dos_SSDP.csv`)
  8. SYN Floods (`Polished_Dos_Syn.csv`)
  9. TFTP Floods (`Polished_Dos_TFTP.csv`)
  10. UDP Floods (`Polished_Dos_UDP.csv`)

### Directory Mount Configuration

Place full datasets in `Dataset/` or configure custom paths in `config.yaml`:
```yaml
datasets:
  benign: "Dataset/PolishedBenign/Polished_benign.csv"
  dos: "Dataset/PolishedDos/"
```

---

## 3. Selected 33 Flow Features

Features are partitioned into four domain-driven groups corresponding to the paper's B-DAP autoencoders:
- **Volume (7 features)**: `flow duration`, `total fwd packets`, `total backward packets`, `total length of fwd packets`, `total length of bwd packets`, `flow bytes/s`, `flow packets/s`
- **Packet Size (8 features)**: `fwd packet length max/min/mean/std`, `bwd packet length max/min/mean/std`
- **Inter-Arrival Times (14 features)**: `flow iat mean/std/max/min`, `fwd iat total/mean/std/max/min`, `bwd iat total/mean/std/max/min`
- **TCP Control Flags (4 features)**: `fwd psh flags`, `bwd psh flags`, `fwd urg flags`, `bwd urg flags`

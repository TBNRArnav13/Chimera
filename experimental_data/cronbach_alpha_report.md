# Cronbach's Alpha Reliability Report
This report calculates the internal consistency (Cronbach's alpha) of the evaluation metrics (Accuracy) across the three separate runs for each model.

## Results
- **XGB Accuracy Cronbach's Alpha:** 1.0000
- **KITSUNE Accuracy Cronbach's Alpha:** 0.8114
- **HYBRID Accuracy Cronbach's Alpha:** 0.9994

## Interpretation
- **α ≥ 0.9:** Excellent reliability (the model's performance on the files is highly consistent across runs).
- **0.8 ≤ α < 0.9:** Good reliability.
- **0.7 ≤ α < 0.8:** Acceptable reliability.
- **α < 0.7:** Questionable/Poor reliability.

## Raw Accuracy Data by Run
### XGB
| File | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| Polished_Dos_DNS.csv | 0.9978 | 0.9978 | 0.9978 |
| Polished_Dos_LDAP.csv | 0.9999 | 0.9999 | 0.9999 |
| Polished_Dos_MSSQL.csv | 0.9996 | 0.9996 | 0.9996 |
| Polished_Dos_NTP.csv | 0.9928 | 0.9928 | 0.9928 |
| Polished_Dos_NetBIOS.csv | 0.9996 | 0.9996 | 0.9996 |
| Polished_Dos_SNMP.csv | 1.0000 | 1.0000 | 1.0000 |
| Polished_Dos_SSDP.csv | 0.9998 | 0.9998 | 0.9998 |
| Polished_Dos_Syn.csv | 0.9987 | 0.9987 | 0.9987 |
| Polished_Dos_UDP.csv | 0.9992 | 0.9992 | 0.9992 |
| Polished_benign.csv | 0.9938 | 0.9938 | 0.9938 |

### KITSUNE
| File | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| Polished_Dos_DNS.csv | 0.9732 | 0.7099 | 0.7099 |
| Polished_Dos_LDAP.csv | 0.9996 | 0.9268 | 0.9268 |
| Polished_Dos_MSSQL.csv | 0.9955 | 0.8034 | 0.8034 |
| Polished_Dos_NTP.csv | 0.4873 | 0.1419 | 0.1419 |
| Polished_Dos_NetBIOS.csv | 0.9454 | 0.4174 | 0.4174 |
| Polished_Dos_SNMP.csv | 0.8514 | 0.0006 | 0.0006 |
| Polished_Dos_SSDP.csv | 0.9514 | 0.4529 | 0.4529 |
| Polished_Dos_Syn.csv | 0.0002 | 0.4033 | 0.4033 |
| Polished_Dos_UDP.csv | 0.9182 | 0.1517 | 0.1517 |
| Polished_benign.csv | 0.9808 | 0.9824 | 0.9824 |

### HYBRID
| File | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| Polished_Dos_DNS.csv | 0.9970 | 0.9970 | 0.9970 |
| Polished_Dos_LDAP.csv | 0.9999 | 0.9999 | 0.9999 |
| Polished_Dos_MSSQL.csv | 0.9994 | 0.9995 | 0.9995 |
| Polished_Dos_NTP.csv | 0.9897 | 0.9907 | 0.9907 |
| Polished_Dos_NetBIOS.csv | 0.9994 | 0.9996 | 0.9996 |
| Polished_Dos_SNMP.csv | 1.0000 | 0.9999 | 0.9999 |
| Polished_Dos_SSDP.csv | 0.9997 | 0.9997 | 0.9997 |
| Polished_Dos_Syn.csv | 0.9987 | 0.9987 | 0.9987 |
| Polished_Dos_UDP.csv | 0.9989 | 0.9989 | 0.9989 |
| Polished_benign.csv | 0.9746 | 0.9762 | 0.9762 |

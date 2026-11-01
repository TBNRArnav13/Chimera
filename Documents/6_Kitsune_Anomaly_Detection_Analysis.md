# Kitsune Anomaly Detection: Technical Analysis

This document provides a deep dive into how the Kitsune model detects anomalies within the Unified DoS/DDoS Detection System. It covers the step-by-step detection process, the mathematical algorithms used, and a detailed breakdown of the features utilized.

## 1. Detection Process: Step-by-Step

Kitsune operates as an unsupervised anomaly detection system, meaning it learns what "normal" traffic looks like and flags anything that deviates significantly from that norm.

### Step 1: Traffic Interception & Feature Extraction
*   **Input**: Raw network traffic (PCAP/PCAPNG files) or live packet capture.
*   **Process**:
    1.  The system reads raw packets.
    2.  It aggregates packets into **Bidirectional Flows** (sessions between two IPs/Ports).
    3.  For each flow, it calculates a set of statistical features (see Section 3).
*   **Output**: A numerical vector $x$ representing the flow's behavior.

### Step 2: Model Inference (Reconstruction)
*   **Input**: Feature vector $x$.
*   **Process**:
    1.  The vector $x$ is fed into the **Autoencoder** neural network.
    2.  The Autoencoder compresses the data into a lower-dimensional representation (encoding).
    3.  It then attempts to reconstruct the original input from this compressed version.
*   **Output**: Reconstructed vector $x'$.

### Step 3: Anomaly Scoring (RMSE)
*   **Logic**:
    *   If the input $x$ represents **benign (normal)** traffic, the model (trained on benign data) can reconstruct it accurately. The difference between $x$ and $x'$ will be very small.
    *   If the input $x$ represents **anomalous (attack)** traffic, the model fails to reconstruct it accurately because it has never seen such patterns before. The difference between $x$ and $x'$ will be large.
*   **Calculation**: The system calculates the **Root Mean Square Error (RMSE)** between the input and the reconstruction.
    $$ \text{Score} = \text{RMSE}(x, x') $$

### Step 4: Thresholding & Verdict
*   **Input**: Anomaly Score (RMSE).
*   **Process**:
    1.  The score is compared against a pre-determined **Threshold** ($\tau$).
    2.  This threshold is established during the training phase (see Section 2).
*   **Verdict**:
    *   **If Score > $\tau$**: Traffic is flagged as an **Anomaly**.
    *   **If Score $\le$ $\tau$**: Traffic is considered **Benign** (by Kitsune).

---

## 2. Mathematical Algorithm

Kitsune uses an **Autoencoder** neural network to derive the RMSE score.

### 2.1 Model Architecture
The model is a feed-forward neural network with an encoder-decoder structure:
1.  **Encoder**: Compresses the input.
    *   Layer 1: Linear Transformation (Input Dim $\rightarrow$ Hidden Dim) + ReLU
    *   Layer 2: Linear Transformation (Hidden Dim $\rightarrow$ Bottleneck) + ReLU
2.  **Decoder**: Reconstructs the input.
    *   Layer 3: Linear Transformation (Bottleneck $\rightarrow$ Hidden Dim) + ReLU
    *   Layer 4: Linear Transformation (Hidden Dim $\rightarrow$ Output Dim)

$$ x' = \text{Decoder}(\text{Encoder}(x)) $$

### 2.2 Root Mean Square Error (RMSE)
The anomaly score is the Euclidean distance between the input vector $x$ and the reconstructed vector $x'$, normalized by the number of features ($N$).

$$ \text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (x_i - x'_i)^2} $$

*   $x_i$: Value of feature $i$ in the input.
*   $x'_i$: Value of feature $i$ in the reconstruction.

### 2.3 Dynamic Threshold Calculation
The threshold is not arbitrary; it is statistically derived from the training data (Benign traffic only).

1.  After training, the model processes the entire training set again to generate reconstruction errors (RMSE) for every benign sample.
2.  It calculates the **Mean** ($\mu$) and **Standard Deviation** ($\sigma$) of these errors.
3.  The threshold ($\tau$) is set as:
    $$ \tau = \mu + k \cdot \sigma $$
    *   **$\mu$**: Average reconstruction error for normal traffic.
    *   **$\sigma$**: Variability of the error for normal traffic.
    *   **$k$**: Sensitivity factor (configured as `threshold_std_factor` in `config.yaml`, default is 3.0).

*   *Interpretation*: We define "anomaly" as anything falling more than $k$ standard deviations away from the average normal error.

---

## 3. Feature Analysis

The model relies on **33 statistical features** extracted from each flow. These features capture volume, timing, and packet dynamics.

### 3.1 Packet Counts (Volume)
*   **flow duration**: Total time the connection was active (microseconds).
*   **total fwd packets**: Number of packets sent by the initiator.
*   **total backward packets**: Number of packets sent by the responder.
*   **flow bytes/s**: Speed of data transfer (Bytes per second).
*   **flow packets/s**: Rate of packet transfer (Packets per second).

   *Significance*: High packet rates or counts in short durations are classic signs of flooding attacks (UDP Flood, ICMP Flood).

### 3.2 Packet Lengths (Size Dynamics)
These features measure the payload size distribution.
*   **total length of fwd/bwd packets**: Total bytes transferred in each direction.
*   **fwd/bwd packet length max**: Size of the largest packet.
*   **fwd/bwd packet length min**: Size of the smallest packet.
*   **fwd/bwd packet length mean**: Average packet size.
*   **fwd/bwd packet length std**: Standard deviation (variability) of packet sizes.

   *Significance*:
    *   **DDoS**: Often uses fixed-size packets (zero std dev).
    *   **Normal**: Variable packet sizes (high std dev).
    *   **Exfiltration**: Unexpectedly large packets (high max/mean).

### 3.3 Inter-Arrival Times (IAT) (Timing)
These features measure the time gap between consecutive packets.
*   **flow iat mean/std/max/min**: Statistics for time between *any* two packets in the flow.
*   **fwd iat total/mean/std/max/min**: Statistics for time between packets sent by the initiator.
*   **bwd iat total/mean/std/max/min**: Statistics for time between packets sent by the responder.

   *Significance*:
    *   **Automated Attacks**: Often have very uniform timing (low/zero std dev) or extremely short gaps (low mean).
    *   **Human/Normal**: Bursty and irregular timing (high std dev).

### 3.4 TCP Flags (Behavior)
Counts of specific TCP control flags set in the packets.
*   **fwd/bwd psh flags**: PUSH flag (requests immediate data transfer).
*   **fwd/bwd urg flags**: URGENT flag (priority data).

   *Significance*: Abnormal usage of flags can indicate scanning attempts, OS fingerprinting, or specific TCP floods (e.g., PSH+ACK flood).

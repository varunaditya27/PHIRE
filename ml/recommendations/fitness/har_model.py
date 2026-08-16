"""
Human activity recognition (HAR) model for fitness recommendations.

Dataset decision (finalized, see docs/DATASETS_AND_GRAPH_RAG.md):
- Pretrain on PAMAP2 (CC BY 4.0, 100Hz multi-IMU, 18 activities, N=9) for a
  general activity representation.
- Fine-tune / deploy on WISDM (single accelerometer, phone/watch-realistic,
  20Hz, N=51) — WISDM's sensor placement matches real consumer wearables
  (Fitbit/Apple Watch/phone) far better than PAMAP2's chest+wrist+ankle rig,
  so it is the target feature space for the shipped classifier, not PAMAP2.

Responsibilities (to implement):
- Load/run a HAR model (lightweight 1D-CNN or CNN-LSTM, quantized for local
  inference) pretrained on PAMAP2 and fine-tuned on WISDM to classify
  activity from wearable/PGHD input.
- Both datasets only classify *which* activity is happening — they carry no
  form-quality signal. Do not use this model's output as a proxy for
  exercise form; see ml/recommendations/fitness/recommendations.py and the
  pose-based approach in docs/DATASETS_AND_GRAPH_RAG.md for that.
"""

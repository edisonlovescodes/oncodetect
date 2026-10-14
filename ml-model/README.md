# Historical model-development utilities

The serving artifact lives at `../backend/oncodetect_model_v3.h5`; its identical duplicate was removed from this tree. Historical files remain in Git history. The more complete extractor is `preprocess_data_v3_fixed.py`; the unfinished predecessor is retired.

These scripts are not a recovered training/evaluation pipeline. Data/label semantics, patient-disjoint splits, DICOM intensity conversion and trainer/serving equivalence still require review before a new scientific evaluation. They are not needed to run the local application.

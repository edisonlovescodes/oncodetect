import pylidc as pl
from tqdm import tqdm

print("Querying pylidc database...")
scans = pl.query(pl.Scan)
print(f"Found {scans.count()} scans")

patients = {}
for scan in tqdm(scans, desc="Analyzing"):
    for ann in scan.annotations:
        if ann.malignancy and ann.malignancy != 3:
            pid = scan.patient_id
            patients[pid] = patients.get(pid, 0) + 1

sorted_patients = sorted(patients.items(), key=lambda x: x[1], reverse=True)

print("\nTop 50 patients:")
for i, (pid, count) in enumerate(sorted_patients[:50]):
    print(f"{pid}: {count} nodules")
